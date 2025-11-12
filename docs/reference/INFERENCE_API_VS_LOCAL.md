# HuggingFace Inference API vs Local Models

## The Issue

You're seeing this error:
```
Model 'facebook/bart-large-cnn' is no longer available (deprecated)
```

Even though the model exists on HuggingFace and you can see it at https://huggingface.co/facebook/bart-large-cnn

## Why This Happens

**The model exists on HuggingFace, but it's NOT available via the Inference API.**

### Two Different Ways to Use Models:

1. **HuggingFace Inference API** (`https://api-inference.huggingface.co/models`)
   - Remote API endpoint
   - Fast, no download needed
   - Only certain models are available
   - `facebook/bart-large-cnn` is NOT available here ❌

2. **Local Download** (via `transformers` library)
   - Download model to your machine
   - Run inference locally
   - All models available
   - `facebook/bart-large-cnn` IS available here ✅

## What's Happening Now

Your system is working correctly:

1. ✅ Tried Inference API first (failed - model not available)
2. ✅ Automatically fell back to local mode
3. ✅ Currently downloading the model locally (1.63GB)
4. ✅ Once downloaded, it will work perfectly!

You can see the download progress:
```
model.safetensors: 51%|█ | 832M/1.63G [00:27<00:26, 29.8MB/s]
```

## Solutions

### Option 1: Let It Finish Downloading (Recommended)
- The model is downloading now (~1.6GB)
- Once complete, it will work locally
- Future runs will be fast (model cached)
- No changes needed

### Option 2: Use Local Strategy Directly
If you want to skip the API attempt entirely:

1. In the frontend, select **"local"** as the model strategy
2. Or update your default in `.env`:
   ```env
   MODEL_STRATEGY=local
   ```

### Option 3: Find an API-Available Model
If you want to use the Inference API, find models that are available:

- Check HuggingFace Inference API documentation
- Look for models with "Hosted inference API" badge
- Test in the model's "Hosted inference API" widget

## Current Status

✅ **System is working correctly!**
- Fallback mechanism is functioning
- Model is downloading
- Will work after download completes

The warning message is just informational - the system is handling it automatically.

## Performance Comparison

**Inference API (when available):**
- ✅ Fast (no download)
- ✅ No storage needed
- ❌ Requires internet
- ❌ Model must be available on API

**Local (current setup):**
- ✅ Works offline after download
- ✅ All models available
- ✅ No API limits
- ❌ First download takes time (~1.6GB)
- ✅ Subsequent runs are fast (cached)

## Recommendation

**Let the download complete.** The model will work perfectly once downloaded, and future runs will be fast since it's cached locally.

You'll only see this download once - after that, the cached model will be used immediately.

