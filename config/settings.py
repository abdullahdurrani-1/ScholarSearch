"""Production central settings module so all components share consistent runtime constants."""

from pathlib import Path

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K = 5
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "gemini-flash-latest"

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
FEEDBACK_FILE = METADATA_DIR / "feedback.csv"
REQUEST_LOG_FILE = METADATA_DIR / "query_logs.jsonl"
RATE_LIMIT_PER_MINUTE = 10
AUTH_DB_FILE = METADATA_DIR / "scholarsearch.db"
AUTH_TOKEN_TTL_HOURS = 168
