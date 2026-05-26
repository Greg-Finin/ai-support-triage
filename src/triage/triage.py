"""Claude-driven triage of an incoming support ticket.

The model is given the ticket and a single tool (``search_issues``) to look up
related engineering issues. Once it has enough context, it produces a
structured ``TriageResult`` via a second tool (``submit_triage``) which we use
as a forced-output mechanism — the loop ends as soon as the model calls it.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic

from . import issue_tracker_client
from .models import IssueRef, SupportTicket, TriageResult

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 6

SYSTEM_PROMPT = """You are a support triage assistant for a B2B SaaS company.

For each incoming ticket you:
1. Search the issue tracker for related engineering issues — try multiple queries if the
   first returns nothing useful. Pull keywords from the ticket body, not just
   the title.
2. Identify the most likely owning engineer based on assignees of related
   issues.
3. Draft a short, professional reply to the customer that acknowledges the
   issue and — if there is a known related ticket — references it without
   leaking implementation details.
4. Suggest 1–3 follow-ups for the human support agent (e.g. "ping @alice, she
   owns ENG-1421", "check if customer is on the affected version").

When you have enough context, call ``submit_triage`` with your conclusion.
Be concise. Do not invent issue tracker tickets — only reference ones returned by
the search tool.
"""

TOOLS = [
    {
        "name": "search_issues",
        "description": "Search the engineering issue tracker for issues matching a free-text query. Returns up to 5 results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text search query."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "submit_triage",
        "description": "Submit the final triage result. Call this exactly once when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "1-2 sentence summary of the ticket."},
                "related_issue_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Issue identifiers (e.g. ENG-1421) returned by search_issues.",
                },
                "suggested_engineer": {
                    "type": "string",
                    "description": "Name of the engineer most likely to own this. Empty string if unclear.",
                },
                "draft_reply": {"type": "string", "description": "Draft response to the customer."},
                "follow_ups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Action items for the human support agent.",
                },
            },
            "required": ["summary", "related_issue_ids", "draft_reply", "follow_ups"],
        },
    },
]


def _ticket_to_user_message(ticket: SupportTicket) -> str:
    return (
        f"Customer: {ticket.customer_name} (id={ticket.customer_id})\n"
        f"Priority: {ticket.priority}\n"
        f"Tags: {', '.join(ticket.tags) or 'none'}\n"
        f"Title: {ticket.title}\n\n"
        f"Body:\n{ticket.body}"
    )


def triage_ticket(ticket: SupportTicket) -> TriageResult:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [{"role": "user", "content": _ticket_to_user_message(ticket)}]
    seen_issues: dict[str, IssueRef] = {}

    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            raise RuntimeError(f"Model stopped without submitting triage: {response.stop_reason}")

        tool_results = []
        finalized: TriageResult | None = None

        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "search_issues":
                issues = issue_tracker_client.search_issues(block.input["query"])
                for issue in issues:
                    seen_issues[issue.identifier] = issue
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps([i.model_dump() for i in issues]),
                    }
                )
            elif block.name == "submit_triage":
                args = block.input
                related = [seen_issues[i] for i in args.get("related_issue_ids", []) if i in seen_issues]
                finalized = TriageResult(
                    summary=args["summary"],
                    related_issues=related,
                    suggested_engineer=args.get("suggested_engineer") or None,
                    draft_reply=args["draft_reply"],
                    follow_ups=args.get("follow_ups", []),
                )

        if finalized is not None:
            return finalized

        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"Triage did not complete within {MAX_TURNS} turns")
