"""Extract analyst question text from an uploaded PDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from workflow.exceptions import ValidationError


def extract_question_from_pdf(pdf_path: str | Path) -> str:
    """Return normalized question text extracted from a PDF file."""
    path = Path(pdf_path)
    if not path.is_file():
        raise ValidationError(f"question_pdf not found: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValidationError("question_pdf must be a PDF file")

    doc = pymupdf.open(path)
    try:
        parts: list[str] = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                parts.append(text)
    finally:
        doc.close()

    question = "\n".join(parts).strip()
    if not question:
        raise ValidationError("question_pdf contains no extractable text")
    return question
