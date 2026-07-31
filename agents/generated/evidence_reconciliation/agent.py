"""Evidence normalization across document and SQL reuse outputs."""

from __future__ import annotations

import re
from typing import Any

INSUFFICIENT_PATTERNS = (
    "do not have enough information",
    "insufficient",
    "no relevant",
    "cannot answer",
)


def _document_status(document_result: dict[str, Any] | None) -> str:
    if not document_result:
        return "empty"
    answer = str(document_result.get("llm_answer", "")).strip()
    if not answer:
        return "empty"
    lower = answer.lower()
    if any(p in lower for p in INSUFFICIENT_PATTERNS):
        return "insufficient"
    return "ok"


def _sql_status(sql_result: dict[str, Any] | None) -> str:
    if not sql_result:
        return "empty"
    query = str(sql_result.get("query", "")).strip()
    query_answer = str(sql_result.get("query_answer", "")).strip()
    query_results = str(sql_result.get("query_results", "")).strip()
    inference = str(sql_result.get("inference", "")).strip()

    if query_results and not query_results.lower().startswith("an error occurred"):
        return "ok"
    if query and query_answer and not any(p in query_answer.lower() for p in INSUFFICIENT_PATTERNS):
        return "ok"
    if inference and "error" in inference.lower():
        return "failed"
    if not query and not query_answer:
        return "empty"
    if any(p in query_answer.lower() for p in INSUFFICIENT_PATTERNS):
        return "insufficient"
    return "failed"


def _filter_by_scope(text: str, session_context: dict[str, Any], source_type: str) -> bool:
    if session_context.get("permission_denied"):
        return False
    if source_type == "document":
        allowed = session_context.get("allowed_document_ids")
        if isinstance(allowed, list) and len(allowed) == 0 and "allowed_document_ids" in session_context:
            return False
    if source_type == "sql":
        allowed = session_context.get("allowed_tables")
        if isinstance(allowed, list) and len(allowed) == 0 and "allowed_tables" in session_context:
            return False
    return bool(text.strip())


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    document_result = payload.get("document_result")
    sql_result = payload.get("sql_result")
    routing = payload.get("routing_decision") or {}
    session_context = payload.get("session_context") or {}

    items: list[dict[str, Any]] = []
    nl_parts: list[str] = []

    doc_status = _document_status(document_result if isinstance(document_result, dict) else None)
    sql_status = _sql_status(sql_result if isinstance(sql_result, dict) else None)

    if isinstance(document_result, dict) and routing.get("run_document"):
        answer = str(document_result.get("llm_answer", "")).strip()
        if answer and _filter_by_scope(answer, session_context, "document"):
            items.append(
                {
                    "citation_id": "Doc-1",
                    "source_type": "document",
                    "text": answer,
                    "provenance": {
                        "updated_question": document_result.get("updated_question"),
                        "question": document_result.get("question"),
                    },
                    "confidence": 1.0,
                    "status": doc_status,
                }
            )
            nl_parts.append(f"[Document] {answer}")

    if isinstance(sql_result, dict) and routing.get("run_sql"):
        query = str(sql_result.get("query", "")).strip()
        query_results = str(sql_result.get("query_results", "")).strip()
        query_answer = str(sql_result.get("query_answer", "")).strip()
        evidence_text = query_results if query_results else query_answer
        if evidence_text and _filter_by_scope(evidence_text, session_context, "sql"):
            preview = evidence_text[:500]
            items.append(
                {
                    "citation_id": "SQL-1",
                    "source_type": "sql",
                    "text": query_answer or preview,
                    "provenance": {
                        "sql_query": query,
                        "row_preview": preview,
                        "inference": sql_result.get("inference"),
                    },
                    "confidence": 1.0,
                    "status": sql_status,
                }
            )
            nl_parts.append(f"[SQL] {query_answer or preview}")

    ok_items = [i for i in items if i.get("status") == "ok"]
    if not ok_items:
        coverage = "none"
    elif len(ok_items) < len(items):
        coverage = "partial"
    else:
        coverage = "full"

    required_doc = routing.get("run_document") and doc_status in {"empty", "insufficient", "failed"}
    required_sql = routing.get("run_sql") and sql_status in {"empty", "insufficient", "failed"}
    if routing.get("run_document") and routing.get("run_sql") and not ok_items:
        coverage = "none"
    elif (required_doc and doc_status != "ok" and not routing.get("run_sql")) or (
        required_sql and sql_status != "ok" and not routing.get("run_document")
    ):
        if not ok_items:
            coverage = "none"

    return {
        "natural_language_answers": "\n\n".join(nl_parts),
        "normalized_cross_source_evidence_set": {
            "items": items,
            "coverage": coverage,
            "document_status": doc_status,
            "sql_status": sql_status,
        },
    }


run = execute
