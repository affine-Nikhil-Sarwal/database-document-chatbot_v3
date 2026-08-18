"""HTTP routes for workflow intake and health."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import time
import zlib
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from orchestrator.graph import run_workflow_from_node

logger = logging.getLogger(__name__)
router = APIRouter()

_CSV_DOWNLOAD_TTL_SECONDS = 15 * 60


def _csv_download_secret() -> bytes:
    configured = os.environ.get("CSV_DOWNLOAD_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")
    for env_name in ("AZURE_OPENAI_API_KEY", "AZURE_SEARCH_API_KEY", "SQL_PASSWORD"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return hashlib.sha256(f"csv-download|{env_name}|{value}".encode("utf-8")).digest()
    return hashlib.sha256(b"csv-download-dev-fallback").digest()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


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


def _register_csv_download(attachment: dict[str, Any]) -> str | None:
    content_b64 = attachment.get("content_base64")
    if not isinstance(content_b64, str) or not content_b64:
        return None
    try:
        base64.b64decode(content_b64.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return None
    filename = str(attachment.get("filename") or "answer_tables.csv")
    body = json.dumps(
        {
            "f": filename,
            "p": content_b64,
            "e": int(time.time()) + _CSV_DOWNLOAD_TTL_SECONDS,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = _b64url_encode(zlib.compress(body, level=9))
    signature = hmac.new(_csv_download_secret(), encoded.encode("ascii"), hashlib.sha256).digest()
    token = f"{encoded}.{_b64url_encode(signature)}"
    attachment["download_token"] = token
    return token


def _read_csv_download(token: str) -> tuple[str, bytes] | None:
    if not token or "." not in token:
        return None
    encoded, signature_b64 = token.rsplit(".", 1)
    if not encoded or not signature_b64:
        return None
    try:
        given_sig = _b64url_decode(signature_b64)
        expected_sig = hmac.new(
            _csv_download_secret(), encoded.encode("ascii"), hashlib.sha256
        ).digest()
    except (ValueError, UnicodeEncodeError):
        return None
    if len(given_sig) != len(expected_sig) or not hmac.compare_digest(given_sig, expected_sig):
        return None
    try:
        body = json.loads(zlib.decompress(_b64url_decode(encoded)))
    except (ValueError, OSError, json.JSONDecodeError, UnicodeDecodeError, zlib.error, TypeError):
        return None
    if not isinstance(body, dict):
        return None
    try:
        expires_at = int(body["e"])
    except (KeyError, TypeError, ValueError):
        return None
    if expires_at < int(time.time()):
        return None
    filename = body.get("f")
    if not isinstance(filename, str) or not filename:
        filename = "answer_tables.csv"
    content_b64 = body.get("p")
    if not isinstance(content_b64, str) or not content_b64:
        return None
    try:
        payload = base64.b64decode(content_b64.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return None
    return filename, payload


def _attach_csv_download_url(result: dict[str, Any]) -> dict[str, Any]:
    attachment = result.get("csv_attachment")
    if not isinstance(attachment, dict):
        return result
    token = _register_csv_download(attachment)
    if token:
        result = dict(result)
        result["csv_download_url"] = f"/download/csv/{token}"
    return result


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
    result = await asyncio.to_thread(run_workflow_from_node, "user-question-intake", payload)
    return _attach_csv_download_url(result)


@router.get("/download/csv/{token}", tags=["export"], summary="Download tabular answer CSV")
async def download_csv(token: str) -> Response:
    """Download CSV exported from a prior chat response."""
    cached = _read_csv_download(token)
    if cached is None:
        raise HTTPException(status_code=404, detail="CSV export not found or expired")
    filename, payload = cached
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type="text/csv; charset=utf-8", headers=headers)


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
