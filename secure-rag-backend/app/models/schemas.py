from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: str
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Document Management ───────────────────────────────────────────────────────

class DocumentRecord(BaseModel):
    document_id: str
    tenant_id: str
    filename: str
    file_size: Optional[int] = None
    page_count: int = 0
    chunk_count: int = 0
    version: int = 1
    is_active: bool = True
    status: str  # pending | processing | ready | failed
    error_message: Optional[str] = None
    processing_ms: Optional[float] = None
    uploaded_by: str
    uploaded_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentRecord]
    total: int


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_count: int
    version: int
    status: str
    message: str
    duplicate: bool = False  # True if SHA-256 matched an existing upload


class DocumentStatusResponse(BaseModel):
    document_id: str
    status: str
    chunk_count: int
    page_count: int
    processing_ms: Optional[float] = None
    error_message: Optional[str] = None


# ── Chat & RAG ────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    chunk_id: str
    document_id: str
    source_file: str
    page_number: int
    chunk_preview: str
    retrieval_score: float
    rrf_score: float


class ConfidenceResult(BaseModel):
    score: float
    decision: str   # "answer" | "abstain"
    signals: Dict[str, Any]


class RerankerTrace(BaseModel):
    provider: str
    status: str
    attempts: int
    fallback: Optional[str] = None
    fallback_reason: Optional[str] = None
    latency_ms: float

class GenerationTrace(BaseModel):
    provider: str
    status: str
    attempts: int
    latency_ms: float

class RAGTrace(BaseModel):
    query_id: str
    decomposition_status: str
    decomposition_latency_ms: float
    subquery_count: int
    subqueries_requested: int = 0
    subqueries_accepted: int = 0
    subqueries_truncated: bool = False
    embedding_ms: float
    bm25_ms: float
    dense_ms: float
    rrf_ms: float
    confidence_ms: float
    llm_ms: float
    total_ms: float
    retrieved_chunks: int
    top_dense_score: float
    top_rrf_score: float
    reranker: Optional[RerankerTrace] = None
    generation: Optional[GenerationTrace] = None


class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = None  # [{"role":"user","content":"..."}]
    document_ids: Optional[list[str]] = Field(
        default=None,
        description="Filter retrieval to specific document IDs (e.g. current focused doc)",
    )
    
    retrieval_mode: str = Field(
        default="full",
        description="Evaluation mode: dense, bm25, hybrid, hybrid_rerank, full",
    )
    top_k: Optional[int] = None
    decompose: bool = True


class ChatResponse(BaseModel):
    query: str
    rewritten_query: Optional[str] = None
    answer: str
    abstained: bool
    confidence: ConfidenceResult
    citations: List[Citation]
    hallucinated_citation_ids: List[str]   # chunk_ids cited by LLM but not retrieved
    citation_precision: float
    trace: RAGTrace


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricsSummary(BaseModel):
    total_queries: int
    avg_total_ms: float
    avg_retrieval_ms: float
    avg_llm_ms: float
    abstention_rate: float
    avg_confidence: float
    p50_ms: float
    p95_ms: float