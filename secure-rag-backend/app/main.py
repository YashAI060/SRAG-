"""
Enterprise RAG API — main application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.models.database import engine, Base

# ── Lifespan: create DB tables on startup ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all SQLAlchemy tables (users table, etc.)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure data directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.TRACE_LOG_PATH) or ".", exist_ok=True)

    yield  # Application runs here

    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-oriented RAG system with grounded generation, "
        "hybrid retrieval, citation tracking, and retrieval-based abstention."
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

from app.api import routes_auth, routes_doc, routes_chat, routes_eval, routes_metrics

app.include_router(routes_auth.router,    prefix=settings.API_V1_STR)
app.include_router(routes_doc.router,     prefix=settings.API_V1_STR)
app.include_router(routes_chat.router,    prefix=settings.API_V1_STR)
app.include_router(routes_eval.router,    prefix=settings.API_V1_STR)
app.include_router(routes_metrics.router, prefix=settings.API_V1_STR)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
