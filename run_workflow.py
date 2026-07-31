"""Backward-compatible re-export of orchestrator.graph."""

from orchestrator.graph import run_workflow_from_node, set_dry_run

__all__ = ["run_workflow_from_node", "set_dry_run"]
