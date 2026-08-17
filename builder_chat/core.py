"""Core helpers for formatting Agentic LaunchPad builder chat edit responses."""

from __future__ import annotations

from typing import Any


def format_builder_chat_edit_response(
    *,
    status: str,
    message: str,
    edit_id: str | None = None,
    applied_commands: list[dict[str, Any]] | None = None,
    workflow_snapshot: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Format a builder chat edit outcome for API consumers and contributors.

    Returns
    -------
    dict[str, Any]
        Normalized response payload with the following schema:

        ``status`` : str
            Outcome of the edit operation: ``"success"``, ``"partial"``, or
            ``"error"``.
        ``message`` : str
            Human-readable summary of applied edits or the failure reason.
        ``edit_id`` : str, optional
            Stable identifier for the applied edit batch when the operation
            succeeds or partially succeeds.
        ``applied_commands`` : list[dict[str, Any]], optional
            Builder command deltas that were applied to the workflow graph.
        ``workflow_snapshot`` : dict[str, Any], optional
            Post-edit workflow state for clients that refresh the canvas.
        ``warnings`` : list[str], optional
            Non-fatal issues encountered while applying edits.
        ``error`` : str, optional
            Error detail when ``status`` is ``"error"``; omitted on success.
    """
    response: dict[str, Any] = {
        "status": status,
        "message": message,
    }
    if edit_id is not None:
        response["edit_id"] = edit_id
    if applied_commands is not None:
        response["applied_commands"] = applied_commands
    if workflow_snapshot is not None:
        response["workflow_snapshot"] = workflow_snapshot
    if warnings:
        response["warnings"] = warnings
    if error is not None:
        response["error"] = error
    return response
