"""Engineering issue tracker API client.

Talks to a GraphQL issue tracker API when ``ISSUE_TRACKER_BASE_URL`` is unset,
or to the local mock server (``mocks/issue_tracker_server.py``) for the demo.
The request shape mirrors a typical issue-search GraphQL endpoint, so swapping
between mock and a real integration is just an env var change.
"""
from __future__ import annotations

import os

import httpx

from .models import IssueRef

ISSUE_TRACKER_GRAPHQL_URL = "https://issue-tracker.example.com/graphql"

SEARCH_ISSUES_QUERY = """
query SearchIssues($query: String!, $first: Int!) {
  issueSearch(query: $query, first: $first) {
    nodes {
      id
      identifier
      title
      url
      state { name }
      assignee { name }
    }
  }
}
"""


def _endpoint() -> str:
    base = os.environ.get("ISSUE_TRACKER_BASE_URL")
    return f"{base.rstrip('/')}/graphql" if base else ISSUE_TRACKER_GRAPHQL_URL


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("ISSUE_TRACKER_API_KEY")
    if api_key:
        headers["Authorization"] = api_key
    return headers


def search_issues(query: str, limit: int = 5) -> list[IssueRef]:
    """Search engineering issues matching a free-text query."""
    response = httpx.post(
        _endpoint(),
        json={
            "query": SEARCH_ISSUES_QUERY,
            "variables": {"query": query, "first": limit},
        },
        headers=_headers(),
        timeout=10.0,
    )
    response.raise_for_status()
    nodes = response.json()["data"]["issueSearch"]["nodes"]
    return [
        IssueRef(
            id=n["id"],
            identifier=n["identifier"],
            title=n["title"],
            state=n["state"]["name"],
            assignee=(n.get("assignee") or {}).get("name"),
            url=n["url"],
        )
        for n in nodes
    ]
