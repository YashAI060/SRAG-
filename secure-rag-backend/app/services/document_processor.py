"""
Document Processor — PDF text extraction with OCR fallback.

Pipeline:
    PDF
      ↓
    Is text extractable? (len > OCR_MIN_TEXT_CHARS)
      ├── YES → PyMuPDF fast extraction
      └── NO  → OCR (pytesseract + pdf2image)
                 ↓
             Extracted text
      ↓
    Chunking (configurable size + overlap)
      ↓
    Chunks with page metadata

Also computes SHA-256 for idempotent ingestion.
"""
from __future__ import annotations

import hashlib
import os
from typing import Dict, List, Optional

import fitz  # PyMuPDF

from app.core.config import settings


class DocumentProcessor:
    # ── Hashing ───────────────────────────────────────────────────────────────

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    # ── Text extraction ───────────────────────────────────────────────────────

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[Dict]:
        """
        Extracts text page-by-page using PyMuPDF.
        Falls back to OCR for pages with insufficient text.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        doc = fitz.open(file_path)
        pages_content = []

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""

            if len(text.strip()) < settings.OCR_MIN_TEXT_CHARS and settings.OCR_ENABLED:
                text = DocumentProcessor._ocr_page(file_path, page_num - 1)

            pages_content.append({
                "page_number": page_num,
                "text": text.strip(),
                "char_count": len(text),
                "is_ocr": len((page.get_text("text") or "").strip()) < settings.OCR_MIN_TEXT_CHARS,
            })

        doc.close()
        return pages_content

    @staticmethod
    def _ocr_page(pdf_path: str, page_index: int) -> str:
        """
        OCR a single page using pytesseract.
        Requires: tesseract binary installed on host + pdf2image + Pillow.
        Falls back gracefully if dependencies are missing.
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path

            images = convert_from_path(
                pdf_path, first_page=page_index + 1, last_page=page_index + 1, dpi=300
            )
            if not images:
                return ""
            return pytesseract.image_to_string(images[0], lang="eng")
        except ImportError:
            # Tesseract not installed — log and skip gracefully
            print(
                f"[OCR] pytesseract/pdf2image not available. "
                f"Page {page_index + 1} will have empty text. "
                f"Install tesseract and set OCR_ENABLED=true to enable OCR."
            )
            return ""
        except Exception as e:
            print(f"[OCR] Failed on page {page_index + 1}: {e}")
            return ""

    # ── Chunking ───────────────────────────────────────────────────────────────

    @staticmethod
    def chunk_document(
        pages_content: List[Dict],
        filename: str,
        document_id: str,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> List[Dict]:
        """
        Word-based chunking with configurable overlap.
        Returns chunks with page traceability for citations.

        Includes document-level contextual enrichment to solve multi-hop ranking.
        """
        base_name = os.path.splitext(filename)[0]
        title = base_name.replace("_", " ").title()
        
        chunks = []
        step = max(1, chunk_size - chunk_overlap)

        for page in pages_content:
            text = page["text"]
            page_num = page["page_number"]

            if not text:
                continue

            words = text.split()
            for i in range(0, len(words), step):
                chunk_words = words[i: i + chunk_size]
                if not chunk_words:
                    continue
                    
                original_text = " ".join(chunk_words)
                
                # Contextual enrichment for the embedding model
                context_header = f"Document: {title}\nDocument ID: {document_id}\nPage: {page_num}\n\n"
                contextualized_text = context_header + original_text
                
                chunks.append({
                    "text":        original_text,
                    "contextualized_text": contextualized_text,
                    "page_number": page_num,
                    "chunk_index": len(chunks),
                    "word_count":  len(chunk_words),
                })

        return chunks
