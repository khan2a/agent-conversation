# WebSocket Audio Streaming Server

A modular FastAPI WebSocket server for streaming audio data, designed for easy expansion (e.g., NLP processing).

## Features
- WebSocket endpoint for real-time audio streaming
- WebSocket endpoint for playing audio files from server
- Modular structure for easy future expansion
- Ready for integration with NLP or other audio processing services

## Requirements
- Python 3.9+
- [fastapi](https://fastapi.tiangolo.com/)
- [uvicorn](https://www.uvicorn.org/)
- [pydantic](https://docs.pydantic.dev/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [aiofiles](https://pypi.org/project/aiofiles/) (for async file operations)
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
- WebSocket echo endpoint: `ws://localhost:8000/ws/echo`
- WebSocket file player endpoint: `ws://localhost:8000/ws/play/{filename}`

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

- **Sample secure WebSocket endpoints:**
  - Echo: `wss://e8097d851324.ngrok-free.app/ws/echo`
  - File Player: `wss://e8097d851324.ngrok-free.app/ws/play/filename.mp3`

## WebSocket Endpoints

### Echo Endpoint
- URL: `ws://localhost:8000/ws/echo` (local) or `wss://e8097d851324.ngrok-free.app/ws/echo` (ngrok)
- Accepts: Binary audio data (raw bytes)
- Responds: Echoes received audio data (placeholder for future processing)

### Audio File Player Endpoint
- URL: `ws://localhost:8000/ws/play/{filename}` (local) or `wss://e8097d851324.ngrok-free.app/ws/play/{filename}` (ngrok)
- Accepts: WebSocket connection with filename in URL path
- Responds: Streams the specified audio file as binary chunks
- Supported formats: MP3, WAV, OGG, M4A, FLAC, AAC
- Files must be placed in the `audio_files/` directory

**Usage Examples:**
```javascript
// Echo endpoint
const echoWs = new WebSocket('ws://localhost:8000/ws/echo');

// File player endpoint
const playerWs = new WebSocket('ws://localhost:8000/ws/play/example.mp3');
```

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
    uri = "ws://localhost:8000/ws/echo"  # or wss://e8097d851324.ngrok-free.app/ws/echo
    async with websockets.connect(uri) as websocket:
        # Example: send 1 second of silence (16-bit PCM, 16kHz, mono)
        silence = b"\x00\x00" * 16000
        await websocket.send(silence)
        response = await websocket.recv()
        print(f"Received {len(response)} bytes back")

async def play_audio_file():
    filename = "example.mp3"
    uri = f"ws://localhost:8000/ws/play/{filename}"
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                if isinstance(message, str):
                    print(f"Server: {message}")
                else:
                    print(f"Received audio chunk: {len(message)} bytes")
            except websockets.exceptions.ConnectionClosed:
                break

asyncio.run(send_audio())  # Test echo endpoint
asyncio.run(play_audio_file())  # Test file player
```

## Testing

### Web Client
Open `test_client.html` in your browser to test both WebSocket endpoints with a simple web interface.

### Audio File Testing
1. Place audio files in the `audio_files/` directory
2. Connect to `ws://localhost:8000/ws/play/filename.ext`
3. The server will stream the file as binary chunks

### Supported Audio Formats
- MP3 (.mp3)
- WAV (.wav)
- OGG (.ogg)
- M4A (.m4a)
- FLAC (.flac)
- AAC (.aac)
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

