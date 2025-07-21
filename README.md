# WebSocket Audio Streaming Server

A modular FastAPI WebSocket server for streaming audio data, designed for easy expansion (e.g., NLP processing).

## Features
- WebSocket endpoint for real-time audio streaming
- Modular structure for easy future expansion
- Ready for integration with NLP or other audio processing services

## Requirements
- Python 3.9+
- [fastapi](https://fastapi.tiangolo.com/)
- [uvicorn](https://www.uvicorn.org/)
- [pydantic](https://docs.pydantic.dev/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [ruff](https://docs.astral.sh/ruff/) (dev)
- [flake8](https://flake8.pycqa.org/en/latest/) (dev)
- [black](https://black.readthedocs.io/en/stable/) (dev)

## Installation

1. **Clone the repository and enter the project directory:**
   ```bash
   git clone <repo-url>
   cd websocket-server
   ```

2. **Install dependencies:**
   - With [uv](https://github.com/astral-sh/uv):
     ```bash
     pip install uv
     uv pip install -r requirements.txt
     ```
   - Or with pip:
     ```bash
     pip install -r requirements.txt
     ```
   - Or with Poetry:
     ```bash
     poetry install
     poetry shell
     ```

3. **Environment configuration:**
   - Create a `.env` file in the project root:
     ```env
     HOST_NAME=https://your-ngrok-or-domain/callback
     ```
   - The server will use this value for event URLs in NCCO responses.

## Running the Server

Start the WebSocket server with:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- The server will be accessible at [http://localhost:8000/](http://localhost:8000/)
- WebSocket endpoint: `ws://localhost:8000/ws/audio`

## Exposing the Server Publicly (ngrok)

To make your local WebSocket server accessible over the internet, use [ngrok](https://ngrok.com/):

1. **Install ngrok** (if not already installed):
   - Download from https://ngrok.com/download
   - Or use Homebrew: `brew install ngrok/ngrok/ngrok`

2. **Expose port 8000 with ngrok:**
   ```bash
   ngrok http 8000
   ```

3. ngrok will display a forwarding address like `https://e8097d851324.ngrok-free.app`. Use this address to connect to your WebSocket server or for HTTP callbacks from remote clients.

- **Sample secure WebSocket endpoint:**
  - `wss://e8097d851324.ngrok-free.app/ws/audio`

## WebSocket Audio Endpoint
- URL: `ws://localhost:8000/ws/audio` (local) or `wss://e8097d851324.ngrok-free.app/ws/audio` (ngrok)
- Accepts: Binary audio data (raw bytes)
- Responds: Echoes received audio data (placeholder for future processing)

## Callback Endpoint
- URL: `/callback` (e.g., `https://e8097d851324.ngrok-free.app/callback`)
- Method: `GET` or `POST`
- Accepts: Any JSON body (for POST)
- Returns: HTTP 204 No Content
- The server will print the received JSON to the console.

**Sample JSON for callback registration:**
```json
{
  "eventUrl": ["https://e8097d851324.ngrok-free.app/callback"],
  "eventMethod": "POST"
}
```

**Example curl request:**
```bash
curl -X POST https://e8097d851324.ngrok-free.app/callback \
  -H "Content-Type: application/json" \
  -d '{"foo": "bar", "number": 42}'
```

## NCCO Endpoints
- **GET `/ncco/talk`**: Returns a sample Vonage NCCO "talk" action.
- **GET `/ncco/connect?endpoint=...`**: Returns a Vonage NCCO "connect" action for the given endpoint (websocket, sip, or phone). Uses `HOST_NAME` from `.env` for `eventUrl`.

## Example Python Client

```python
import asyncio
import websockets

async def send_audio():
    uri = "ws://localhost:8000/ws/audio"  # or wss://e8097d851324.ngrok-free.app/ws/audio
    async with websockets.connect(uri) as websocket:
        # Example: send 1 second of silence (16-bit PCM, 16kHz, mono)
        silence = b"\x00\x00" * 16000
        await websocket.send(silence)
        response = await websocket.recv()
        print(f"Received {len(response)} bytes back from server.")

asyncio.run(send_audio())
```

## Development Tools & Code Quality
- **Ruff**: Linting
- **Flake8**: PEP8 compliance
- **Black**: Code formatting

To check and format code:
```bash
ruff check .
flake8 .
black .
```

---
MIT License

