"""Evidence sufficiency gate — approve or refuse grounded answers."""

from __future__ import annotations

import re
from typing import Any

REFUSAL_TEMPLATE = (
    "I cannot provide a supported answer because the available approved evidence "
    "is insufficient to answer your question safely. Please refine your question "
    "or ensure the relevant documents and data are accessible within your permissions."
)


def _cited_ids(text: str) -> set[str]:
    return set(re.findall(r"\[(Doc-\d+|SQL-\d+)\]", text))


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    draft = str(payload.get("draft_answer", "")).strip()
    evidence_set = payload.get("normalized_cross_source_evidence_set") or {}
    bundle = payload.get("evidence_plus_conflict_annotations") or {}
    conflicts = bundle.get("conflicts") or []
    routing = payload.get("routing_decision") or {}
    session_context = payload.get("session_context") or {}
    generation_flags = payload.get("generation_flags") or {}

    refusal_reason: str | None = None

    if session_context.get("permission_denied"):
        refusal_reason = "permission_denied"
    elif routing.get("refusal_reason") == "permission_denied":
        refusal_reason = "permission_denied"
    elif generation_flags.get("insufficient_evidence") or generation_flags.get("generation_error"):
        refusal_reason = "insufficient_evidence"
    elif not draft or "insufficient_evidence" in draft.lower():
        refusal_reason = "insufficient_evidence"
    elif evidence_set.get("coverage") == "none":
        refusal_reason = "insufficient_evidence"
    else:
        items = evidence_set.get("items") or []
        ok_items = [i for i in items if i.get("status") == "ok"]
        if routing.get("run_document") and evidence_set.get("document_status") in {
            "empty",
            "insufficient",
            "failed",
        }:
            if not any(i.get("source_type") == "document" and i.get("status") == "ok" for i in items):
                refusal_reason = "documents_missing"
        if routing.get("run_sql") and evidence_set.get("sql_status") in {"empty", "failed"}:
            if not any(i.get("source_type") == "sql" and i.get("status") == "ok" for i in items):
                refusal_reason = refusal_reason or "sql_failed"
        if not ok_items:
            refusal_reason = "partial_evidence"
        else:
            valid_ids = {i.get("citation_id") for i in ok_items}
            cited = _cited_ids(draft)
            if cited and not cited.intersection(valid_ids):
                refusal_reason = "partial_evidence"

    if refusal_reason:
        payload_out = {
            "status": "refused",
            "message": REFUSAL_TEMPLATE,
            "citations": [],
            "conflicts": conflicts,
            "refusal_reason": refusal_reason,
        }
        return {
            "natural_language_answers": REFUSAL_TEMPLATE,
            "approved_answer_or_refusal_payload": payload_out,
        }

    citations = sorted(_cited_ids(draft)) or [i.get("citation_id") for i in ok_items if i.get("citation_id")]
    payload_out = {
        "status": "approved",
        "message": draft,
        "citations": citations,
        "conflicts": conflicts,
        "refusal_reason": None,
    }
    return {
        "natural_language_answers": draft,
        "approved_answer_or_refusal_payload": payload_out,
    }


run = execute
