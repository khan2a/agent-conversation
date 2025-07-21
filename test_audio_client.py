import asyncio
import websockets


async def send_audio():
    uri = "ws://localhost:8000/ws/audio"
    async with websockets.connect(uri) as websocket:
        # Example: send 1 second of silence (16-bit PCM, 16kHz, mono)
        silence = b"\x00\x00" * 16000
        await websocket.send(silence)
        response = await websocket.recv()
        print(f"Received {len(response)} bytes back from server.")


asyncio.run(send_audio())
