#!/usr/bin/env python3
"""
Test script to check environment variables and Vonage API connectivity.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_environment():
    """Test environment variables."""
    print("🔍 Testing Environment Variables")
    print("=" * 50)
    
    # Check Vonage variables
    vonage_app_id = os.environ.get("VONAGE_APP_ID")
    vonage_private_key_path = os.environ.get("VONAGE_PRIVATE_KEY_PATH")
    
    print(f"VONAGE_APP_ID: {'✅ Set' if vonage_app_id else '❌ Not Set'}")
    print(f"VONAGE_PRIVATE_KEY_PATH: {'✅ Set' if vonage_private_key_path else '❌ Not Set'}")
    
    # Check OpenAI variables
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY: {'✅ Set' if openai_api_key else '❌ Not Set'}")
    
    # Check if private key file exists
    if vonage_private_key_path:
        if os.path.exists(vonage_private_key_path):
            print(f"Private key file: ✅ Found at {vonage_private_key_path}")
            try:
                with open(vonage_private_key_path, 'r') as f:
                    key_content = f.read()
                    print(f"Private key: ✅ Valid (length: {len(key_content)} chars)")
            except Exception as e:
                print(f"Private key: ❌ Error reading: {e}")
        else:
            print(f"Private key file: ❌ Not found at {vonage_private_key_path}")
    
    # Check HOST_NAME
    host_name = os.environ.get("HOST_NAME", "http://localhost:8000")
    print(f"HOST_NAME: {host_name}")
    
    print("\n📋 Summary:")
    if vonage_app_id and vonage_private_key_path and os.path.exists(vonage_private_key_path):
        print("✅ Vonage integration should work")
    else:
        print("❌ Vonage integration will fail - missing credentials")
    
    if openai_api_key:
        print("✅ OpenAI integration should work")
    else:
        print("❌ OpenAI integration will fail - missing API key")

if __name__ == "__main__":
    test_environment() 