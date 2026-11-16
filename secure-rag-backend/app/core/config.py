from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    PROJECT_NAME: str = "Enterprise RAG API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | production

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── AI Providers ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str

    # Model selection (swap without code changes)
    EMBEDDING_MODEL: str = "models/gemini-embedding-2"
    EMBEDDING_DIMENSIONS: int = 3072
    GENERATION_MODEL: str = "models/gemini-3.6-flash"
    
    # Retry & Resiliency
    LLM_TIMEOUT_SECONDS: int = 10
    LLM_MAX_RETRIES: int = 2
    LLM_RETRY_BASE_DELAY: float = 0.5

    # ── Vector Store ────────────────────────────────────────────────────────────────
    QDRANT_URL: str = "./data/qdrant_db"
    QDRANT_COLLECTION: str = "enterprise_rag_v2"

    # ── Retrieval ─────────────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 10          # Candidates before reranking
    RERANK_TOP_K: int = 3              # Final chunks sent to LLM
    RRF_K: int = 60                    # RRF fusion constant (standard = 60)

    # ── Confidence Gate ───────────────────────────────────────────────────────
    # These are DEFAULT weights — tune via evaluation/evaluate.py
    CONFIDENCE_THRESHOLD: float = 0.45   # Empirically calibrate; do NOT use 0.50 blindly
    CONFIDENCE_WEIGHT_RERANKER: float = 0.45
    CONFIDENCE_WEIGHT_RRF: float = 0.25
    CONFIDENCE_WEIGHT_DENSITY: float = 0.20
    CONFIDENCE_WEIGHT_ALIGNMENT: float = 0.10

    # ── Document Processing ───────────────────────────────────────────────────
    CHUNK_SIZE: int = 500              # Words per chunk
    CHUNK_OVERLAP: int = 50
    OCR_MIN_TEXT_CHARS: int = 50       # If page text < this, trigger OCR
    OCR_ENABLED: bool = True

    # ── Storage ───────────────────────────────────────────────────────────────
    SQLITE_DB_PATH: str = "./data/document_registry.db"
    UPLOAD_DIR: str = "./data/uploads"

    # SQLAlchemy async URL for the users database (separate from document registry)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/users.db"

    # ── Observability ─────────────────────────────────────────────────────────
    LOG_QUERY_TRACES: bool = True
    TRACE_LOG_PATH: str = "./data/traces.jsonl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
