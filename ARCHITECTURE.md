# Architecture

## Intended deployment

```
                  ┌───────────────┐
                  │ Support tool  │  (ticketing SaaS)
                  └───────┬───────┘
                          │ ticket.created webhook
                          ▼
                  ┌───────────────┐
                  │  API Gateway  │  POST /support/webhook
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐         ┌─────────────────────┐
                  │    Lambda     │────────▶│  Anthropic (Claude) │
                  │ (handler.py)  │◀────────│  Sonnet 4.6 + tools │
                  └───┬───────┬───┘         └─────────────────────┘
                      │       │
                      │       └────────▶ Issue tracker GraphQL API
                      │                  (tool: search_issues)
                      ▼
                  ┌───────────────┐
                  │     Slack     │  incoming webhook → #cs-triage
                  └───────────────┘
```

## Demo deployment (this repo, runnable locally)

| Component | Real integration | Demo |
| --- | --- | --- |
| Trigger | Support platform `ticket.created` webhook | `scripts/run_local.py` reads a fixture JSON |
| Transport | API Gateway → Lambda | Direct call into `lambda_handler` |
| LLM | Anthropic API | Anthropic API (same) |
| Issue search | Issue tracker GraphQL API | Local FastAPI mock at `localhost:8765/graphql` |
| Notification | Slack incoming webhook | stdout (or real Slack if `SLACK_WEBHOOK_URL` is set) |

The issue tracker client (`src/triage/issue_tracker_client.py`) is the same
code in both paths — only the `ISSUE_TRACKER_BASE_URL` env var differs. The
mock returns the same GraphQL shape as a real API, so swapping is purely a
config change.

## Why these choices

**API Gateway → Lambda** rather than a long-running service: ticket creation is
bursty and the work per ticket is short (a few seconds). Lambda's
pay-per-invocation model fits the load shape, and there's no idle infra to
maintain.

**Tool use rather than a chained prompt** for the issue lookup: the model
decides how many searches to do and with what queries. In practice it
re-queries with different terms when the first try misses, which a fixed
pipeline can't do.

**`submit_triage` as a forced-output tool** rather than parsing JSON from a
free-form completion: removes a whole class of "the model added a prose
preamble and broke the parser" failures, and the schema is enforced by the
SDK.

**Prompt caching on the system prompt**: at higher volume, the system prompt
dominates input cost. Caching reduces both
latency and spend without changing behavior.
