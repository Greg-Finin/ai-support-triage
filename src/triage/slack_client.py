"""Slack incoming-webhook poster.

If ``SLACK_WEBHOOK_URL`` is unset (the default for the local demo), the
formatted message is printed to stdout instead of posted. This keeps the
project runnable without any Slack setup.
"""
from __future__ import annotations

import json
import os

import httpx

from .models import SupportTicket, TriageResult


def _format_blocks(ticket: SupportTicket, result: TriageResult) -> list[dict]:
    related_lines = (
        "\n".join(
            f"• <{i.url}|{i.identifier}> — {i.title} _({i.state})_"
            for i in result.related_issues
        )
        or "_No related issues found_"
    )
    follow_up_lines = "\n".join(f"• {f}" for f in result.follow_ups) or "_None_"
    engineer = result.suggested_engineer or "_unassigned_"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"New ticket — {ticket.customer_name}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{ticket.title}*\n{result.summary}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Priority:*\n{ticket.priority}"},
                {"type": "mrkdwn", "text": f"*Suggested engineer:*\n{engineer}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Related issues:*\n{related_lines}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Draft reply:*\n```{result.draft_reply}```"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Follow-ups:*\n{follow_up_lines}"}},
    ]


def post_triage(ticket: SupportTicket, result: TriageResult) -> None:
    blocks = _format_blocks(ticket, result)
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("[slack:dry-run] " + json.dumps({"blocks": blocks}, indent=2))
        return
    response = httpx.post(webhook, json={"blocks": blocks}, timeout=10.0)
    response.raise_for_status()
