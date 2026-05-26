"""Local issue tracker mock — just enough GraphQL to answer the issueSearch query.

Run with:  uvicorn mocks.issue_tracker_server:app --port 8765
"""
from __future__ import annotations

from fastapi import FastAPI, Request

app = FastAPI()

# Fictional engineering issues. The triage agent's job is to find matches
# against these from realistic-looking customer ticket text.
ISSUES = [
    {
        "id": "iss_001",
        "identifier": "ENG-1421",
        "title": "SSO SAML callback fails when RelayState contains a hash fragment",
        "url": "https://issue-tracker.example.com/demo/issue/ENG-1421",
        "state": {"name": "In Progress"},
        "assignee": {"name": "Priya Raman"},
        "keywords": ["sso", "saml", "login", "okta", "relaystate", "callback", "redirect"],
    },
    {
        "id": "iss_002",
        "identifier": "ENG-1518",
        "title": "Webhook deliveries delayed >5min during ingest backfill",
        "url": "https://issue-tracker.example.com/demo/issue/ENG-1518",
        "state": {"name": "In Review"},
        "assignee": {"name": "Marcus Lee"},
        "keywords": ["webhook", "delay", "delivery", "ingest", "lag", "backfill", "queue"],
    },
    {
        "id": "iss_003",
        "identifier": "ENG-1602",
        "title": "Export CSV truncates rows >100k on Snowflake-backed reports",
        "url": "https://issue-tracker.example.com/demo/issue/ENG-1602",
        "state": {"name": "Triage"},
        "assignee": None,
        "keywords": ["export", "csv", "truncate", "snowflake", "report", "rows", "download"],
    },
    {
        "id": "iss_004",
        "identifier": "ENG-1377",
        "title": "API rate-limit headers missing on /v1/events endpoint",
        "url": "https://issue-tracker.example.com/demo/issue/ENG-1377",
        "state": {"name": "Done"},
        "assignee": {"name": "Dana Okafor"},
        "keywords": ["rate", "limit", "429", "headers", "events", "api", "throttle"],
    },
    {
        "id": "iss_005",
        "identifier": "ENG-1655",
        "title": "Dashboard time-zone offset wrong for users east of UTC",
        "url": "https://issue-tracker.example.com/demo/issue/ENG-1655",
        "state": {"name": "Backlog"},
        "assignee": {"name": "Jordan Park"},
        "keywords": ["timezone", "tz", "utc", "offset", "dashboard", "date"],
    },
]


def _score(issue: dict, query: str) -> int:
    q = query.lower()
    return sum(1 for kw in issue["keywords"] if kw in q) + (
        2 if any(tok in issue["title"].lower() for tok in q.split()) else 0
    )


@app.post("/graphql")
async def graphql(request: Request) -> dict:
    payload = await request.json()
    variables = payload.get("variables") or {}
    query = (variables.get("query") or "").strip()
    limit = variables.get("first") or 5

    ranked = sorted(ISSUES, key=lambda i: _score(i, query), reverse=True)
    hits = [i for i in ranked if _score(i, query) > 0][:limit]

    return {
        "data": {
            "issueSearch": {
                "nodes": [
                    {
                        "id": i["id"],
                        "identifier": i["identifier"],
                        "title": i["title"],
                        "url": i["url"],
                        "state": i["state"],
                        "assignee": i["assignee"],
                    }
                    for i in hits
                ]
            }
        }
    }
