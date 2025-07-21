from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.audio_stream import handle_audio_stream

router = APIRouter()


@router.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await handle_audio_stream(websocket)
    except WebSocketDisconnect:
        pass
