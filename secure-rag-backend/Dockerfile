FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ────────────────────────────────────────────────────────
# tesseract-ocr: required for OCR fallback on scanned PDFs
# poppler-utils: required by pdf2image for PDF→image conversion
# libmupdf-dev: for PyMuPDF (fitz) native bindings
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ───────────────────────────────────────────────────────────
COPY . .

# ── Data directories ───────────────────────────────────────────────────────────
RUN mkdir -p data/uploads data/traces data/qdrant_db

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
