"""AWS Lambda entry point.

Support ticket webhook → API Gateway → this handler. Validates the incoming
webhook payload, runs triage, and posts the result to Slack.
"""
from __future__ import annotations

import json
import logging

from .models import SupportTicket
from .slack_client import post_triage
from .triage import triage_ticket

log = logging.getLogger()
log.setLevel(logging.INFO)


def lambda_handler(event: dict, _context) -> dict:
    body = event.get("body") or "{}"
    if isinstance(body, str):
        body = json.loads(body)

    ticket = SupportTicket.model_validate(body.get("ticket", body))
    log.info("triaging ticket id=%s customer=%s", ticket.id, ticket.customer_name)

    result = triage_ticket(ticket)
    post_triage(ticket, result)

    return {
        "statusCode": 200,
        "body": json.dumps({"ticket_id": ticket.id, "summary": result.summary}),
    }
