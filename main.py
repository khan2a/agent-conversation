import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from routers.websocket_audio import router as websocket_audio_router
from pydantic import RootModel
from dotenv import load_dotenv

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

# In-memory storage for callback data
callback_storage: List[Dict[str, Any]] = []

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
            "text": "This is a sample Vonage NCCO talk action."
        }
    ]
    return JSONResponse(content=ncco)


@app.get("/ncco/connect")
def ncco_connect(endpoint: str = Query(..., description="Endpoint string, e.g. ws://, sip:, or phone number")) -> JSONResponse:
    # Get HOST_NAME from environment or use default
    host_name = os.environ.get("HOST_NAME", "http://localhost:8000")
    event_url = f"{host_name.rstrip('/')}/callback"

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
    elif endpoint.startswith("sip:"):
        endpoint_obj = {
            "type": "sip",
            "uri": endpoint
        }
    elif endpoint.isdigit() or (endpoint.startswith("+") and endpoint[1:].isdigit()):
        endpoint_obj = {
            "type": "phone",
            "number": endpoint
        }
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
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
