"""
Document routes — full CRUD with SHA-256 dedup, versioning, and status tracking.

POST   /api/v1/docs/upload              Upload + ingest PDF
GET    /api/v1/docs/                    List documents for current tenant
GET    /api/v1/docs/{document_id}       Get single document metadata
GET    /api/v1/docs/{document_id}/status  Ingestion status
DELETE /api/v1/docs/{document_id}       Soft delete
"""
import os
import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_current_user, RoleChecker
from app.core.config import settings
from app.models.schemas import (
    DocumentListResponse,
    DocumentRecord,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.document_processor import DocumentProcessor
from app.services.document_store import document_store
from app.services.llm_generator import LLMGeneratorService
from app.services.vector_store import VectorStoreService

router = APIRouter(prefix="/docs", tags=["Documents"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


# ── Background ingestion task ─────────────────────────────────────────────────

def _ingest_document(
    document_id: str,
    file_path: str,
    filename: str,
    tenant_id: str,
    version: int,
):
    """
    Run in a FastAPI BackgroundTask.
    Structured so the function body (processing + indexing) can be extracted
    into a Celery/RQ worker without rewriting the pipeline.
    See ADR: docs/decisions/003-background-tasks.md
    """
    t_start = time.perf_counter()
    try:
        document_store.update_status(document_id, "processing")

        # 1. Extract text (with OCR fallback)
        pages = DocumentProcessor.extract_text_from_pdf(file_path)

        # 2. Chunk
        chunks = DocumentProcessor.chunk_document(pages, filename=filename, document_id=document_id)
        if not chunks:
            raise ValueError("No extractable text or chunks found in document. File may be empty or unreadable.")

        # 3. Embed + index
        llm_svc = LLMGeneratorService()
        vector_svc = VectorStoreService()

        embeddings = [
            llm_svc.get_embedding(chunk["contextualized_text"], task_type="retrieval_document")
            for chunk in chunks
        ]

        vector_svc.add_documents(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document_id,
            tenant_id=tenant_id,
            filename=filename,
            version=version,
        )

        processing_ms = (time.perf_counter() - t_start) * 1000
        document_store.update_status(
            document_id,
            status="ready",
            chunk_count=len(chunks),
            page_count=len(pages),
            processing_ms=processing_ms,
        )

    except Exception as e:
        document_store.update_status(
            document_id, status="failed", error_message=str(e)
        )
        raise


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """
    Upload a PDF. Ingestion (embedding + indexing) runs in the background.
    Returns immediately with document_id and status=pending.

    SHA-256 deduplication: identical files return the existing document.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    content = await file.read()
    file_hash = DocumentProcessor.compute_sha256(content)
    tenant_id = current_user["tenant_id"]  # server-derived, never from client

    # ── Deduplication check ───────────────────────────────────────────────────
    existing = document_store.find_by_hash(file_hash, tenant_id)
    if existing and existing["status"] == "ready":
        return DocumentUploadResponse(
            document_id=existing["document_id"],
            filename=existing["filename"],
            chunks_count=existing["chunk_count"],
            version=existing["version"],
            status=existing["status"],
            message="Identical document already indexed. Returning existing record.",
            duplicate=True,
        )

    # ── Save file ─────────────────────────────────────────────────────────────
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_hash}_{safe_filename}")
    with open(file_path, "wb") as f:
        f.write(content)

    # ── Register in document store ────────────────────────────────────────────
    document_id, deactivated_ids = document_store.create(
        tenant_id=tenant_id,
        filename=safe_filename,
        file_hash=file_hash,
        file_size=len(content),
        uploaded_by=current_user["sub"],
    )

    # Deactivate chunks for previous versions in the vector store
    if deactivated_ids:
        vector_svc = VectorStoreService()
        for d_id in deactivated_ids:
            vector_svc.deactivate_document_chunks(document_id=d_id, tenant_id=tenant_id)

    # Get version number
    doc = document_store.get(document_id, tenant_id)
    version = doc["version"] if doc else 1

    # ── Kick off background ingestion ─────────────────────────────────────────
    background_tasks.add_task(
        _ingest_document, document_id, file_path, safe_filename, tenant_id, version
    )

    return DocumentUploadResponse(
        document_id=document_id,
        filename=safe_filename,
        chunks_count=0,
        version=version,
        status="pending",
        message="Document received. Ingestion running in background.",
        duplicate=False,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """List all active documents for the current tenant."""
    tenant_id = current_user["tenant_id"]
    docs = document_store.list_for_tenant(tenant_id, active_only=True)
    return DocumentListResponse(
        documents=[DocumentRecord(**d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentRecord)
async def get_document(
    document_id: str,
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """Retrieve metadata for a single document (must belong to current tenant)."""
    tenant_id = current_user["tenant_id"]
    doc = document_store.get(document_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord(**doc)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """Poll ingestion status for a specific document."""
    tenant_id = current_user["tenant_id"]
    doc = document_store.get(document_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentStatusResponse(
        document_id=document_id,
        status=doc["status"],
        chunk_count=doc.get("chunk_count", 0),
        page_count=doc.get("page_count", 0),
        processing_ms=doc.get("processing_ms"),
        error_message=doc.get("error_message"),
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(RoleChecker(["admin", "user"])),
):
    """Soft-delete a document from the registry and hard-delete its Qdrant chunks."""
    tenant_id = current_user["tenant_id"]

    doc = document_store.get(document_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove from Qdrant
    vector_svc = VectorStoreService()
    vector_svc.delete_document_chunks(document_id=document_id, tenant_id=tenant_id)

    # Soft delete in registry
    document_store.delete(document_id, tenant_id)

    return {"message": f"Document '{doc['filename']}' deleted successfully.", "document_id": document_id}
