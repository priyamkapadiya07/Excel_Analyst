"""
Configuration settings for AI Excel Analyst.
Loads settings from environment variables with sensible defaults.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file if available
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Upload constraints
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# AI Settings
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Preview constraints
DEFAULT_PREVIEW_ROWS = 10
MAX_PREVIEW_ROWS = 100
