#!/usr/bin/env python3
"""
Test script for the async STTS implementation.
This script simulates a POST request to the STTS endpoint to verify the async pattern works.
"""

import asyncio
import httpx
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def test_async_stts():
    """Test the async STTS endpoint."""
    
    # Test payload simulating a speech input callback
    test_payload = {
        "uuid": "test-call-uuid-12345",
        "conversation_uuid": "test-conversation-uuid-67890",
        "speech": {
            "results": [
                {
                    "text": "Hello, how are you?",
                    "confidence": "0.95"
                }
            ]
        },
        "status": "completed"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test the STTS endpoint
            response = await client.post(
                "http://localhost:8000/stts/openai",
                json=test_payload,
                timeout=10.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            if response.status_code == 204:
                print("✅ SUCCESS: Received HTTP 204 (No Content) as expected for async processing")
            else:
                print(f"❌ UNEXPECTED: Received status {response.status_code}")
                print(f"Response body: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

async def test_get_stts():
    """Test the GET STTS endpoint."""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/stts/openai")
            
            print(f"GET Response status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS: GET request returned NCCO: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ UNEXPECTED GET status: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR in GET test: {e}")

async def main():
    """Run all tests."""
    print("🧪 Testing Async STTS Implementation")
    print("=" * 50)
    
    print("\n1. Testing GET /stts/openai (should return initial NCCO)")
    await test_get_stts()
    
    print("\n2. Testing POST /stts/openai (should return HTTP 204)")
    await test_async_stts()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 