"""Pytest helpers for PDF-based intake tests."""

from __future__ import annotations

from pathlib import Path

import pymupdf


def write_question_pdf(path: Path, question_text: str) -> Path:
    """Create a minimal PDF containing ``question_text`` for intake tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        page = doc.new_page()
        page.insert_text((72, 72), question_text)
        doc.save(path)
    finally:
        doc.close()
    return path
