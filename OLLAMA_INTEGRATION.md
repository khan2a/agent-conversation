# Ollama Integration

## Overview

The application now supports Ollama as an alternative AI agent for generating responses. Ollama provides local LLM inference capabilities.

## Setup

### 1. Install Ollama

Visit [https://ollama.ai/](https://ollama.ai/) and follow the installation instructions for your platform.

### 2. Pull the Model

```bash
ollama pull llama3.2
```

### 3. Start Ollama

```bash
ollama serve
```

Ollama will be available at `http://localhost:11434`

## API Integration

### Request Format

The application sends requests to Ollama using the chat API:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2", 
  "stream": false,
  "messages": [
    { "role": "user", "content": "why is the sky blue?" }
  ]
}'
```

### Response Format

Ollama returns responses in this format:

```json
{
  "model": "llama3.2",
  "created_at": "2025-07-28T23:09:14.503359Z",
  "message": {
    "role": "assistant", 
    "content": "The sky appears blue to our eyes because of a phenomenon called scattering..."
  },
  "done_reason": "stop",
  "done": true,
  "total_duration": 39902475667,
  "load_duration": 68398475,
  "prompt_eval_count": 31,
  "prompt_eval_duration": 313700161,
  "eval_count": 341,
  "eval_duration": 39517633629
}
```

The application extracts `message.content` and uses it as the AI response.

## Usage

### Endpoint

Use the `/stts/ollama` endpoint instead of `/stts/openai`:

```bash
curl -X POST http://localhost:8000/stts/ollama \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "call-uuid",
    "conversation_uuid": "conv-uuid",
    "speech": {
      "results": [
        {"text": "what is the weather like?", "confidence": "0.95"}
      ]
    }
  }'
```

### Performance Notes

⚠️ **Important**: Ollama responses can take up to **40 seconds** to complete. This is normal for local LLM inference.

- The application uses a 60-second timeout for Ollama requests
- Users will experience longer response times compared to OpenAI
- Consider this when choosing between OpenAI and Ollama for production use

## Error Handling

If Ollama is not running or unavailable:

1. The application will log connection errors
2. Return the fallback response: `"I am sorry, could you repeat yourself again?"`
3. Continue processing without crashing

## Testing

Use the provided test script to verify Ollama integration:

```bash
python test_ollama_integration.py
```

This will:
1. Test direct Ollama API calls
2. Test the STTS Ollama endpoint
3. Provide setup instructions if Ollama is not available

## Configuration

### Model Selection

The current implementation uses `llama3.2`. To use a different model:

1. Pull the desired model: `ollama pull <model-name>`
2. Update the model name in `query_ollama()` function in `main.py`

### Available Models

Common Ollama models include:
- `llama3.2` - Llama 3.2 (default)
- `llama3.1` - Llama 3.1
- `mistral` - Mistral 7B
- `codellama` - Code Llama
- `llama2` - Llama 2

## Benefits

1. **Local Processing** - No external API calls required
2. **Privacy** - Data stays on your local machine
3. **Cost Effective** - No per-token charges
4. **Customizable** - Use any compatible model

## Limitations

1. **Performance** - Slower than cloud APIs (40+ seconds)
2. **Resource Usage** - Requires significant RAM and CPU
3. **Model Quality** - May not match cloud API quality
4. **Setup Complexity** - Requires local installation and model downloads

## Troubleshooting

### Connection Errors

If you see "All connection attempts failed":

1. Ensure Ollama is running: `ollama serve`
2. Check if port 11434 is available: `curl http://localhost:11434/api/tags`
3. Verify model is pulled: `ollama list`

### Slow Responses

- 40+ second response times are normal for local LLM inference
- Consider using a more powerful machine for better performance
- Try smaller models for faster responses

### Memory Issues

- Ollama requires significant RAM (8GB+ recommended)
- Close other applications to free memory
- Use smaller models if memory is limited 