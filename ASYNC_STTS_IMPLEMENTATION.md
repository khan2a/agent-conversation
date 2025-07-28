# Async STTS Implementation

## Overview

The Speech-to-Text Service (STTS) has been updated to implement an asynchronous response pattern to prevent delays in returning NCCO responses. This implementation addresses the issue where `generate_speech_response_ncco()` could take longer to generate responses, causing delays.

## Key Changes

### 1. Modified `handle_stts_request()` Function

The function now implements the following pattern for POST requests:

1. **Extract Call UUID**: Saves the `uuid` from the incoming request JSON (different from `conversation_uuid`)
2. **Immediate Response**: Returns HTTP 204 (No Content) immediately to acknowledge receipt
3. **Async Processing**: Proceeds with generating speech NCCO in the background
4. **Call Update**: Once NCCO is generated, updates the call using Vonage Voice API

### 2. New Async Functions

#### `async_process_speech_and_update_call()`
- Handles the asynchronous processing of speech results
- Generates NCCO using `generate_speech_response_ncco()`
- Updates the call via `update_call_with_ncco()`

#### `update_call_with_ncco()`
- Makes PUT request to `https://api.nexmo.com/v1/calls/:uuid`
- Uses JWT authentication with Vonage credentials
- Sends transfer action with NCCO payload

### 3. Updated Dependencies

Added new dependencies to `requirements.txt`:
- `httpx>=0.24.0` - For async HTTP requests
- `PyJWT>=2.8.0` - For JWT token generation
- `cryptography>=41.0.0` - For JWT signing

## Environment Variables Required

The following environment variables must be set for the Vonage API integration:

```bash
VONAGE_APP_ID=your_vonage_app_id
VONAGE_PRIVATE_KEY_PATH=/path/to/your/private.key
```

## API Flow

### POST Request to `/stts/{agent_type}`

1. **Request**: Speech input callback with `uuid` and `conversation_uuid`
2. **Immediate Response**: HTTP 204 (No Content)
3. **Background Processing**:
   - Store callback data
   - Process speech results
   - Generate AI response
   - Update call with new NCCO

### Vonage API Call

The call is updated using:
```http
PUT https://api.nexmo.com/v1/calls/{call_uuid}
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "action": "transfer",
  "destination": {
    "type": "ncco",
    "ncco": [
      {
        "action": "talk",
        "text": "AI response",
        "style": 0,
        "language": "en-GB",
        "bargeIn": true
      },
      {
        "action": "input",
        "eventUrl": ["event_url"],
        "type": ["speech"]
      }
    ]
  }
}
```

## Testing

Use the provided test script to verify the implementation:

```bash
python test_async_stts.py
```

The test script will:
1. Test GET requests (should return initial NCCO)
2. Test POST requests (should return HTTP 204)

## Benefits

1. **Reduced Latency**: Immediate HTTP 204 response prevents timeouts
2. **Better User Experience**: No delays in call flow
3. **Scalability**: Async processing allows handling multiple requests concurrently
4. **Reliability**: Background processing with proper error handling

## Error Handling

- Missing call UUID returns HTTP 400
- Invalid JSON payload returns HTTP 400
- Vonage API errors are logged but don't affect the initial response
- Async processing errors are logged separately

## Backward Compatibility

- GET requests still return NCCO directly (no changes)
- All existing endpoints remain functional
- New async pattern only affects POST requests to STTS endpoints 