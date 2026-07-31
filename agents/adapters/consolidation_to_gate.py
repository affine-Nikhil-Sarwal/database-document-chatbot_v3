"""Bundles consolidation output for the sufficiency gate."""

from __future__ import annotations

from typing import Any


def bundle_for_gate(
    consolidation_output: dict[str, Any],
    evidence_bundle: dict[str, Any],
    routing_decision: dict[str, Any],
    session_context: dict[str, Any],
) -> dict[str, Any]:
    evidence_set = (evidence_bundle.get("evidence_set") or {}) if evidence_bundle else {}
    return {
        "draft_answer": consolidation_output.get("natural_language_answers", ""),
        "normalized_cross_source_evidence_set": evidence_set,
        "evidence_plus_conflict_annotations": evidence_bundle,
        "routing_decision": routing_decision,
        "session_context": session_context,
        "generation_flags": consolidation_output.get("generation_flags") or {},
    }
