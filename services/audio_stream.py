import os
import asyncio
import aiofiles
import wave
import logging
import subprocess
import tempfile
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect

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

# Set up logger
logger = logging.getLogger(__name__)


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
        
        # Validate file and get streaming parameters
        streaming_params = await _validate_and_get_streaming_params(websocket, file_path, audio_dir, filename)
        if not streaming_params:
            return
        
        # Use the actual file path (which may be converted file for MP3)
        actual_file_path = streaming_params.get('file_path', file_path)
            
        # Stream the file using the adapted code structure
        await _stream_audio_file(websocket, actual_file_path, streaming_params, filename)
        
    except WebSocketDisconnect:
        # Client disconnected cleanly
        pass
    except FileNotFoundError:
        # Log error but don't send text to client
        logger.error(f"{Colors.RED}Error: Audio file '{filename}' not found.{Colors.RESET}")
    except Exception as e:
        # Log error but don't send text to client  
        logger.error(f"{Colors.RED}Error during playback: {str(e)}{Colors.RESET}")


async def _validate_and_get_streaming_params(websocket: WebSocket, file_path: Path, audio_dir: Path, filename: str) -> dict | None:
    """Validate file and return streaming parameters."""
    # Check if file exists and is in the allowed directory
    if not file_path.exists():
        # Close connection instead of sending text error
        await websocket.close(code=1003, reason="File not found")
        return None
        
    # Check if it's actually within the audio directory (security check)
    try:
        file_path.resolve().relative_to(audio_dir.resolve())
    except ValueError:
        # Close connection instead of sending text error
        await websocket.close(code=1003, reason="Invalid file path")
        return None
    
    # Check file extension for supported formats
    supported_formats = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    if file_path.suffix.lower() not in supported_formats:
        # Send error as binary data or close connection instead of text
        await websocket.close(code=1003, reason="Unsupported audio format")
        return None
    
    # Convert MP3 to L16 if needed
    if file_path.suffix.lower() == '.mp3':
        converted_path = await _convert_mp3_to_l16(file_path, filename)
        if not converted_path:
            await websocket.close(code=1003, reason="MP3 conversion failed")
            return None
        # Update file_path to point to converted file
        file_path = converted_path
    
    streaming_params = _calculate_streaming_parameters(filename, file_path)
    streaming_params['file_path'] = file_path  # Include actual file path for streaming
    return streaming_params


def _calculate_streaming_parameters(filename: str, file_path: Path) -> dict:
    """Calculate streaming parameters based on filename and file properties."""
    # Default values for audio streaming
    sample_rate = 8000  # Default to 8kHz
    bit_depth = 16     # 16-bit audio
    channels = 1       # Mono
    chunk_duration = 0.02  # 20ms chunks
    
    # Check filename for sample rate indication and calculate parameters
    if "16000" in filename:
        sample_rate = 16000
        # For 16,000 Hz, mono, 16-bit audio, with 20ms chunks:
        # Chunk Size = (Sample Rate × Bit Depth × Channels × Chunk Duration) / 8
        # Chunk Size = (16,000 × 16 × 1 × 0.02) / 8 = 640 bytes
        # Bitrate = 16,000 × 16 × 1 = 256,000 bits/sec = 256 kbps
        # Sleep Time = 20ms (50 chunks/sec)
        chunk_size = 640
        sleep_time = 0.02  # 20ms between chunks (50 chunks/sec)
        logger.info(f"{Colors.CYAN}16kHz mode: chunk_size={chunk_size} bytes, sleep_time={sleep_time}s, bitrate=256kbps{Colors.RESET}")
    elif "8000" in filename:
        sample_rate = 8000
        # For 8,000 Hz, mono, 16-bit audio, with 20ms chunks:
        # Chunk Size = (Sample Rate × Bit Depth × Channels × Chunk Duration) / 8
        # Chunk Size = (8,000 × 16 × 1 × 0.02) / 8 = 320 bytes
        # Bitrate = 8,000 × 16 × 1 = 128,000 bits/sec = 128 kbps
        # Sleep Time = 20ms (50 chunks/sec)
        chunk_size = 320
        sleep_time = 0.02  # 20ms between chunks (50 chunks/sec)
        logger.info(f"{Colors.BLUE}8kHz mode: chunk_size={chunk_size} bytes, sleep_time={sleep_time}s, bitrate=128kbps{Colors.RESET}")
    else:
        # Default calculation: assume 8kHz for unknown files
        chunk_size = int((sample_rate * bit_depth * channels * chunk_duration) / 8)
        sleep_time = chunk_duration
        logger.info(f"{Colors.YELLOW}Default mode: chunk_size={chunk_size} bytes, sleep_time={sleep_time}s, sample_rate={sample_rate}Hz{Colors.RESET}")
    
    # For WAV files, verify actual audio properties match filename expectations
    if file_path.suffix.lower() == '.wav':
        _analyze_wav_properties(filename, file_path, sample_rate, channels, bit_depth)
    
    return {
        'chunk_size': chunk_size,
        'sleep_time': sleep_time,
        'sample_rate': sample_rate
    }


