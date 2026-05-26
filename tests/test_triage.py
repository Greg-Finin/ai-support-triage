"""Smoke tests with a stubbed Anthropic client and mocked issue search."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from src.triage import triage as triage_mod
from src.triage.models import IssueRef, SupportTicket


class _Block(SimpleNamespace):
    pass


class _FakeMessages:
    def __init__(self, scripted_responses):
        self._scripted = list(scripted_responses)

    def create(self, **_kwargs):
        return self._scripted.pop(0)


class _FakeAnthropic:
    def __init__(self, scripted_responses):
        self.messages = _FakeMessages(scripted_responses)


def _make_ticket() -> SupportTicket:
    return SupportTicket(
        id="tkt_test",
        title="SSO broken",
        body="Users bouncing back to login after Okta auth.",
        customer_name="ACME",
        customer_id="cust_1",
        priority="high",
        created_at=datetime(2026, 5, 20, 12, 0, 0),
        tags=["sso"],
    )


def test_triage_completes_on_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    search_block = _Block(
        type="tool_use", id="tu_1", name="search_issues", input={"query": "okta sso redirect"}
    )
    submit_block = _Block(
        type="tool_use",
        id="tu_2",
        name="submit_triage",
        input={
            "summary": "Customer hitting SSO redirect loop after Okta login.",
            "related_issue_ids": ["ENG-1421"],
            "suggested_engineer": "Priya Raman",
            "draft_reply": "Thanks — we're investigating and will follow up shortly.",
            "follow_ups": ["Ping Priya in #eng-platform"],
        },
    )

    scripted = [
        SimpleNamespace(content=[search_block], stop_reason="tool_use"),
        SimpleNamespace(content=[submit_block], stop_reason="tool_use"),
    ]

    monkeypatch.setattr(triage_mod, "Anthropic", lambda **_: _FakeAnthropic(scripted))
    monkeypatch.setattr(
        triage_mod.issue_tracker_client,
        "search_issues",
        lambda *_a, **_k: [
            IssueRef(
                id="iss_001",
                identifier="ENG-1421",
                title="SAML callback redirect bug",
                state="In Progress",
                assignee="Priya Raman",
                url="https://issue-tracker.example.com/demo/issue/ENG-1421",
            )
        ],
    )

    result = triage_mod.triage_ticket(_make_ticket())
    assert result.suggested_engineer == "Priya Raman"
    assert len(result.related_issues) == 1
    assert result.related_issues[0].identifier == "ENG-1421"
    assert "Priya" in result.follow_ups[0]
