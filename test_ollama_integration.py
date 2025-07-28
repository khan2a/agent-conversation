#!/usr/bin/env python3
"""
Test script for Ollama API integration.
This script tests the Ollama API call format and response handling.
"""

import asyncio
import httpx
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def test_ollama_api():
    """Test Ollama API call."""
    
    print("🔍 Testing Ollama API Integration")
    print("=" * 50)
    
    # Test payload
    test_message = "what is the weather like?"
    
    request_payload = {
        "model": "llama3.2",
        "stream": False,
        "messages": [
            {"role": "user", "content": test_message}
        ]
    }
    
    print(f"📤 Request payload:")
    print(json.dumps(request_payload, indent=2))
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"\n🔄 Sending request to Ollama...")
            response = await client.post(
                "http://localhost:11434/api/chat",
                json=request_payload,
                timeout=60.0
            )
            
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"📥 Response Data:")
                print(json.dumps(response_data, indent=2))
                
                # Extract message content
                if "message" in response_data and "content" in response_data["message"]:
                    ai_response = response_data["message"]["content"]
                    print(f"\n✅ Extracted AI Response: {ai_response}")
                else:
                    print(f"\n❌ Unexpected response format")
                    
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("\n💡 To use Ollama:")
        print("1. Install Ollama: https://ollama.ai/")
        print("2. Pull the model: ollama pull llama3.2")
        print("3. Start Ollama: ollama serve")
        print("4. Ollama will be available at http://localhost:11434")

async def test_stts_ollama_endpoint():
    """Test the STTS Ollama endpoint."""
    
    print("\n🧪 Testing STTS Ollama Endpoint")
    print("=" * 50)
    
    test_payload = {
        "uuid": "test-call-ollama",
        "conversation_uuid": "test-conv-ollama", 
        "speech": {
            "results": [
                {"text": "what is the weather like?", "confidence": "0.95"}
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/stts/ollama",
                json=test_payload,
                timeout=70.0  # Longer timeout for Ollama
            )
            
            print(f"📥 Response Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📥 NCCO Response: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all tests."""
    await test_ollama_api()
    await test_stts_ollama_endpoint()

if __name__ == "__main__":
    asyncio.run(main()) 