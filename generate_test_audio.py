#!/usr/bin/env python3
"""
Generate a simple test audio file for WebSocket streaming tests.
This creates a short sine wave audio file in WAV format.
"""

import wave
import struct
import math
import sys
from pathlib import Path

def generate_sine_wave(frequency=440, duration=3, sample_rate=44100, amplitude=0.3):
    """Generate a sine wave audio signal."""
    frames = []
    for i in range(int(duration * sample_rate)):
        # Generate sine wave sample
        sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
        # Convert to 16-bit integer
        sample = int(sample * 32767)
        # Pack as little-endian 16-bit integer
        frames.append(struct.pack('<h', sample))
    return b''.join(frames)

def create_test_audio():
    """Create a test audio file in the audio_files directory."""
    audio_dir = Path("audio_files")
    audio_dir.mkdir(exist_ok=True)
    
    output_file = audio_dir / "test_tone.wav"
    
    # Generate a 3-second 440Hz sine wave (A4 note)
    print("Generating test audio: 440Hz sine wave, 3 seconds...")
    audio_data = generate_sine_wave(frequency=440, duration=3)
    
    # Write WAV file
    with wave.open(str(output_file), 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(44100)  # 44.1kHz
        wav_file.writeframes(audio_data)
    
    print(f"Created test audio file: {output_file}")
    print(f"File size: {output_file.stat().st_size} bytes")
    print("To test: connect to ws://localhost:8000/ws/play/test_tone.wav")

if __name__ == "__main__":
    create_test_audio()
