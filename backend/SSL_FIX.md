# SSL Certificate Fix for Windows

## Problem
When downloading models from Hugging Face, you may encounter SSL certificate verification errors:
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate
```

## Solutions

### Option 1: Install Python Certificates (Recommended)
```powershell
# Install certifi package
pip install certifi

# Get certificate location
python -c "import certifi; print(certifi.where())"

# Set environment variable (add to your .env file or PowerShell profile)
$env:SSL_CERT_FILE = "C:\Users\YourUsername\AppData\Local\Programs\Python\Python313\Lib\site-packages\certifi\cacert.pem"
```

### Option 2: Update Certificates Manually
```powershell
# Download latest certificates
curl https://curl.se/ca/cacert.pem -o cacert.pem

# Set environment variable
$env:SSL_CERT_FILE = "C:\path\to\cacert.pem"
```

### Option 3: Disable SSL Verification (Development Only)
**Warning**: This is NOT secure for production use!

The code will automatically attempt to work around SSL issues, but for a permanent fix, add to your `.env` file:
```env
CURL_CA_BUNDLE=
REQUESTS_CA_BUNDLE=
HF_HUB_DISABLE_SSL_WARNING=1
```

Or set environment variables before running:
```powershell
$env:CURL_CA_BUNDLE = ""
$env:REQUESTS_CA_BUNDLE = ""
uvicorn app.main:app --reload
```

### Option 4: Use Hugging Face Hub with SSL Disabled (Code-level)
The code now automatically detects SSL errors and retries with SSL verification disabled as a fallback.

## Verification
After applying a fix, restart the server and try processing a transcript. The SSL warnings should be resolved.

## Note
The embedding model (for topic segmentation) is optional. If SSL issues prevent it from loading, preprocessing will continue without topic segmentation.
