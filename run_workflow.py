"""Graph execution entrypoint — the cloud agent implements node wiring here."""

from __future__ import annotations

from typing import Any

# Idempotent: honor AZURE_OPENAI_DEPLOYMENT (incl. dotted names) for ag2 create/cost.
try:
    from config.autogen_azure_compat import apply_autogen_azure_compat

    apply_autogen_azure_compat()
except Exception:
    pass


def run_workflow_from_node(node_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the workflow graph starting at ``node_id`` and return the terminal output."""
    raise NotImplementedError(
        "Implement graph execution in run_workflow.py (discover agents, wire adapters, invoke entrypoints)."
    )
