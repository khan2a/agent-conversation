import uvicorn
import time
from functools import wraps
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from routers.websocket_audio import router as websocket_audio_router
from pydantic import RootModel
from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Color codes for terminal output
class Colors:
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLINK = '\033[5m'
    RESET = '\033[0m'
    MAGENTA = '\033[95m'
# Ensure the audio_files directory exi

# In-memory storage for callback data
callback_storage: List[Dict[str, Any]] = []

# In-memory storage for speech results (conversation_uuid -> highest confidence text)
speech_storage: Dict[str, str] = {}

app = FastAPI()

app.include_router(websocket_audio_router)


@app.get("/")
def health_check() -> dict:
    return {"status": "ok"}


class CallbackPayload(RootModel[dict]):
    pass


@app.api_route("/callback", methods=["GET", "POST"], status_code=204)
async def callback_endpoint(request: Request) -> Response:
    if request.method == "POST":
        try:
            payload = await request.json()
            
            # Convert to JSON string for formatting
            import json
            json_str = json.dumps(payload)
            formatted_json_str = json_str
            
            # Apply color formatting to specific keywords if they exist
            if 'status' in payload:
                formatted_json_str = formatted_json_str.replace('"status"', f'"{Colors.BLINK}{Colors.CYAN}status{Colors.RESET}"')
            
            if 'uuid' in payload:
                formatted_json_str = formatted_json_str.replace('"uuid"', f'"{Colors.BLINK}{Colors.YELLOW}uuid{Colors.RESET}"')
            
            if 'conversation_uuid' in payload:
                formatted_json_str = formatted_json_str.replace('"conversation_uuid"', f'"{Colors.BLINK}{Colors.YELLOW}conversation_uuid{Colors.RESET}"')
            
            logging.info(f"Received callback JSON: {formatted_json_str}")
            
            # Store the payload in memory
            callback_storage.append(payload)
            logging.info(f"{Colors.YELLOW}Stored callback data. Total entries: {len(callback_storage)}{Colors.RESET}")
            
        except Exception as e:
            logging.error(f"Error parsing callback JSON: {e}")
    else:
        # GET request - handle search functionality
        query_params = dict(request.query_params)
        
        if not query_params:
            # No query parameters - return all stored data
            logging.info(f"GET /callback - returning all {len(callback_storage)} entries")
            return JSONResponse(content={
                "total_entries": len(callback_storage),
                "data": callback_storage
            })
        else:
            # Search for matching entries based on query parameters
            logging.info(f"GET /callback - searching with parameters: {query_params}")
            matching_entries = search_callback_data(query_params)
            
            logging.info(f"Found {len(matching_entries)} matching entries")
            return JSONResponse(content={
                "query": query_params,
                "total_matches": len(matching_entries),
                "data": matching_entries
            })
    
    return Response(status_code=204)


