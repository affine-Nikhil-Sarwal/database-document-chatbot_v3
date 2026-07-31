"""Intake routes for the generated workflow — included by main.py."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from run_workflow import run_workflow_from_node

APP_ROOT = Path(__file__).resolve().parent.parent
router = APIRouter()


class WorkflowPayload(BaseModel):
    """JSON body accepted by intake endpoints."""

    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/upload", tags=["intake"], summary='User Question Intake')
async def user_question_intake(payload: WorkflowPayload) -> dict[str, Any]:
    """Start the workflow at node 'user-question-intake' and return its result."""
    return run_workflow_from_node('user-question-intake', payload.data)


@router.post("/evidence-sufficiency-gate", tags=["intake"], summary='Evidence Sufficiency and Refusal Gate')
async def evidence_sufficiency_gate(payload: WorkflowPayload) -> dict[str, Any]:
    """Start the workflow at node 'evidence-sufficiency-gate' and return its result."""
    return run_workflow_from_node('evidence-sufficiency-gate', payload.data)
