"""HTTP routes for workflow intake and health."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator.graph import run_workflow_from_node
from workflow.exceptions import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionContextModel(BaseModel):
    user_id: str = "anonymous"
    request_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    allowed_document_ids: list[str] | None = None
    allowed_tables: list[str] | None = None
    permission_denied: bool = False


def _parse_optional_json(value: str | None, field_name: str) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{field_name} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValidationError(f"{field_name} must be a JSON object")
    return parsed


async def _save_uploaded_pdf(upload: UploadFile) -> Path:
    filename = upload.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise ValidationError("question_pdf must be a PDF file")

    suffix = Path(filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await upload.read()
        if not content:
            raise ValidationError("question_pdf upload is empty")
        tmp.write(content)
        return Path(tmp.name)


async def _run_intake_from_pdf(
    question_pdf: UploadFile,
    request: Request,
    *,
    session_context_json: str | None = None,
    documents_pdf_docx: str | None = None,
    structured_tabular_data_json: str | None = None,
) -> dict[str, Any]:
    request_id = getattr(request.state, "request_id", None)
    session = _parse_optional_json(session_context_json, "session_context") or {}
    if request_id and not session.get("request_id"):
        session["request_id"] = request_id

    pdf_path = await _save_uploaded_pdf(question_pdf)
    payload: dict[str, Any] = {
        "question_pdf": str(pdf_path),
        "session_context": session,
    }
    if documents_pdf_docx is not None:
        payload["documents_pdf_docx"] = documents_pdf_docx
    structured_tabular_data = _parse_optional_json(
        structured_tabular_data_json,
        "structured_tabular_data",
    )
    if structured_tabular_data is not None:
        payload["structured_tabular_data"] = structured_tabular_data
    return await asyncio.to_thread(run_workflow_from_node, "user-question-intake", payload)


@router.post("/chat", tags=["intake"], summary="Chat Intake & Safety Gate")
async def chat_intake(
    request: Request,
    question_pdf: UploadFile = File(..., description="PDF containing the analyst question"),
    session_context: str | None = Form(default=None, description="JSON session context"),
    documents_pdf_docx: str | None = Form(default=None),
    structured_tabular_data: str | None = Form(default=None, description="JSON SQL scope metadata"),
) -> dict[str, Any]:
    """Accept an uploaded question PDF, extract text, and start the workflow."""
    return await _run_intake_from_pdf(
        question_pdf,
        request,
        session_context_json=session_context,
        documents_pdf_docx=documents_pdf_docx,
        structured_tabular_data_json=structured_tabular_data,
    )


@router.post("/upload", tags=["intake"], summary="Chat Intake & Safety Gate (legacy path)")
async def upload_intake(
    request: Request,
    question_pdf: UploadFile = File(..., description="PDF containing the analyst question"),
    session_context: str | None = Form(default=None, description="JSON session context"),
    documents_pdf_docx: str | None = Form(default=None),
    structured_tabular_data: str | None = Form(default=None, description="JSON SQL scope metadata"),
) -> dict[str, Any]:
    """Alias for /chat — accepts a question PDF and starts workflow at intake."""
    return await chat_intake(
        request,
        question_pdf=question_pdf,
        session_context=session_context,
        documents_pdf_docx=documents_pdf_docx,
        structured_tabular_data=structured_tabular_data,
    )


@router.get("/health", tags=["health"])
async def health() -> JSONResponse:
    from integrations import azure_openai, azure_search, sql_database

    results = await asyncio.gather(
        azure_openai.health_check(),
        azure_search.health_check(),
        sql_database.health_check(),
    )
    integrations = list(results)
    ok = all(r.get("status") == "ok" for r in integrations)
    body = {"status": "ok" if ok else "degraded", "integrations": integrations}
    status_code = 200 if ok else 503
    if not ok:
        reasons = [r.get("reason", "unknown") for r in integrations if r.get("status") != "ok"]
        body["reason"] = "; ".join(reasons)
    return JSONResponse(status_code=status_code, content=body)
