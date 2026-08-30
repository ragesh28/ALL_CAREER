"""
Configuration and settings for ALL_CAREER Image-to-Job Extraction Pipeline.
"""
import os

# ── Processing & Threshold Settings ──
MIN_JOB_SIGNAL_SCORE = 5          # Minimum score for image to pass stage 1 filter
DUPLICATE_HASH_THRESHOLD = 6      # Hamming distance threshold for perceptual hash dedup
MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150
MAX_IMAGE_DIMENSION = 4096

# ── Multi-pass OCR Configuration ──
OCR_UPSCALING_FACTOR = 2.0
OCR_MIN_CONFIDENCE = 0.40
ENABLE_GOOGLE_VISION_FALLBACK = os.environ.get("ENABLE_GOOGLE_VISION_FALLBACK", "false").lower() == "true"
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

# ── Multi-provider AI API Keys ──
GEMINI_API_KEYS = [
    k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()
]
MISTRAL_API_KEYS = [
    k.strip() for k in os.environ.get("MISTRAL_API_KEYS", "").split(",") if k.strip()
]
GROQ_API_KEYS = [
    k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()
]
OPENROUTER_API_KEYS = [
    k.strip() for k in os.environ.get("OPENROUTER_API_KEYS", "").split(",") if k.strip()
]

# ── Default Database Paths ──
TURSO_DB_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
CLOUDFLARE_D1_URL = os.environ.get("CLOUDFLARE_D1_URL", "")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
