"""User question intake — validates question and session context."""

from __future__ import annotations

from typing import Any

from workflow.exceptions import PermissionDeniedError, ValidationError


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    user_question = str(payload.get("user_question", "")).strip()
    if not user_question:
        raise ValidationError("user_question must be a non-empty string")

    session_context = payload.get("session_context") or {}
    if not isinstance(session_context, dict):
        raise ValidationError("session_context must be an object")

    if session_context.get("permission_denied") is True:
        raise PermissionDeniedError("Access denied for this analyst session")

    documents_pdf_docx = payload.get("documents_pdf_docx")
    structured_tabular_data = payload.get("structured_tabular_data")

    enriched = dict(session_context)
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
