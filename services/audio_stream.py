from fastapi import WebSocket, WebSocketDisconnect


async def handle_audio_stream(websocket: WebSocket) -> None:
    try:
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError:
                # Client disconnected
                break
            if "bytes" in message:
                data = message["bytes"]
                await websocket.send_bytes(data)
            elif "text" in message:
                await websocket.send_text("Error: Only binary audio data is supported.")
            else:
                # Optionally handle other message types (e.g., close, ping)
                pass
    except WebSocketDisconnect:
        # Client disconnected cleanly
        pass
