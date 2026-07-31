"""Response delivery — format approved answer or refusal for the analyst."""

from __future__ import annotations

from typing import Any

REFUSAL_HEADER = "## Unable to provide a supported answer\n\n"
APPROVED_HEADER = "## Answer\n\n"


def execute(payload: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    gate_payload = payload.get("approved_answer_or_refusal_payload")
    if not isinstance(gate_payload, dict):
        safe = (
            "I cannot provide a supported answer because the response payload was invalid. "
            "Please try again."
        )
        return {"natural_language_answers": safe, "delivery_error": True}

    status = gate_payload.get("status")
    message = str(gate_payload.get("message", "")).strip()
    conflicts = gate_payload.get("conflicts") or []
    citations = gate_payload.get("citations") or []

    if status == "refused":
        text = REFUSAL_HEADER + message
        if gate_payload.get("refusal_reason"):
            text += f"\n\n*(Reason: {gate_payload['refusal_reason']})*"
        return {"natural_language_answers": text}

    body = APPROVED_HEADER + message
    if conflicts:
        body += "\n\n### Conflicts flagged\n"
        for conflict in conflicts:
            body += f"- **CONFLICT**: {conflict.get('summary', '')}\n"
            body += f"  - Document: {str(conflict.get('doc_claim', ''))[:200]}\n"
            body += f"  - SQL: {str(conflict.get('sql_claim', ''))[:200]}\n"
    if citations:
        body += "\n\n### Citations\n" + ", ".join(str(c) for c in citations)
    return {"natural_language_answers": body}


run = execute
