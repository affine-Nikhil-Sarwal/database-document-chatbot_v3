"""HTTP routes for workflow intake and health."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator.graph import run_workflow_from_node

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionContextModel(BaseModel):
    user_id: str = "anonymous"
    request_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    allowed_document_ids: list[str] | None = None
    allowed_tables: list[str] | None = None
    permission_denied: bool = False


class ChatRequest(BaseModel):
    user_question: str
    session_context: SessionContextModel | None = None
    documents_pdf_docx: str | None = None
    structured_tabular_data: dict[str, Any] | None = None


@router.post("/chat", tags=["intake"], summary="User Question Intake")
async def chat_intake(body: ChatRequest, request: Request) -> dict[str, Any]:
    """Start the workflow at user-question-intake."""
    request_id = getattr(request.state, "request_id", None)
    session = body.session_context.model_dump() if body.session_context else {}
    if request_id and not session.get("request_id"):
        session["request_id"] = request_id
    payload: dict[str, Any] = {
        "user_question": body.user_question,
        "session_context": session,
    }
    if body.documents_pdf_docx is not None:
        payload["documents_pdf_docx"] = body.documents_pdf_docx
    if body.structured_tabular_data is not None:
        payload["structured_tabular_data"] = body.structured_tabular_data
    return await asyncio.to_thread(run_workflow_from_node, "user-question-intake", payload)


@router.post("/upload", tags=["intake"], summary="User Question Intake (legacy path)")
async def upload_intake(body: ChatRequest, request: Request) -> dict[str, Any]:
    """Alias for /chat — starts workflow at user-question-intake."""
    return await chat_intake(body, request)


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
