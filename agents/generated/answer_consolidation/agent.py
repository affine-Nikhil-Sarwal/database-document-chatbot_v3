"""Grounded answer synthesis with inline citations."""

from __future__ import annotations

import json
import re
from typing import Any

from config.settings import get_settings
from integrations import azure_openai


def _format_sources(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in items:
        cid = item.get("citation_id", "")
        prov = item.get("provenance") or {}
        if item.get("source_type") == "sql":
            lines.append(f"- [{cid}] SQL: {prov.get('sql_query', '')} | rows: {prov.get('row_preview', '')[:200]}")
        else:
            lines.append(f"- [{cid}] Document excerpt: {str(item.get('text', ''))[:200]}")
    return "\n".join(lines)


def _deterministic_draft(
    user_question: str,
    items: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
) -> str:
    if not items:
        return ""
    parts = [f"Based on approved enterprise evidence for: {user_question}"]
    for item in items:
        cid = item.get("citation_id", "")
        parts.append(f"- [{cid}] {item.get('text', '')}")
    if conflicts:
        parts.append("\nCONFLICT — both sources disagree:")
        for conflict in conflicts:
            parts.append(f"* {conflict.get('summary')}")
            parts.append(f"  Document: {conflict.get('doc_claim', '')[:200]}")
            parts.append(f"  SQL: {conflict.get('sql_claim', '')[:200]}")
    parts.append("\nSources:\n" + _format_sources(items))
    return "\n".join(parts)


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    bundle = payload.get("evidence_plus_conflict_annotations") or {}
    evidence_set = bundle.get("evidence_set") or {}
    conflicts = bundle.get("conflicts") or []
    user_question = str(payload.get("user_question", "")).strip()

    items = [i for i in (evidence_set.get("items") or []) if i.get("status") == "ok"]
    if evidence_set.get("coverage") == "none" or not items:
        return {
            "natural_language_answers": "",
            "generation_flags": {"insufficient_evidence": True},
        }

    if dry_run:
        draft = _deterministic_draft(user_question, items, conflicts)
        return {"natural_language_answers": draft, "generation_flags": {"dry_run": True}}

    evidence_block = json.dumps(
        [{"id": i["citation_id"], "text": i["text"], "source": i["source_type"]} for i in items],
        indent=2,
    )
    conflict_block = json.dumps(conflicts, indent=2)
    system = (
        "You compose a grounded answer using ONLY the supplied evidence items. "
        "Cite each claim with [Doc-n] or [SQL-n] matching evidence ids. "
        "Never use outside knowledge. When conflicts exist, present both sides labeled CONFLICT. "
        "If evidence is insufficient, respond with exactly: insufficient_evidence"
    )
    user = (
        f"Question: {user_question}\n\nEvidence:\n{evidence_block}\n\nConflicts:\n{conflict_block}"
    )
    try:
        draft = azure_openai.chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            settings=get_settings(),
            max_tokens=2000,
        )
        if "insufficient_evidence" in draft.lower() and len(items) > 0:
            draft = _deterministic_draft(user_question, items, conflicts)
        return {"natural_language_answers": draft.strip()}
    except Exception:
        return {
            "natural_language_answers": "",
            "generation_flags": {"generation_error": True},
        }


run = execute