def _analyze_wav_properties(filename: str, file_path: Path, expected_rate: int, expected_channels: int, expected_bit_depth: int):
    """Analyze WAV file properties and log comparison with expected values."""
    try:
        with wave.open(str(file_path), "rb") as wf:
            actual_channels = wf.getnchannels()
            actual_rate = wf.getframerate()
            actual_width = wf.getsampwidth()
            duration = wf.getnframes() / actual_rate
            
            logger.info(f"{Colors.MAGENTA}WAV file analysis for {filename}:{Colors.RESET}")
            logger.info(f"{Colors.MAGENTA}  Actual: Rate={actual_rate}Hz, Channels={actual_channels}, Width={actual_width} bytes{Colors.RESET}")
            logger.info(f"{Colors.MAGENTA}  Expected: Rate={expected_rate}Hz, Channels={expected_channels}, Width={expected_bit_depth//8} bytes{Colors.RESET}")
            logger.info(f"{Colors.MAGENTA}  Duration: {duration:.2f} seconds{Colors.RESET}")
            
            # Override chunk calculation if WAV properties differ significantly
            if actual_rate != expected_rate:
                logger.warning(f"{Colors.YELLOW}  WARNING: Filename suggests {expected_rate}Hz but WAV is {actual_rate}Hz{Colors.RESET}")
                # Optionally recalculate based on actual properties
                # chunk_size = int((actual_rate * actual_width * 8 * actual_channels * chunk_duration) / 8)
    except Exception as e:
        logger.error(f"{Colors.RED}Could not read WAV properties for {filename}: {e}, using filename-based settings{Colors.RESET}")


async def _convert_mp3_to_l16(file_path: Path, filename: str) -> Path | None:
    """Convert MP3 file to L16 (raw PCM) format using ffmpeg."""
    try:
        # Determine sample rate from filename
        sample_rate = 16000  if "16000" in filename else 8000

        logger.info(f"{Colors.YELLOW}Converting MP3 to L16: {filename} at {sample_rate}Hz{Colors.RESET}")
        
        # Create temporary file for converted audio
        temp_dir = Path(tempfile.gettempdir())
        temp_filename = f"converted_{filename.replace('.mp3', '')}_l16_{sample_rate}.raw"
        temp_path = temp_dir / temp_filename
        
        # ffmpeg command to convert MP3 to raw PCM (L16)
        # -f s16le: 16-bit signed little-endian PCM
        # -ac 1: mono (1 channel)
        # -ar: sample rate
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(file_path),           # Input MP3 file
            '-f', 's16le',                  # Output format: 16-bit signed little-endian PCM
            '-ac', '1',                     # Mono (1 channel)
            '-ar', str(sample_rate),        # Sample rate
            '-y',                           # Overwrite output file if it exists
            str(temp_path)                  # Output raw PCM file
        ]
        
        # Run ffmpeg conversion asynchronously
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.error(f"{Colors.RED}ffmpeg conversion timed out for {filename}{Colors.RESET}")
            return None
        
        if process.returncode != 0:
            logger.error(f"{Colors.RED}ffmpeg conversion failed for {filename}:{Colors.RESET}")
            logger.error(f"{Colors.RED}  stderr: {stderr.decode()}{Colors.RESET}")
            return None
        
        # Verify the converted file exists and has content
        if not temp_path.exists() or temp_path.stat().st_size == 0:
            logger.error(f"{Colors.RED}Converted file is empty or doesn't exist: {temp_path}{Colors.RESET}")
            return None
        
        file_size = temp_path.stat().st_size
        duration_seconds = file_size / (sample_rate * 2)  # 2 bytes per sample for 16-bit
        
        logger.info(f"{Colors.GREEN}MP3 conversion successful:{Colors.RESET}")
        logger.info(f"{Colors.GREEN}  Output: {temp_path}{Colors.RESET}")
        logger.info(f"{Colors.GREEN}  Size: {file_size} bytes, Duration: {duration_seconds:.2f}s{Colors.RESET}")
        logger.info(f"{Colors.GREEN}  Format: {sample_rate}Hz, 16-bit, mono, raw PCM{Colors.RESET}")
        
        return temp_path
        
    except FileNotFoundError:
        logger.error(f"{Colors.RED}ffmpeg not found. Please install ffmpeg to convert MP3 files.{Colors.RESET}")
        return None
    except Exception as e:
        logger.error(f"{Colors.RED}Error converting MP3 to L16: {e}{Colors.RESET}")
        return None


