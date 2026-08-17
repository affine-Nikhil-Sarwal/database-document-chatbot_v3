"""User question intake — validates question PDF and session context."""

from __future__ import annotations

from typing import Any

from workflow.exceptions import PermissionDeniedError, ValidationError

from .pdf_extractor import extract_question_from_pdf


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    question_pdf = payload.get("question_pdf")
    user_question = str(payload.get("user_question", "")).strip()

    if question_pdf:
        user_question = extract_question_from_pdf(str(question_pdf))
    elif not user_question:
        raise ValidationError("question_pdf is required (upload a PDF containing the analyst question)")

    if not user_question:
        raise ValidationError("Extracted question text must be non-empty")

    session_context = payload.get("session_context") or {}
    if not isinstance(session_context, dict):
        raise ValidationError("session_context must be an object")

    if session_context.get("permission_denied") is True:
        raise PermissionDeniedError("Access denied for this analyst session")

    documents_pdf_docx = payload.get("documents_pdf_docx")
    structured_tabular_data = payload.get("structured_tabular_data")

    enriched = dict(session_context)
    if question_pdf:
        refs = list(enriched.get("document_references") or [])
        refs.append(str(question_pdf))
        enriched["document_references"] = refs
    if documents_pdf_docx:
        refs = list(enriched.get("document_references") or [])
        refs.append(str(documents_pdf_docx))
        enriched["document_references"] = refs
    if structured_tabular_data and isinstance(structured_tabular_data, dict):
        enriched["sql_scope"] = structured_tabular_data

    return {
        "user_question": user_question,
        "session_context": enriched,
    }


run = execute
