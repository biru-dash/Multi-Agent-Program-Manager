# File Upload Troubleshooting Guide

## Common Issues and Solutions

### 1. "Cannot connect to backend" Error

**Symptoms:**
- Error message: "Cannot connect to backend at http://localhost:8000"
- Network error in browser console

**Solution:**
1. Make sure backend is running:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload
   ```
2. Verify backend is accessible:
   ```powershell
   # Open in browser or use curl
   curl http://localhost:8000/health
   # Should return: {"status":"healthy",...}
   ```

### 2. CORS Error

**Symptoms:**
- Error in browser console: "CORS policy" or "Access-Control-Allow-Origin"
- Network request shows OPTIONS request failing

**Solution:**
1. Check if your frontend port is in CORS allowed origins (should be automatic now)
2. Backend CORS includes: 8080, 8081, 5173, 3000
3. Restart backend after any CORS config changes

### 3. "Unsupported file type" Error

**Symptoms:**
- File upload fails with "Unsupported file type" message

**Solution:**
- Supported formats: `.txt`, `.json`, `.srt`
- Check file extension is correct (not `.TXT` vs `.txt`)
- Test with sample files from `backend/tests/`:
  - `sample_transcript.txt`
  - `sample_transcript.json`
  - `sample_transcript.srt`

### 4. "File too large" Error

**Symptoms:**
- Error: "File too large. Max size: 50MB"

**Solution:**
- Default max size is 50MB
- Check file size before uploading
- For larger files, increase `MAX_FILE_SIZE_MB` in `backend/.env`

### 5. Upload Succeeds But No Progress

**Symptoms:**
- File uploads successfully (green toast)
- But "Process Transcript" button stays disabled
- `uploadId` is null

**Solution:**
1. Check browser console for errors
2. Verify `handleFilesSelected` is called and `uploadId` is set
3. Check that `uploadResponse.upload_id` exists in API response

### 6. Network Request Fails Silently

**Symptoms:**
- No error message, but upload doesn't work
- Browser console shows failed fetch request

**Debug Steps:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Try uploading a file
4. Look for `/api/upload` request
5. Check:
   - Status code (should be 200)
   - Request URL (should be `http://localhost:8000/api/upload`)
   - Response body
   - Error details

### 7. FormData Not Being Sent

**Symptoms:**
- Request reaches backend but file is empty
- Backend error: "File is required"

**Solution:**
1. Verify `FormData` is created correctly
2. Check `Content-Type` header (should NOT be set manually - browser sets it with boundary)
3. Ensure file is actually appended: `formData.append('file', file)`

## Testing Upload Manually

### Using Browser Console

```javascript
// Test upload directly
const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
const formData = new FormData();
formData.append('file', file);

fetch('http://localhost:8000/api/upload', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(console.log)
.catch(console.error);
```

### Using curl

```powershell
# Test upload with curl
curl -X POST http://localhost:8000/api/upload `
  -F "file=@backend/tests/sample_transcript.txt"
```

### Using Postman/Insomnia

1. POST to `http://localhost:8000/api/upload`
2. Body type: `form-data`
3. Key: `file` (type: File)
4. Select a test file
5. Send

## Verification Checklist

- [ ] Backend server is running on port 8000
- [ ] Frontend is configured with correct API URL (`VITE_API_BASE_URL`)
- [ ] CORS is configured for your frontend port
- [ ] File format is supported (`.txt`, `.json`, `.srt`)
- [ ] File size is under 50MB
- [ ] Browser console shows no errors
- [ ] Network tab shows successful POST to `/api/upload`
- [ ] Backend logs show upload received
- [ ] `uploadId` is set after successful upload

## Debug Mode

Add this to `src/pages/Index.tsx` temporarily for more logging:

```typescript
const handleFilesSelected = async (files: File[]) => {
  console.log('=== UPLOAD DEBUG ===');
  console.log('Files:', files);
  console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000');
  
  if (files.length === 0) {
    console.log('No files selected');
    return;
  }
  
  const file = files[0];
  console.log('Uploading:', {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified
  });
  
  // ... rest of upload code
};
```

## Common Backend Errors

### "File is required"
- Backend didn't receive the file
- Check FormData is sent correctly
- Verify `file` parameter name matches

### "Unsupported file type"
- File extension not in allowed list
- Backend checks: `.txt`, `.json`, `.srt`

### "File too large"
- File exceeds `MAX_FILE_SIZE_MB` (default 50MB)

### 500 Internal Server Error
- Check backend logs for Python exceptions
- Verify upload directory exists: `backend/uploads/`
- Check file permissions

## Still Not Working?

1. **Check Backend Logs:**
   ```powershell
   # Look for errors in backend terminal
   # Should see: "POST /api/upload HTTP/1.1 200 OK"
   ```

2. **Verify API Base URL:**
   ```powershell
   # Check .env file in root
   cat .env
   # Should have: VITE_API_BASE_URL=http://localhost:8000
   ```

3. **Test Backend Directly:**
   ```powershell
   # Health check
   curl http://localhost:8000/health
   
   # Test upload
   curl -X POST http://localhost:8000/api/upload -F "file=@backend/tests/sample_transcript.txt"
   ```

4. **Check Browser Console:**
   - Open DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests
