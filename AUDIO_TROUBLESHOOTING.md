# Audio Streaming Troubleshooting Guide

## Why You Might Get Silence Instead of Audio

### 1. **Web Browser Audio Handling**
**Problem**: Raw audio file bytes cannot be directly played by web browsers
**Solution**: The audio data needs to be reconstructed as a proper audio file

### 2. **MIME Type Issues**
**Problem**: Incorrect MIME type when creating the audio blob
**Solution**: Use correct MIME type based on file extension

### 3. **Incomplete Audio Data**
**Problem**: Audio streaming might be interrupted or incomplete
**Solution**: Ensure all chunks are received before attempting playback

### 4. **Browser Security Restrictions**
**Problem**: Many browsers require user interaction before playing audio
**Solution**: Click the "Play Received Audio" button after streaming

## Testing Steps

### Step 1: Generate Test Audio
```bash
python generate_test_audio.py
```
This creates `audio_files/test_tone.wav` - a 3-second 440Hz tone.

### Step 2: Stream the Test File
1. Open `test_client.html` in your browser
2. Enter `test_tone.wav` in the filename field
3. Click "Play Audio File"
4. Wait for streaming to complete (check logs)

### Step 3: Play the Received Audio
1. Click "Play Received Audio" button
2. You should hear a 440Hz tone for 3 seconds

## Debugging Checklist

### ✅ Server Side
- [ ] File exists in `audio_files/` directory
- [ ] File has supported extension (.wav, .mp3, etc.)
- [ ] Server logs show successful streaming
- [ ] All bytes are sent (check "Sent X bytes total" message)

### ✅ Client Side
- [ ] WebSocket connection successful
- [ ] All audio chunks received
- [ ] Audio blob created with correct MIME type
- [ ] No console errors in browser
- [ ] User clicked "Play Received Audio" button

## Common Issues & Solutions

### Issue 1: "File not found" error
**Cause**: File not in `audio_files/` directory
**Solution**: Place audio files directly in `audio_files/` folder

### Issue 2: WebSocket connection fails
**Cause**: Server not running or wrong URL
**Solution**: Ensure server is running on `localhost:8000`

### Issue 3: Audio blob created but no sound
**Cause**: 
- Wrong MIME type
- Browser audio policy
- Corrupted audio data

**Solutions**:
- Check browser console for errors
- Try different audio file formats
- Ensure user interaction before playing

### Issue 4: Partial audio streaming
**Cause**: WebSocket disconnects early
**Solution**: Check server logs and network stability

## Advanced Debugging

### Check Received Audio Data
```javascript
// In browser console after streaming
console.log('Audio chunks:', audioChunks.length);
console.log('Total bytes:', audioChunks.reduce((sum, chunk) => sum + chunk.size, 0));
console.log('Audio blob:', receivedAudioBlob);
```

### Verify Audio File Integrity
```bash
# Check if test file plays normally
ffplay audio_files/test_tone.wav  # If you have ffmpeg installed
```

### Network Analysis
- Open browser DevTools → Network tab
- Look for WebSocket connection and data transfer
- Check for any dropped connections or errors

## Expected Behavior

1. **Connection**: WebSocket connects successfully
2. **Streaming**: Binary chunks received (shown in log)
3. **Completion**: "Finished playback" message
4. **Playback**: Audio plays when "Play Received Audio" is clicked

## File Format Notes

- **WAV**: Best for testing (uncompressed, widely supported)
- **MP3**: Good compression, universally supported
- **OGG**: Good for web, may not work in all browsers
- **M4A/AAC**: Good quality, supported in modern browsers

## Browser Compatibility

- ✅ Chrome: Full support
- ✅ Firefox: Full support
- ✅ Safari: Full support (may need user interaction)
- ✅ Edge: Full support
