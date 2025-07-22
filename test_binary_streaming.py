#!/usr/bin/env python3
"""
Test script to verify binary audio streaming via WebSocket.
This connects to the WebSocket endpoint and analyzes the received data.
"""

import asyncio
import websockets
import sys
from pathlib import Path

async def test_binary_streaming(filename="test_tone.wav"):
    """Test binary audio streaming and analyze the received data."""
    uri = f"ws://localhost:8000/ws/play/{filename}"
    
    print(f"Testing binary streaming from: {uri}")
    print(f"Expected file: audio_files/{filename}")
    
    # Check if file exists locally for comparison
    local_file = Path("audio_files") / filename
    if local_file.exists():
        local_size = local_file.stat().st_size
        print(f"Local file size: {local_size} bytes")
        
        # Read first 20 bytes for comparison
        with open(local_file, 'rb') as f:
            first_bytes = f.read(20)
            print(f"Local file first 20 bytes: {first_bytes.hex()}")
    else:
        print(f"WARNING: Local file {local_file} not found")
    
    print("\n--- Connecting to WebSocket ---")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully")
            
            received_chunks = []
            text_messages = []
            total_bytes = 0
            
            while True:
                try:
                    message = await websocket.recv()
                    
                    if isinstance(message, str):
                        text_messages.append(message)
                        print(f"TEXT: {message}")
                    elif isinstance(message, bytes):
                        chunk_size = len(message)
                        total_bytes += chunk_size
                        received_chunks.append(message)
                        
                        # Log first chunk details
                        if len(received_chunks) == 1:
                            print(f"FIRST BINARY CHUNK: {chunk_size} bytes")
                            print(f"First 20 bytes: {message[:20].hex()}")
                            print(f"Data type: {type(message)}")
                        
                        print(f"BINARY CHUNK #{len(received_chunks)}: {chunk_size} bytes (Total: {total_bytes})")
                    else:
                        print(f"UNKNOWN MESSAGE TYPE: {type(message)}")
                        
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
            
            print(f"\n--- Summary ---")
            print(f"Text messages: {len(text_messages)}")
            print(f"Binary chunks: {len(received_chunks)}")
            print(f"Total bytes received: {total_bytes}")
            
            if received_chunks:
                # Verify binary data integrity
                combined_data = b''.join(received_chunks)
                print(f"Combined data size: {len(combined_data)} bytes")
                
                if local_file.exists():
                    # Compare with local file
                    with open(local_file, 'rb') as f:
                        local_data = f.read()
                    
                    if combined_data == local_data:
                        print("✅ SUCCESS: Received data matches local file exactly!")
                    else:
                        print("❌ ERROR: Received data differs from local file")
                        print(f"Local file size: {len(local_data)}")
                        print(f"Received size: {len(combined_data)}")
                
                # Save received data for inspection
                output_file = Path(f"received_{filename}")
                with open(output_file, 'wb') as f:
                    f.write(combined_data)
                print(f"Saved received data to: {output_file}")
            else:
                print("❌ ERROR: No binary data received!")
                
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "test_tone.wav"
    asyncio.run(test_binary_streaming(filename))
