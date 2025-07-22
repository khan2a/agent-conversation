# Audio Files Directory

This directory contains audio files that can be streamed through the WebSocket endpoint.

## Usage

Place your audio files in this directory and access them via:
```
ws://localhost:8000/ws/play/{filename}
```

## Supported Formats

- MP3 (.mp3)
- WAV (.wav) 
- OGG (.ogg)
- M4A (.m4a)
- FLAC (.flac)
- AAC (.aac)

## Example

If you have a file named `example.mp3` in this directory, connect to:
```
ws://localhost:8000/ws/play/example.mp3
```

The server will stream the audio file as binary data through the WebSocket connection.

## Security

- Files must be placed directly in this directory
- Path traversal attacks are prevented
- Only supported audio formats are allowed
