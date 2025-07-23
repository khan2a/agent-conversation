#!/usr/bin/env python3
"""
Test script to verify binary audio streaming via WebSocket.
This connects to the WebSocket endpoint and analyzes the received data.
"""

import asyncio
import websockets
import sys
import logging
from pathlib import Path

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log levels."""
    
    COLORS = {
        'DEBUG': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD,
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Colors.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Colors.RESET}"
        return super().format(record)

# Set up colored logging
def setup_logging():
    """Configure logging with colors."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with color formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = ColoredFormatter(
        f'{Colors.BLUE}%(asctime)s{Colors.RESET} - %(levelname)s - {Colors.WHITE}%(message)s{Colors.RESET}',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

def _check_local_file(filename):
    """Check if local file exists and print comparison info."""
    local_file = Path("audio_files") / filename
    if local_file.exists():
        local_size = local_file.stat().st_size
        logger.info(f"{Colors.CYAN}Local file size: {local_size} bytes{Colors.RESET}")
        
        # Read first 20 bytes for comparison
        with open(local_file, 'rb') as f:
            first_bytes = f.read(20)
            logger.info(f"{Colors.CYAN}Local file first 20 bytes: {first_bytes.hex()}{Colors.RESET}")
        return local_file
    else:
        logger.warning(f"Local file {local_file} not found")
        return None

def _process_message(message, received_chunks, text_messages, total_bytes):
    """Process a single WebSocket message and update counters."""
    if isinstance(message, str):
        text_messages.append(message)
        logger.info(f"{Colors.MAGENTA}TEXT MESSAGE: {message}{Colors.RESET}")
    elif isinstance(message, bytes):
        chunk_size = len(message)
        total_bytes += chunk_size
        received_chunks.append(message)
        
        # Log first chunk details
        if len(received_chunks) == 1:
            logger.info(f"{Colors.GREEN}FIRST BINARY CHUNK: {chunk_size} bytes{Colors.RESET}")
            logger.info(f"{Colors.GREEN}First 20 bytes: {message[:20].hex()}{Colors.RESET}")
            logger.info(f"{Colors.GREEN}Data type: {type(message)}{Colors.RESET}")
        
        logger.info(f"{Colors.BLUE}BINARY CHUNK #{len(received_chunks)}: {chunk_size} bytes (Total: {total_bytes}){Colors.RESET}")
    else:
        logger.error(f"UNKNOWN MESSAGE TYPE: {type(message)}")
    
    return total_bytes

def _verify_data_integrity(received_chunks, local_file, filename):
    """Verify binary data integrity against local file."""
    combined_data = b''.join(received_chunks)
    logger.info(f"{Colors.CYAN}Combined data size: {len(combined_data)} bytes{Colors.RESET}")
    
    if local_file and local_file.exists():
        # Compare with local file
        with open(local_file, 'rb') as f:
            local_data = f.read()
        
        if combined_data == local_data:
            logger.info(f"{Colors.GREEN}{Colors.BOLD}✅ SUCCESS: Received data matches local file exactly!{Colors.RESET}")
        else:
            logger.error(f"{Colors.RED}❌ ERROR: Received data differs from local file{Colors.RESET}")
            logger.error(f"{Colors.RED}Local file size: {len(local_data)}{Colors.RESET}")
            logger.error(f"{Colors.RED}Received size: {len(combined_data)}{Colors.RESET}")
    
    # Save received data for inspection
    output_file = Path(f"received_{filename}")
    with open(output_file, 'wb') as f:
        f.write(combined_data)
    logger.info(f"{Colors.YELLOW}Saved received data to: {output_file}{Colors.RESET}")

async def _receive_messages(websocket):
    """Receive and process WebSocket messages."""
    received_chunks = []
    text_messages = []
    total_bytes = 0
    
    while True:
        try:
            message = await websocket.recv()
            total_bytes = _process_message(message, received_chunks, text_messages, total_bytes)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"{Colors.YELLOW}WebSocket connection closed{Colors.RESET}")
            break
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            break
    
    return received_chunks, text_messages, total_bytes

async def test_binary_streaming(filename="test_tone.wav"):
    """Test binary audio streaming and analyze the received data."""
    uri = f"ws://localhost:8000/ws/play/{filename}"
    
    logger.info(f"{Colors.BOLD}{Colors.WHITE}Testing binary streaming from: {uri}{Colors.RESET}")
    logger.info(f"{Colors.WHITE}Expected file: audio_files/{filename}{Colors.RESET}")
    
    # Check if file exists locally for comparison
    local_file = _check_local_file(filename)
    
    logger.info(f"{Colors.BOLD}{Colors.CYAN}--- Connecting to WebSocket ---{Colors.RESET}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"{Colors.GREEN}WebSocket connected successfully{Colors.RESET}")
            
            received_chunks, text_messages, total_bytes = await _receive_messages(websocket)
            
            logger.info(f"{Colors.BOLD}{Colors.CYAN}--- Summary ---{Colors.RESET}")
            logger.info(f"{Colors.MAGENTA}Text messages: {len(text_messages)}{Colors.RESET}")
            logger.info(f"{Colors.BLUE}Binary chunks: {len(received_chunks)}{Colors.RESET}")
            logger.info(f"{Colors.GREEN}Total bytes received: {total_bytes}{Colors.RESET}")
            
            if received_chunks:
                # Verify binary data integrity
                _verify_data_integrity(received_chunks, local_file, filename)
            else:
                logger.error(f"{Colors.RED}{Colors.BOLD}❌ ERROR: No binary data received!{Colors.RESET}")
                
    except Exception as e:
        logger.error(f"Connection error: {e}")

if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "test_tone.wav"
    asyncio.run(test_binary_streaming(filename))
