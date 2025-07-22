import os
import asyncio
import aiofiles
import wave
import logging
from pathlib import Path
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


async def handle_audio_file_stream(websocket: WebSocket, filename: str) -> None:
    """Stream an audio file to the WebSocket client."""
    try:
        # Define the audio files directory (you can modify this path as needed)
        audio_dir = Path("audio_files")
        file_path = audio_dir / filename
        
        # Check if file exists and is in the allowed directory
        if not file_path.exists():
            # Close connection instead of sending text error
            await websocket.close(code=1003, reason="File not found")
            return
            
        # Check if it's actually within the audio directory (security check)
        try:
            file_path.resolve().relative_to(audio_dir.resolve())
        except ValueError:
            # Close connection instead of sending text error
            await websocket.close(code=1003, reason="Invalid file path")
            return
        
        # Check file extension for supported formats
        supported_formats = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
        if file_path.suffix.lower() not in supported_formats:
            # Send error as binary data or close connection instead of text
            await websocket.close(code=1003, reason="Unsupported audio format")
            return
        
        # Stream the file in chunks - NO TEXT MESSAGES, ONLY BINARY
        chunk_size = 320  # Smaller chunks for better timing control (was 640)
        
        # For WAV files, try to get audio properties for better timing
        sleep_time = 0.01  # Increased default sleep time (was 0.001)
        if file_path.suffix.lower() == '.wav':
            try:
                with wave.open(str(file_path), "rb") as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    width = wf.getsampwidth()
                    bytes_per_frame = (channels * width)
                    # Adjusted formula for more realistic timing
                    sleep_time = (chunk_size / (rate * bytes_per_frame)) - 0.005  # Reduced adjustment factor
                    # Ensure minimum sleep time to prevent too fast playback
                    sleep_time = max(sleep_time, 0.005)  # Minimum 5ms between chunks
                    duration = wf.getnframes() / rate
                    print(f"Streaming {filename} | Channels: {channels}, Rate: {rate}, Bytes per Frame: {bytes_per_frame}, Width: {width}, Duration: {duration:.2f} sec, Sleep: {sleep_time:.6f} sec")
            except Exception as e:
                print(f"Could not read WAV properties for {filename}: {e}, using default timing")
        
        # Stream the file using the adapted code structure
        async with aiofiles.open(file_path, 'rb') as audio_file:
            chunk_count = 0
            bytes_sent = 0
            
            while True:
                # Check if client is still connected
                try:
                    # Try to receive any messages (including ping/close)
                    message = await asyncio.wait_for(websocket.receive(), timeout=0.0001)
                    if message.get("type") == "websocket.disconnect":
                        break
                except asyncio.TimeoutError:
                    # No message received, continue streaming
                    pass
                except WebSocketDisconnect:
                    break
                
                # Read chunk
                chunk = await audio_file.read(chunk_size)
                if not chunk:
                    break
                
                chunk_count += 1
                bytes_sent += len(chunk)
                
                # Debug logging to verify binary data (server-side only)
                if chunk_count == 1:
                    print(f"First chunk: {len(chunk)} bytes, type: {type(chunk)}, first 10 bytes: {chunk[:10]}")
                
                # Send binary chunk
                await websocket.send_bytes(chunk)
                
                # Sleep based on audio properties for realistic streaming rate
                await asyncio.sleep(sleep_time)
        
        # Don't send completion text - just close cleanly
        print(f"Finished streaming '{filename}'. Sent {bytes_sent} bytes total in {chunk_count} chunks.")
        
    except WebSocketDisconnect:
        # Client disconnected cleanly
        pass
    except FileNotFoundError:
        # Log error but don't send text to client
        print(f"Error: Audio file '{filename}' not found.")
    except Exception as e:
        # Log error but don't send text to client  
        print(f"Error during playback: {str(e)}")
