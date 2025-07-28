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
import httpx
import asyncio
import uuid
import jwt
import json

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
    GREEN = '\033[92m'
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


async def query_ollama(stored_text: str) -> str:
    """
    Send a query to Ollama and retrieve the response.
    
    Args:
        stored_text: The text to send to Ollama
        
    Returns:
        The response from Ollama (extracted from message.content)
    """
    try:
        # Prepare the request payload for Ollama chat API
        request_payload = {
            "model": "llama3.2",
            "stream": False,
            "messages": [
                {"role": "user", "content": stored_text}
            ]
        }
        
        logging.info(f"{Colors.CYAN}Sending request to Ollama for: '{stored_text}'{Colors.RESET}")
        
        # Make the API call to Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://192.168.1.96:11434/api/chat",
                json=request_payload,
                timeout=60.0  # Increased timeout for Ollama's slower response
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the message content from the response
                if "message" in response_data and "content" in response_data["message"]:
                    ai_response = response_data["message"]["content"]
                    logging.info(f"{Colors.MAGENTA}Ollama response for '{stored_text}': '{ai_response}'{Colors.RESET}")
                    return ai_response
                else:
                    logging.error(f"Unexpected Ollama response format: {response_data}")
                    return "I am sorry, could you repeat yourself again?"
            else:
                logging.error(f"Ollama API error: {response.status_code} - {response.text}")
                return "I am sorry, could you repeat yourself again?"
                
    except Exception as e:
        logging.error(f"Error querying Ollama: {e}")
        return "I am sorry, could you repeat yourself again?"


def get_ai_agent_function(agent_type: str):
    """
    Get the appropriate AI agent function based on the agent type.
    
    Args:
        agent_type: Either 'openai' or 'ollama'
        
    Returns:
        The corresponding AI query function (async for ollama, sync for openai)
    """
    if agent_type == "openai":
        return query_openai
    elif agent_type == "ollama":
        # Note: Ollama responses can take up to 40 seconds
        logging.info(f"{Colors.YELLOW}Using Ollama - expect up to 40 seconds for response{Colors.RESET}")
        return query_ollama
    else:
        raise ValueError(f"Unsupported AI agent type: {agent_type}")


async def update_call_with_ncco(call_uuid: str, ncco: List[dict]) -> None:
    """
    Update a call with new NCCO using Vonage Voice API.
    
    Args:
        call_uuid: The UUID of the call to update
        ncco: The NCCO array to send
    """
    try:
        # Get Vonage credentials from environment
        vonage_app_id = os.environ.get("VONAGE_APP_ID")
        vonage_private_key_path = os.environ.get("VONAGE_PRIVATE_KEY_PATH")
        
        logging.info(f"{Colors.CYAN}Attempting to update call {call_uuid} with NCCO{Colors.RESET}")
        logging.info(f"{Colors.CYAN}VONAGE_APP_ID: {vonage_app_id}{Colors.RESET}")
        logging.info(f"{Colors.CYAN}VONAGE_PRIVATE_KEY_PATH: {vonage_private_key_path}{Colors.RESET}")
        
        if not vonage_app_id or not vonage_private_key_path:
            logging.error("VONAGE_APP_ID or VONAGE_PRIVATE_KEY_PATH not found in environment variables")
            logging.error("Please set these environment variables to enable Vonage API integration")
            return
        
        # Check if private key file exists
        if not os.path.exists(vonage_private_key_path):
            logging.error(f"Private key file not found: {vonage_private_key_path}")
            return
        
        # Read private key
        with open(vonage_private_key_path, 'r') as f:
            private_key = f.read()
        
        logging.info(f"{Colors.CYAN}Private key loaded successfully{Colors.RESET}")
        
        # Create JWT token (simplified - in production, use proper JWT library)
        import time
        
        payload = {
            'application_id': vonage_app_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,  # 1 hour expiry
            'jti': str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, private_key, algorithm='RS256')
        logging.info(f"{Colors.CYAN}JWT token generated successfully{Colors.RESET}")
        
        # Prepare the request payload
        request_payload = {
            "action": "transfer",
            "destination": {
                "type": "ncco",
                "ncco": ncco
            }
        }
        
        logging.info(f"{Colors.CYAN}Request payload: {json.dumps(request_payload, indent=2)}{Colors.RESET}")
        
        # Make the API call
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://api.nexmo.com/v1/calls/{call_uuid}",
                json=request_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            logging.info(f"{Colors.CYAN}Vonage API response status: {response.status_code}{Colors.RESET}")
            logging.info(f"{Colors.CYAN}Vonage API response headers: {dict(response.headers)}{Colors.RESET}")
            logging.info(f"{Colors.CYAN}Vonage API response body: {response.text}{Colors.RESET}")
            
            if response.status_code == 200:
                logging.info(f"{Colors.GREEN}Successfully updated call {call_uuid} with NCCO{Colors.RESET}")
            else:
                logging.error(f"Failed to update call {call_uuid}: {response.status_code} - {response.text}")
                
    except Exception as e:
        logging.error(f"Error updating call {call_uuid} with NCCO: {e}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")


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
    
    # Find the result with highest confidence, handling None values
    try:
        highest_confidence_result = max(speech_results, key=lambda x: float(x.get('confidence', 0) or 0))
        highest_confidence_text = highest_confidence_result.get('text', '')
        highest_confidence_score = highest_confidence_result.get('confidence', '0')
        
        # Store only the highest confidence text for this conversation
        speech_storage[conversation_uuid] = highest_confidence_text
        
        logging.info(f"{Colors.MAGENTA}Stored highest confidence speech for {conversation_uuid}: '{highest_confidence_text}' (confidence: {highest_confidence_score}){Colors.RESET}")
        logging.info(f"{Colors.YELLOW}Total speech conversations stored: {len(speech_storage)}{Colors.RESET}")
    except (ValueError, TypeError) as e:
        logging.error(f"Error processing speech results: {e}")
        # Store empty text to indicate processing error
        speech_storage[conversation_uuid] = ""


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
async def generate_speech_response_ncco(conversation_uuid: str, event_url: str, ai_agent_func) -> List[dict]:
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
        
        # Check if speech processing failed or text is empty
        if not stored_text or stored_text.strip() == "":
            logging.info(f"{Colors.YELLOW}Speech processing failed or empty text for {conversation_uuid}, using fallback response{Colors.RESET}")
            ai_response = "I am sorry, could you repeat yourself again?"
        else:
            # Handle both sync and async AI agent functions
            if asyncio.iscoroutinefunction(ai_agent_func):
                ai_response = await ai_agent_func(stored_text)
            else:
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


