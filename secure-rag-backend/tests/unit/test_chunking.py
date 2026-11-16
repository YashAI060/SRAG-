"""Unit tests for DocumentProcessor chunking and OCR detection."""
import os
import tempfile
import pytest
from app.services.document_processor import DocumentProcessor


class TestChunking:
    def _pages(self, text: str, page_num: int = 1) -> list[dict]:
        return [{"page_number": page_num, "text": text, "char_count": len(text), "is_ocr": False}]

    def test_basic_chunking(self):
        text = " ".join([f"word{i}" for i in range(200)])
        pages = self._pages(text)
        chunks = DocumentProcessor.chunk_document(pages, chunk_size=50, chunk_overlap=10, filename='test.pdf', document_id='doc_1')
        assert len(chunks) > 1
        assert all("text" in c for c in chunks)
        assert all("page_number" in c for c in chunks)

    def test_chunk_overlap_creates_shared_words(self):
        words = [f"w{i}" for i in range(120)]
        text = " ".join(words)
        pages = self._pages(text)
        chunks = DocumentProcessor.chunk_document(pages, chunk_size=50, chunk_overlap=10, filename='test.pdf', document_id='doc_1')
        # Last words of chunk N should appear in chunk N+1
        if len(chunks) > 1:
            tail = set(chunks[0]["text"].split()[-10:])
            head = set(chunks[1]["text"].split()[:10])
            assert len(tail & head) > 0

    def test_empty_page_skipped(self):
        pages = [{"page_number": 1, "text": "", "char_count": 0, "is_ocr": False}]
        chunks = DocumentProcessor.chunk_document(pages, filename='test.pdf', document_id='doc_1')
        assert chunks == []

    def test_chunk_index_is_sequential(self):
        text = " ".join([f"word{i}" for i in range(300)])
        pages = self._pages(text)
        chunks = DocumentProcessor.chunk_document(pages, chunk_size=50, chunk_overlap=0, filename='test.pdf', document_id='doc_1')
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_word_count_recorded(self):
        text = " ".join(["word"] * 100)
        pages = self._pages(text)
        chunks = DocumentProcessor.chunk_document(pages, chunk_size=50, chunk_overlap=0, filename='test.pdf', document_id='doc_1')
        for c in chunks:
            assert c["word_count"] <= 50

    def test_sha256_deterministic(self):
        content = b"test content for hashing"
        h1 = DocumentProcessor.compute_sha256(content)
        h2 = DocumentProcessor.compute_sha256(content)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_sha256_different_content(self):
        h1 = DocumentProcessor.compute_sha256(b"content a")
        h2 = DocumentProcessor.compute_sha256(b"content b")
        assert h1 != h2

    def test_chunk_size_respected(self):
        text = " ".join([f"word{i}" for i in range(500)])
        pages = self._pages(text)
        chunks = DocumentProcessor.chunk_document(pages, chunk_size=100, chunk_overlap=0, filename='test.pdf', document_id='doc_1')
        for c in chunks:
            assert len(c["text"].split()) <= 100
