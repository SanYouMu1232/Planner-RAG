"""Application configuration loaded from environment variables."""
from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'planner.db'}")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "stub")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "none")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_BASE_URL = os.getenv("SEARCH_BASE_URL", "")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "storage" / "uploads"))
UPLOAD_TEMP_DIR = os.getenv("UPLOAD_TEMP_DIR", str(BASE_DIR / "storage" / "tmp"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "80"))
UPLOAD_CHUNK_SIZE = int(os.getenv("UPLOAD_CHUNK_SIZE", str(2 * 1024 * 1024)))

# Cloud OCR only. The application intentionally does not install or call local OCR engines.
BAIDU_OCR_TASK_URL = os.getenv(
    "BAIDU_OCR_TASK_URL",
    "https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/task",
)
BAIDU_OCR_QUERY_URL = os.getenv(
    "BAIDU_OCR_QUERY_URL",
    "https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/task/query",
)
BAIDU_OCR_TOKEN_URL = os.getenv("BAIDU_OCR_TOKEN_URL", "https://aip.baidubce.com/oauth/2.0/token")
BAIDU_OCR_POLL_SECONDS = float(os.getenv("BAIDU_OCR_POLL_SECONDS", "5"))
BAIDU_OCR_TIMEOUT_SECONDS = int(os.getenv("BAIDU_OCR_TIMEOUT_SECONDS", "180"))

REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "40"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
PROVIDER_CONFIG_SECRET = os.getenv("PROVIDER_CONFIG_SECRET", "planner-dev-secret-change-me")

# Embedding provider configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "stub")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID", "stub-embedding-v1")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
EMBEDDING_VERSION = os.getenv("EMBEDDING_VERSION", "1.0.0")
ALLOW_STUB_EMBEDDING = os.getenv("ALLOW_STUB_EMBEDDING", "1").lower() in ("1", "true", "yes", "on")
INGESTION_MODE = os.getenv("INGESTION_MODE", "background")

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(UPLOAD_TEMP_DIR).mkdir(parents=True, exist_ok=True)
