# Agentic Conversation Server

A modular FastAPI WebSocket server for streaming audio data, designed for easy expansion (e.g., NLP processing).

## Features
### Core Features
- WebSocket endpoint for real-time audio streaming
- WebSocket endpoint for playing audio files from server
- Modular structure for easy future expansion
- Ready for integration with NLP or other audio processing services
- Health check endpoint (`GET /`)
- **Callback endpoint** (`/callback`):
  - In-memory storage of all received JSON payloads
  - Search stored data via GET with query parameters (multi-field search supported)
  - Color-coded logging for important fields (uuid, conversation_uuid, status)
  - RESTful API: POST to store, GET to search
- **Audio file serving** (`/audio/{filename}`):
  - Secure HTTP serving of audio files from `audio_files/` directory
  - Supported formats: MP3, WAV, OGG, M4A, FLAC, AAC
- **Speech-to-Text endpoints**:
  - `/stts`, `/stts/openai`, `/stts/ollama`: Accept speech input, process with OpenAI or Ollama, return NCCO responses
  - In-memory storage and retrieval of speech recognition results (`/speech`)
  - Asynchronous update of calls with new NCCO via Vonage API (with JWT auth)
- **NCCO endpoints**:
  - `/ncco/talk`: Returns a sample Vonage NCCO "talk" action
  - `/ncco/connect`: Returns a Vonage NCCO "connect" action for websocket, SIP, or phone endpoints, with support for custom headers
- **AI agent integration**: OpenAI and Ollama support for generating responses

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

### Direct Audio File Serving
- **Endpoint:** `GET /audio/{filename}`
- Securely serves audio files from `audio_files/` directory
- Supported formats: MP3, WAV, OGG, M4A, FLAC, AAC

**Usage Examples:**
```javascript
// Echo endpoint
const echoWs = new WebSocket('ws://localhost:8000/ws/echo');

// File player endpoint
const playerWs = new WebSocket('ws://localhost:8000/ws/play/example.mp3');
```

## Callback Endpoint

The `/callback` endpoint now includes advanced storage and search capabilities for received JSON data.

### Features
- **In-Memory Storage**: Automatically stores all received JSON payloads
- **Search Functionality**: Query stored data using URL parameters
- **Color-Coded Logging**: Important keywords are highlighted in console logs
- **RESTful API**: GET requests for searching, POST requests for storing

### Usage
- **POST** `/callback`: Store callback data (see example below)
- **GET** `/callback`: Retrieve all or search by any field (e.g., uuid, status, conversation_uuid)

### Endpoint Details
- **URL**: `/callback` (e.g., `https://e8097d851324.ngrok-free.app/callback`)
- **Methods**: `GET` (search), `POST` (store)
- **Storage**: JSON payloads stored in memory with automatic indexing
- **Logging**: Color-coded console output with blinking keywords

### POST - Store Callback Data
Stores JSON data in memory and logs with color highlighting.

**Example Request:**
```bash
curl -X POST https://e8097d851324.ngrok-free.app/callback \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "e2116b90-8b58-49fb-8487-0dcb0a8d29b5",
    "conversation_uuid": "CON-765ac2c5-8191-45fe-9ef3-c44ef1138868",
    "status": "completed",
    "duration": "1",
    "from": "Unknown",
    "to": "wss://khan2a.ngrok.io/ws/play/ff-16b-1c-16000hz.mp3"
  }'
```

**Response:** HTTP 204 No Content

**Console Output:**
```
2025-07-23 16:34:53,644 [INFO] Received callback JSON: {"uuid": "e2116b90-8b58-49fb-8487-0dcb0a8d29b5", "conversation_uuid": "CON-765ac2c5-8191-45fe-9ef3-c44ef1138868", "status": "completed", ...}
                                                          ^^^^ (blinking yellow)    ^^^^^^^^^^^^^^^^^ (blinking yellow)                  ^^^^^^ (blinking cyan)
2025-07-23 16:34:53,645 [INFO] Stored callback data. Total entries: 1  (in yellow)
```

### GET - Search Stored Data

#### Retrieve All Data
Get all stored callback entries.

**Request:**
```bash
curl https://e8097d851324.ngrok-free.app/callback
```

