#!/usr/bin/env python3
"""
Test script to debug Vonage API calls.
"""

import os
import jwt
import time
import uuid
import json
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_vonage_api():
    """Test Vonage API call with detailed debugging."""
    
    print("🔍 Testing Vonage API Call")
    print("=" * 50)
    
    # Get credentials
    vonage_app_id = os.environ.get("VONAGE_APP_ID")
    vonage_private_key_path = os.environ.get("VONAGE_PRIVATE_KEY_PATH")
    
    print(f"VONAGE_APP_ID: {vonage_app_id}")
    print(f"VONAGE_PRIVATE_KEY_PATH: {vonage_private_key_path}")
    
    if not vonage_app_id or not vonage_private_key_path:
        print("❌ Missing Vonage credentials")
        return
    
    if not os.path.exists(vonage_private_key_path):
        print(f"❌ Private key file not found: {vonage_private_key_path}")
        return
    
    # Read private key
    with open(vonage_private_key_path, 'r') as f:
        private_key = f.read()
    
    print(f"✅ Private key loaded (length: {len(private_key)} chars)")
    
    # Create JWT token
    payload = {
        'application_id': vonage_app_id,
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600,  # 1 hour expiry
        'jti': str(uuid.uuid4())
    }
    
    token = jwt.encode(payload, private_key, algorithm='RS256')
    print(f"✅ JWT token generated: {token[:50]}...")
    
    # Test payload
    test_ncco = [
        {
            "action": "talk",
            "text": "Hello, this is a test response.",
            "style": 0,
            "language": "en-GB",
            "bargeIn": True
        },
        {
            "action": "input",
            "eventUrl": ["https://khan2a.ngrok.io/stts/openai"],
            "type": ["speech"]
        }
    ]
    
    request_payload = {
        "action": "transfer",
        "destination": {
            "type": "ncco",
            "ncco": test_ncco
        }
    }
    
    print(f"📤 Request payload:")
    print(json.dumps(request_payload, indent=2))
    
    # Test with a fake call UUID
    test_call_uuid = "test-call-123"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"https://api.nexmo.com/v1/calls/{test_call_uuid}",
                json=request_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            print(f"📥 Response Headers: {dict(response.headers)}")
            print(f"📥 Response Body: {response.text}")
            
            if response.status_code == 200:
                print("✅ API call successful!")
            else:
                print(f"❌ API call failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error making API call: {e}")

if __name__ == "__main__":
    asyncio.run(test_vonage_api()) 