async def _stream_audio_file(websocket: WebSocket, file_path: Path, streaming_params: dict, filename: str):
    """Stream the audio file data to the WebSocket."""
    chunk_size = streaming_params['chunk_size']
    sleep_time = streaming_params['sleep_time']
    
    # Check if we need to skip WAV header for raw PCM streaming
    header_skip = 0
    if file_path.suffix.lower() == '.wav':
        # WAV files have a 44-byte header that should be skipped for raw PCM
        header_skip = 44
        logger.info(f"{Colors.CYAN}WAV file detected: skipping {header_skip} byte header for raw PCM streaming{Colors.RESET}")
    elif file_path.suffix.lower() == '.raw':
        # Raw PCM files (converted from MP3) have no header
        logger.info(f"{Colors.CYAN}Raw PCM file detected: no header to skip, streaming directly{Colors.RESET}")
    
    async with aiofiles.open(file_path, 'rb') as audio_file:
        # Skip WAV header if present
        if header_skip > 0:
            header_data = await audio_file.read(header_skip)
            logger.info(f"{Colors.CYAN}Skipped WAV header: {header_skip} bytes, header starts with: {header_data[:8]}{Colors.RESET}")
        
        chunk_count = 0
        bytes_sent = 0
        
        while True:
            # Check if client is still connected
            if await _check_client_disconnected(websocket):
                break
            
            # Read chunk
            chunk = await audio_file.read(chunk_size)
            if not chunk:
                break
            
            chunk_count += 1
            bytes_sent += len(chunk)
            
            # Debug logging to verify binary data (server-side only)
            if chunk_count == 1:
                logger.info(f"{Colors.GREEN}First PCM chunk: {len(chunk)} bytes, type: {type(chunk)}, first 10 bytes: {chunk[:10]}{Colors.RESET}")
            
            # Send binary chunk (raw PCM data, no WAV header)
            await websocket.send_bytes(chunk)
            
            # Sleep based on audio properties for realistic streaming rate
            await asyncio.sleep(sleep_time)
    
    # Clean up temporary files for converted MP3s
    if file_path.suffix.lower() == '.raw' and 'converted_' in file_path.name:
        try:
            file_path.unlink()  # Delete temporary converted file
            logger.info(f"{Colors.BLUE}Cleaned up temporary file: {file_path.name}{Colors.RESET}")
        except Exception as e:
            logger.warning(f"{Colors.YELLOW}Could not clean up temporary file {file_path}: {e}{Colors.RESET}")
    
    # Don't send completion text - just close cleanly
    _log_streaming_completion(filename, bytes_sent, chunk_count, chunk_size, sleep_time)


async def _check_client_disconnected(websocket: WebSocket) -> bool:
    """Check if the WebSocket client has disconnected."""
    try:
        # Try to receive any messages (including ping/close)
        message = await asyncio.wait_for(websocket.receive(), timeout=0.0001)
        return message.get("type") == "websocket.disconnect"
    except asyncio.TimeoutError:
        # No message received, continue streaming
        return False
    except WebSocketDisconnect:
        return True


def _log_streaming_completion(filename: str, bytes_sent: int, chunk_count: int, chunk_size: int, sleep_time: float):
    """Log streaming completion statistics."""
    chunks_per_second = 1 / sleep_time if sleep_time > 0 else 0
    bytes_per_second = chunk_size * chunks_per_second
    bitrate_kbps = (bytes_per_second * 8) / 1000
    
    logger.info(f"{Colors.BOLD}{Colors.WHITE}Finished streaming '{filename}':{Colors.RESET}")
    logger.info(f"{Colors.GREEN}  Total: {bytes_sent} bytes in {chunk_count} chunks{Colors.RESET}")
    logger.info(f"{Colors.BLUE}  Rate: {chunks_per_second:.0f} chunks/sec, {bytes_per_second:.0f} bytes/sec{Colors.RESET}")
    logger.info(f"{Colors.CYAN}  Effective bitrate: {bitrate_kbps:.0f} kbps{Colors.RESET}")
