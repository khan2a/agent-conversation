from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.audio_stream import handle_audio_stream, handle_audio_file_stream

router = APIRouter()


@router.websocket("/ws/echo")
async def audio_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await handle_audio_stream(websocket)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/play/{filename}")
async def play_audio_file_endpoint(websocket: WebSocket, filename: str):
    """WebSocket endpoint to play an audio file by filename."""
    await websocket.accept()
    try:
        await handle_audio_file_stream(websocket, filename)
    except WebSocketDisconnect:
        pass
