"""Domain models for the support triage flow."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SupportTicket(BaseModel):
    """Subset of fields we care about from a support ticket-created webhook."""

    id: str
    title: str
    body: str
    customer_name: str
    customer_id: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    created_at: datetime
    tags: list[str] = Field(default_factory=list)


class IssueRef(BaseModel):
    id: str
    identifier: str  # e.g. "ENG-1421"
    title: str
    state: str
    assignee: str | None
    url: str


class TriageResult(BaseModel):
    """What the LLM returns after one triage pass."""

    summary: str
    related_issues: list[IssueRef]
    suggested_engineer: str | None
    draft_reply: str
    follow_ups: list[str]