**Response:**
```json
{
  "total_entries": 5,
  "data": [
    {
      "uuid": "e2116b90-8b58-49fb-8487-0dcb0a8d29b5",
      "conversation_uuid": "CON-765ac2c5-8191-45fe-9ef3-c44ef1138868",
      "status": "completed",
      "duration": "1"
    },
    // ... more entries
  ]
}
```

#### Search by UUID
Find entries matching a specific UUID.

**Request:**
```bash
curl "https://e8097d851324.ngrok-free.app/callback?uuid=e2116b90-8b58-49fb-8487-0dcb0a8d29b5"
```

**Response:**
```json
{
  "query": {
    "uuid": "e2116b90-8b58-49fb-8487-0dcb0a8d29b5"
  },
  "total_matches": 1,
  "data": [
    {
      "uuid": "e2116b90-8b58-49fb-8487-0dcb0a8d29b5",
      "conversation_uuid": "CON-765ac2c5-8191-45fe-9ef3-c44ef1138868",
      "status": "completed",
      "duration": "1",
      "from": "Unknown",
      "to": "wss://khan2a.ngrok.io/ws/play/ff-16b-1c-16000hz.mp3"
    }
  ]
}
```

#### Search by Status
Find all entries with a specific status.

**Request:**
```bash
curl "https://e8097d851324.ngrok-free.app/callback?status=completed"
```

#### Search by Conversation UUID
Find all entries for a specific conversation.

**Request:**
```bash
curl "https://e8097d851324.ngrok-free.app/callback?conversation_uuid=CON-765ac2c5-8191-45fe-9ef3-c44ef1138868"
```

#### Multi-Field Search
Search using multiple criteria (AND operation).

**Request:**
```bash
curl "https://e8097d851324.ngrok-free.app/callback?status=completed&duration=1"
```

**Response:**
```json
{
  "query": {
    "status": "completed",
    "duration": "1"
  },
  "total_matches": 3,
  "data": [
    // ... matching entries
  ]
}
```

### Color-Coded Logging
The server highlights important keywords in console logs:

- **`uuid`**: Blinking yellow
- **`conversation_uuid`**: Blinking yellow  
- **`status`**: Blinking cyan
- **"Stored callback data"**: Yellow text

### Use Cases
- **Debug Webhooks**: Track callback data from external services
- **Audit Trail**: Search conversation history by UUID
- **Status Monitoring**: Filter by status values
- **Integration Testing**: Verify callback data structure and content

### Sample Integration with Vonage
```json
{
  "eventUrl": ["https://e8097d851324.ngrok-free.app/callback"],
  "eventMethod": "POST"
}
```

## NCCO Endpoints
- **GET `/ncco/talk`**: Returns a sample Vonage NCCO "talk" action.
- **GET `/ncco/connect?endpoint=...`**: Returns a Vonage NCCO "connect" action for the given endpoint (websocket, sip, or phone). Uses `HOST_NAME` from `.env` for `eventUrl`. Supports custom headers for websocket and SIP endpoints.

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

### Direct HTTP Audio File Testing
1. Place audio files in the `audio_files/` directory
2. Request `GET /audio/filename.ext` to download or stream the file

### Supported Audio Formats
- MP3 (.mp3)
- WAV (.wav)
- OGG (.ogg)
- M4A (.m4a)
- FLAC (.flac)
- AAC (.aac)

## Speech-to-Text & AI Agent Endpoints

### Endpoints
- `/stts` (default: OpenAI)
- `/stts/openai` (OpenAI)
- `/stts/ollama` (Ollama)

### Features
- Accepts speech input via POST callback (Vonage or other voice platforms)
- Stores speech recognition results per conversation UUID
- Returns NCCO responses generated by OpenAI or Ollama
- Supports asynchronous call updates via Vonage API (JWT authentication required)
- Retrieve speech results via `GET /speech` (all or by conversation_uuid)

### Example Usage
1. Configure Vonage or other voice platform to POST speech results to `/stts/openai` or `/stts/ollama`
2. The server processes speech, queries AI agent, and returns NCCO response
3. Speech results are stored and can be retrieved via `/speech`
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
## Additional Endpoints
- `GET /` — Health check (returns `{"status": "ok"}`)
- `GET /speech` — Retrieve all stored speech results or filter by conversation UUID
- All endpoints log important events with color-coded output for easier debugging

---
MIT License

