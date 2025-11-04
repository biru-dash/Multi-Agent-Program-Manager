"""Configuration settings for the MIA application."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Literal
from pathlib import Path
import os

# Get the backend directory (settings.py is at backend/app/config/settings.py)
# So: __file__ -> backend/app/config/settings.py
#     parent.parent.parent -> backend/
BACKEND_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# Debug: Check path resolution
print(f"[DEBUG] Looking for .env at: {ENV_FILE.absolute()}")
print(f"[DEBUG] File exists: {ENV_FILE.exists()}")

# Pre-process .env file to remove BOM and fix spacing
if ENV_FILE.exists():
    try:
        # Read the file with BOM handling
        with open(ENV_FILE, 'r', encoding='utf-8-sig') as f:  # utf-8-sig strips BOM
            content = f.read()
        
        # Fix spacing around = signs and strip empty lines
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Remove spaces around = sign
            if '=' in line:
                key, value = line.split('=', 1)
                lines.append(f"{key.strip()}={value.strip()}")
        
        # Write cleaned content back
        cleaned_content = '\n'.join(lines) + '\n'
        with open(ENV_FILE, 'w', encoding='utf-8') as f:  # Write without BOM
            f.write(cleaned_content)
        
        print("[DEBUG] Cleaned .env file (removed BOM, fixed spacing)")
        
        # Also set as environment variables as fallback
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if key == 'HUGGINGFACE_TOKEN':
                    print(f"[DEBUG] Set HUGGINGFACE_TOKEN env var: {value[:10]}...")
    except Exception as e:
        print(f"[DEBUG] Warning: Could not pre-process .env file: {e}")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Hugging Face Configuration - explicitly map HUGGINGFACE_TOKEN env var
    huggingface_token: str = Field(..., env="HUGGINGFACE_TOKEN")
    
    # Model Strategy: local, remote, or hybrid
    model_strategy: Literal["local", "remote", "hybrid"] = "hybrid"
    
    # Directory Configuration
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    
    # File Upload Limits
    max_file_size_mb: int = 50
    
    # Model Names
    summarization_model: str = "knkarthick/bart-large-xsum-samsum"
    ner_model: str = "dslim/bert-base-NER"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8-sig",  # Use utf-8-sig to automatically strip BOM
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from env file
    )


print("[DEBUG] Creating Settings instance...")
try:
    settings = Settings()
    print("[DEBUG] Settings created successfully!")
    print(f"[DEBUG] Token loaded: {settings.huggingface_token[:10]}...")
except Exception as e:
    print(f"[DEBUG] Error creating settings: {e}")
    print(f"[DEBUG] Error type: {type(e)}")
    import traceback
    traceback.print_exc()
    raise