def search_callback_data(search_params: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Search stored callback data based on key-value pairs.
    Returns all entries that match ALL provided search parameters.
    """
    matching_entries = []
    
    for entry in callback_storage:
        match_found = True
        
        # Check if all search parameters match this entry
        for key, value in search_params.items():
            if key not in entry:
                match_found = False
                break
            
            # Convert both values to strings for comparison (handles different data types)
            entry_value = str(entry[key])
            search_value = str(value)
            
            if entry_value != search_value:
                match_found = False
                break
        
        if match_found:
            matching_entries.append(entry)
    
    return matching_entries


def query_openai(stored_text: str) -> str:
    """
    Send a query to OpenAI and retrieve the response.
    
    Args:
        stored_text: The text to send to OpenAI
        
    Returns:
        The response from OpenAI, or an error message if the request fails
    """
    try:
        # Set API key from environment variable
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not openai.api_key:
            logging.error("OPENAI_API_KEY not found in environment variables")
            return "I'm sorry, I'm unable to process your request right now."
        
        # Create completion request
        response = openai.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "user", "content": stored_text}
            ],
            max_tokens=150,  # Limit response length for voice calls
            temperature=0.7
        )
        
        # Extract the assistant's reply
        reply = response.choices[0].message.content
        logging.info(f"{Colors.MAGENTA}OpenAI response for '{stored_text}': '{reply}'{Colors.RESET}")
        return reply
        
    except Exception as e:
        logging.error(f"Error querying OpenAI: {e}")
        return "I'm sorry, I encountered an error processing your request."


def query_ollama(stored_text: str) -> str:
    """
    Send a query to Ollama and retrieve the response.
    Placeholder implementation for now.
    
    Args:
        stored_text: The text to send to Ollama
        
    Returns:
        The response from Ollama (currently a placeholder)
    """
    logging.info(f"{Colors.CYAN}Ollama placeholder response for '{stored_text}'{Colors.RESET}")
    return f"you said {stored_text}"


def get_ai_agent_function(agent_type: str):
    """
    Get the appropriate AI agent function based on the agent type.
    
    Args:
        agent_type: Either 'openai' or 'ollama'
        
    Returns:
        The corresponding AI query function
    """
    if agent_type == "openai":
        return query_openai
    elif agent_type == "ollama":
        return query_ollama
    else:
        raise ValueError(f"Unsupported AI agent type: {agent_type}")


@app.get("/audio/{filename}")
async def serve_audio_file(filename: str):
    """Serve audio files directly via HTTP for comparison with WebSocket streaming."""
    audio_dir = Path("audio_files")
    file_path = audio_dir / filename
    
    # Security check - ensure file is in audio directory
    try:
        file_path.resolve().relative_to(audio_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file '{filename}' not found")
    
    # Check file extension
    supported_formats = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    if file_path.suffix.lower() not in supported_formats:
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    return FileResponse(file_path)


@app.get("/ncco/talk")
def ncco_talk() -> JSONResponse:
    ncco = [
        {
            "action": "talk",
            "style": 0,
            "language": "en-GB",
            "text": "This is a sample Vonage NCCO talk action."
        }
    ]
    return JSONResponse(content=ncco)


def process_speech_results(payload: dict) -> None:
    """
    Process speech results from callback payload and store the highest confidence text.
    
    Args:
        payload: The callback payload containing speech results
    """
    if 'speech' not in payload or 'results' not in payload['speech'] or not payload['speech']['results']:
        return
    
    conversation_uuid = payload.get('conversation_uuid')
    speech_results = payload['speech']['results']
    
    if not conversation_uuid or not speech_results:
        return
    
    # Find the result with highest confidence
    highest_confidence_result = max(speech_results, key=lambda x: float(x.get('confidence', 0)))
    highest_confidence_text = highest_confidence_result.get('text', '')
    highest_confidence_score = highest_confidence_result.get('confidence', '0')
    
    # Store only the highest confidence text for this conversation
    speech_storage[conversation_uuid] = highest_confidence_text
    
    logging.info(f"{Colors.MAGENTA}Stored highest confidence speech for {conversation_uuid}: '{highest_confidence_text}' (confidence: {highest_confidence_score}){Colors.RESET}")
    logging.info(f"{Colors.YELLOW}Total speech conversations stored: {len(speech_storage)}{Colors.RESET}")


def timeit_sec(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = (time.time() - start_time)
        logging.info(f"{Colors.CYAN}Total time to generate NCCO: {elapsed_ms:.2f} sec.{Colors.RESET}")
        return result
    return wrapper

@timeit_sec
def generate_speech_response_ncco(conversation_uuid: str, event_url: str, ai_agent_func) -> List[dict]:
    """
    Generate NCCO response based on stored speech for a conversation.
    
    Args:
        conversation_uuid: The conversation UUID to look up
        event_url: The event URL for the input action
        ai_agent_func: The AI agent function to use for generating responses
        
    Returns:
        NCCO array with appropriate response
    """
    if conversation_uuid and conversation_uuid in speech_storage:
        # Get the latest text stored for this conversation and query AI agent
        stored_text = speech_storage[conversation_uuid]
        ai_response = ai_agent_func(stored_text)
        
        ncco = [
            {
                "action": "talk",
                "text": ai_response,
                "style": 0,
                "language": "en-GB",
                "bargeIn": True  # Allow barge-in for voice input
            },
            {
                "action": "input",
                "eventUrl": [event_url],
                "type": ["speech"]
            }
        ]
        logging.info(f"{Colors.YELLOW}Generated NCCO with AI response for {conversation_uuid}:\n'{ncco}'{Colors.RESET}")
        return ncco
    else:
        # No speech result found, use default greeting
        ncco = [
            {
                "action": "talk",
                "style": 0,
                "language": "en-GB",
                "text": "hello, how can i assist you today?"
            },
            {
                "action": "input",
                "eventUrl": [event_url],
                "type": ["speech"]
            }
        ]
        logging.info(f"{Colors.YELLOW}No speech found for {conversation_uuid}, using default greeting{Colors.RESET}")
        return ncco


def generate_initial_speech_ncco(event_url: str) -> List[dict]:
    """
    Generate initial NCCO for speech input.
    
    Args:
        event_url: The event URL for the input action
        
    Returns:
        NCCO array with talk and input actions
    """
    return [
        {
            "action": "talk",
            "style": 0,
            "language": "en-GB",
            "text": "Hello, how can I assist you today?"
        },
        {
            "action": "input",
            "eventUrl": [event_url],
            "type": ["speech"]
        }
    ]


async def handle_stts_request(request: Request, agent_type: str) -> JSONResponse:
    """
    Common handler for STTS requests that delegates to appropriate AI agent.
    
    Args:
        request: The FastAPI request object
        agent_type: The AI agent type ('openai' or 'ollama')
        
    Returns:
        JSONResponse with appropriate NCCO
    """
    # Get HOST_NAME from environment or use default
    host_name = os.environ.get("HOST_NAME", "http://localhost:8000")
    event_url = f"{host_name.rstrip('/')}/stts/{agent_type}"
    
    # Get the appropriate AI agent function
    try:
        ai_agent_func = get_ai_agent_function(agent_type)
    except ValueError as e:
        logging.error(str(e))
        return JSONResponse(status_code=400, content={"error": str(e)})
    
    if request.method == "GET":
        ncco = generate_initial_speech_ncco(event_url)
        logging.info(f"Generated NCCO for {agent_type} speech input: {ncco}")
        return JSONResponse(content=ncco)
    
    # Handle POST request - speech input callback
    try:
        payload = await request.json()
        logging.info(f"Received {agent_type} speech input callback: {payload}")
        
        # Store the full payload in callback storage
        callback_storage.append(payload)
        
        # Process speech results if available
        process_speech_results(payload)
        
        logging.info(f"{Colors.CYAN}Stored speech input data. Total callback entries: {len(callback_storage)}{Colors.RESET}")
        
        # Generate NCCO response based on stored speech
        conversation_uuid = payload.get('conversation_uuid')
        ncco = generate_speech_response_ncco(conversation_uuid, event_url, ai_agent_func)
        
        return JSONResponse(content=ncco)
        
    except Exception as e:
        logging.error(f"Error parsing {agent_type} speech input callback: {e}")
        return JSONResponse(status_code=400, content={"error": "Invalid JSON payload"})


@app.api_route("/stts/openai", methods=["GET", "POST"])
async def stts_openai_endpoint(request: Request) -> JSONResponse:
    """
    Speech-to-Text Service endpoint using OpenAI for responses.
    """
    return await handle_stts_request(request, "openai")


@app.api_route("/stts/ollama", methods=["GET", "POST"])
async def stts_ollama_endpoint(request: Request) -> JSONResponse:
    """
    Speech-to-Text Service endpoint using Ollama for responses.
    """
    return await handle_stts_request(request, "ollama")


@app.api_route("/stts", methods=["GET", "POST"])
async def stts_endpoint(request: Request) -> JSONResponse:
    """
    Default Speech-to-Text Service endpoint that uses OpenAI.
    For backward compatibility.
    """
    return await handle_stts_request(request, "openai")


@app.get("/speech")
async def get_speech_results(conversation_uuid: Optional[str] = Query(None, description="Filter by conversation UUID")):
    """
    Get stored speech recognition results.
    If conversation_uuid is provided, returns the result for that specific conversation.
    Otherwise, returns all stored speech results.
    """
    if conversation_uuid:
        if conversation_uuid in speech_storage:
            return JSONResponse(content={
                "conversation_uuid": conversation_uuid,
                "text": speech_storage[conversation_uuid]
            })
        else:
            raise HTTPException(status_code=404, detail=f"No speech result found for conversation_uuid: {conversation_uuid}")
    else:
        return JSONResponse(content={
            "total_conversations": len(speech_storage),
            "speech_results": speech_storage
        })


@app.get("/ncco/connect")
def ncco_connect(request: Request, endpoint: str = Query(..., description="Endpoint string, e.g. ws://, sip:, or phone number")) -> JSONResponse:
    # Get HOST_NAME from environment or use default
    host_name = os.environ.get("HOST_NAME", "http://localhost:8000")
    event_url = f"{host_name.rstrip('/')}/callback"

    # Get all query parameters
    query_params = dict(request.query_params)
    
    # Parse headers parameter if present
    headers_dict = None
    if "headers" in query_params:
        headers_param = query_params["headers"]
        try:
            # Parse headers format: {key1:value1,key2:value2}
            headers_param = headers_param.strip('{}')
            headers_dict = {}
            if headers_param:
                for pair in headers_param.split(','):
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        headers_dict[key.strip()] = value.strip()
            logging.info(f"Parsed headers: {headers_dict}")
        except Exception as e:
            logging.error(f"Error parsing headers parameter: {e}")
            headers_dict = None

    # Determine endpoint type and build NCCO accordingly
    endpoint_obj = None
    if endpoint.startswith("ws://") or endpoint.startswith("wss://"):
        # Default content type
        content_type = "audio/l16;rate=16000" if "16000" in endpoint else "audio/l16;rate=8000"

        endpoint_obj = {
            "type": "websocket",
            "uri": endpoint,
            "content-type": content_type
        }
        
        # Add headers if present
        if headers_dict:
            endpoint_obj["headers"] = headers_dict
            
    elif endpoint.startswith("sip:"):
        endpoint_obj = {
            "type": "sip",
            "uri": endpoint
        }
        # Add headers if present
        if headers_dict:
            endpoint_obj["headers"] = headers_dict
            
    elif endpoint.isdigit() or (endpoint.startswith("+") and endpoint[1:].isdigit()):
        endpoint_obj = {
            "type": "phone",
            "number": endpoint
        }
        # Note: Headers typically not applicable to phone endpoints
        
    else:
        logging.error(f"Unsupported or invalid endpoint: {endpoint}")
        return JSONResponse(
            status_code=400,
            content={"error": "Unsupported or invalid endpoint. Use ws(s)://, sip:, or phone number."}
        )
    ncco = [
        {
            "action": "connect",
            "endpoint": [endpoint_obj],
            "eventUrl": [event_url]
        }
    ]
    logging.info(f"Generated NCCO for connect: {ncco}")
    return JSONResponse(content=ncco)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
