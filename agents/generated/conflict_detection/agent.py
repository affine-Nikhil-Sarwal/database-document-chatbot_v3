"""Cross-source conflict detection."""

from __future__ import annotations

import re
from typing import Any


def _extract_numbers(text: str) -> list[float]:
    return [float(m.group(0).replace(",", "")) for m in re.finditer(r"\d+(?:\.\d+)?", text)]


def _numbers_conflict(a: str, b: str, tolerance: float = 0.05) -> bool:
    nums_a = _extract_numbers(a)
    nums_b = _extract_numbers(b)
    if not nums_a or not nums_b:
        return False
    for na in nums_a:
        for nb in nums_b:
            if na == 0 and nb == 0:
                continue
            denom = max(abs(na), abs(nb), 1.0)
            if abs(na - nb) / denom > tolerance:
                return True
    return False


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    evidence_set = payload.get("normalized_cross_source_evidence_set") or {}
    items = evidence_set.get("items") or []
    doc_items = [i for i in items if i.get("source_type") == "document" and i.get("status") == "ok"]
    sql_items = [i for i in items if i.get("source_type") == "sql" and i.get("status") == "ok"]

    conflicts: list[dict[str, Any]] = []
    warning: str | None = None

    try:
        if doc_items and sql_items:
            doc_text = " ".join(str(i.get("text", "")) for i in doc_items)
            sql_text = " ".join(str(i.get("text", "")) for i in sql_items)
            if _numbers_conflict(doc_text, sql_text):
                conflicts.append(
                    {
                        "severity": "high",
                        "summary": "Document and SQL sources report materially different numeric values",
                        "doc_claim": doc_text[:400],
                        "sql_claim": sql_text[:400],
                        "citation_ids": [doc_items[0]["citation_id"], sql_items[0]["citation_id"]],
                        "show_both_and_flag": True,
                    }
                )
            elif doc_text.lower()[:80] != sql_text.lower()[:80] and len(doc_text) > 20 and len(sql_text) > 20:
                doc_nums = set(_extract_numbers(doc_text))
                sql_nums = set(_extract_numbers(sql_text))
                if doc_nums != sql_nums:
                    conflicts.append(
                        {
                            "severity": "medium",
                            "summary": "Document and SQL narratives may disagree on key facts",
                            "doc_claim": doc_text[:400],
                            "sql_claim": sql_text[:400],
                            "citation_ids": [doc_items[0]["citation_id"], sql_items[0]["citation_id"]],
                            "show_both_and_flag": True,
                        }
                    )
    except Exception as exc:
        warning = str(exc)

    return {
        "evidence_plus_conflict_annotations": {
            "evidence_set": evidence_set,
            "conflicts": conflicts,
            "warning": warning,
        }
    }


run = execute
