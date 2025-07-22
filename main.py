import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import Response, JSONResponse, FileResponse
from routers.websocket_audio import router as websocket_audio_router
from pydantic import RootModel
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
            logging.info(f"Received callback JSON: {payload}")
        except Exception as e:
            logging.error(f"Error parsing callback JSON: {e}")
    else:
        logging.info("Received GET request to /callback")
    return Response(status_code=204)


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
        endpoint_obj = {
            "type": "websocket",
            "uri": endpoint,
            "content-type": "audio/l16;rate=8000"
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