async def handle_stts_request(request: Request, agent_type: str) -> Response:
    """
    Common handler for STTS requests that delegates to appropriate AI agent.
    
    Args:
        request: The FastAPI request object
        agent_type: The AI agent type ('openai' or 'ollama')
        
    Returns:
        Response with appropriate NCCO or HTTP 204 for async processing
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
        try:
            process_speech_results(payload)
        except (ValueError, TypeError) as e:
            logging.error(f"Error processing speech results: {e}")
            # Continue processing with fallback response
        
        logging.info(f"{Colors.CYAN}Stored speech input data. Total callback entries: {len(callback_storage)}{Colors.RESET}")
        
        # Generate NCCO response based on stored speech immediately
        conversation_uuid = payload.get('conversation_uuid')
        ncco = await generate_speech_response_ncco(conversation_uuid, event_url, ai_agent_func)
        
        logging.info(f"{Colors.GREEN}Returning NCCO immediately for {agent_type} speech input{Colors.RESET}")
        return JSONResponse(content=ncco)
        
    except Exception as e:
        logging.error(f"Error parsing {agent_type} speech input callback: {e}")
        # Return fallback response instead of HTTP 400
        fallback_ncco = [
            {
                "action": "talk",
                "text": "I am sorry, could you repeat yourself again?",
                "style": 0,
                "language": "en-GB",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [event_url],
                "type": ["speech"]
            }
        ]
        logging.info(f"{Colors.YELLOW}Returning fallback NCCO due to error: {e}{Colors.RESET}")
        return JSONResponse(content=fallback_ncco)


async def async_process_speech_and_update_call(
    conversation_uuid: str, 
    event_url: str, 
    ai_agent_func, 
    call_uuid: str
) -> None:
    """
    Asynchronously process speech results and update the call with new NCCO.
    
    Args:
        conversation_uuid: The conversation UUID to look up
        event_url: The event URL for the input action
        ai_agent_func: The AI agent function to use for generating responses
        call_uuid: The UUID of the call to update
    """
    try:
        # Generate NCCO response based on stored speech
        ncco = await generate_speech_response_ncco(conversation_uuid, event_url, ai_agent_func)
        
        # Check if the call is still active by looking at recent callbacks
        # If we received a "completed" status for this call, don't try to update it
        call_completed = False
        for entry in callback_storage[-10:]:  # Check last 10 entries
            if entry.get('uuid') == call_uuid and entry.get('status') == 'completed':
                call_completed = True
                logging.info(f"{Colors.YELLOW}Call {call_uuid} has already completed, skipping NCCO update{Colors.RESET}")
                break
        
        if call_completed:
            logging.info(f"{Colors.YELLOW}Skipping NCCO update for completed call {call_uuid}{Colors.RESET}")
            return
        
        # Add a small delay to ensure the call is still active
        await asyncio.sleep(0.5)
        
        # Update the call with the new NCCO
        await update_call_with_ncco(call_uuid, ncco)
        
    except Exception as e:
        logging.error(f"Error in async speech processing for call {call_uuid}: {e}")


@app.api_route("/stts/openai", methods=["GET", "POST"])
async def stts_openai_endpoint(request: Request) -> Response:
    """
    Speech-to-Text Service endpoint using OpenAI for responses.
    """
    return await handle_stts_request(request, "openai")


@app.api_route("/stts/ollama", methods=["GET", "POST"])
async def stts_ollama_endpoint(request: Request) -> Response:
    """
    Speech-to-Text Service endpoint using Ollama for responses.
    """
    return await handle_stts_request(request, "ollama")


@app.api_route("/stts", methods=["GET", "POST"])
async def stts_endpoint(request: Request) -> Response:
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
