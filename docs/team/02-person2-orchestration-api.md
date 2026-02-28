# Role Card: Person 2 — Orchestration API

**You own:** The brain. Three Mistral AI agents relay in sequence and stream every thought to the dashboard.

---

## Your Job in One Sentence

Build a FastAPI server with one endpoint (`POST /analyze`) that runs three Mistral Large agents in sequence, each calling Neo4j tools, and streams every event (agent thoughts, tool calls, results) as Server-Sent Events.

---

## What You're Building

```
orchestration_api/
├── config.py              ← MISTRAL_API_KEY, model name
├── mcp_bridge.py          ← imports Person 1's tools as plain Python functions
├── main.py                ← FastAPI app, /analyze endpoint
└── agents/
    ├── config.py          ← AGENTS dict (system prompts + tool lists) + TOOL_SCHEMAS
    ├── sse.py             ← make_event() helper
    └── orchestrator.py    ← the 3-agent relay loop → yields SSE events
```

---

## Getting Started

```bash
# 1. Install dependencies
pip install fastapi sse-starlette mistralai uvicorn python-dotenv

# 2. Verify MISTRAL_API_KEY is in .env
grep MISTRAL_API_KEY .env

# 3. Start the server
uvicorn orchestration_api.main:app --port 8000 --reload

# 4. Health check
curl http://localhost:8000/health
# Expected: {"status": "ok"}

# 5. Smoke test the full relay
curl -N -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"geo_id": "EL30", "sdg_id": "SDG_7"}'
# Expected: SSE events scroll past in terminal
```

---

## The Mistral Agentic Loop (critical to understand)

Mistral uses OpenAI-compatible function calling. The loop looks like this:

```python
while True:
    response = client.chat.complete(model=MODEL, messages=messages, tools=tools, tool_choice="auto")
    choice = response.choices[0]
    message = choice.message

    if message.content:
        yield make_event("agent_thought", {"text": message.content})  # stream text

    if choice.finish_reason != "tool_calls":
        break  # agent is done thinking

    messages.append(message.model_dump())  # ← MUST use .model_dump(), not the raw object

    for tool_call in message.tool_calls:
        result = call_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
        yield make_event("tool_call", {...})
        yield make_event("tool_result", {...})
        messages.append({
            "role": "tool",          # ← Mistral expects "tool", NOT "user"
            "tool_call_id": tool_call.id,
            "content": json.dumps(result["result"])
        })
```

**Two easy mistakes to avoid:**
1. `messages.append(message)` → **wrong** (Pydantic model, crashes next API call). Use `message.model_dump()`.
2. Tool result role must be `"tool"` not `"user"`.

---

## The SSE Event Contract

**Person 3 depends on every one of these events being sent correctly.** Do not change the `type` field names.

```python
from orchestration_api.agents.sse import make_event

make_event("agent_start",   {"agent": "analyst"})
make_event("tool_call",     {"tool": "get_regional_sdg_profile", "input": {"geo_id": "EL30", "sdg_id": "SDG_7"}})
make_event("tool_result",   {"output": [...], "cypher": "MATCH (ga:GeoArea)..."})
make_event("agent_thought", {"text": "Attica scores 34% on SDG 7..."})
make_event("agent_done",    {"agent": "analyst", "summary": "..."})
make_event("final",         {"recommendation": {...}, "traces": [...]})
make_event("error",         {"message": "..."})
```

Each event is emitted via `EventSourceResponse` from `sse-starlette`. The dashboard reads `data:` lines and parses the JSON.

---

## The Three Agents

You configure three agents in `agents/config.py`. Each has:
- `model`: `"mistral-large-latest"` (Mistral Large 3)
- `system`: a focused system prompt
- `tools`: list of tool names this agent is allowed to call

| Agent | Allowed Tools | Context it receives |
|---|---|---|
| `analyst` | `get_regional_sdg_profile`, `get_indicator_trend` | Raw user message |
| `strategist` | `find_peer_regions`, `get_indicator_trend` | Analyst's summary |
| `localizer` | `map_sdg_to_policy` | Analyst + Strategist summaries |

The summaries are concatenated into a `context` string and injected into each agent's user message.

---

## Dependency on Person 1

You import Person 1's tools directly — **no HTTP, just Python imports:**

```python
# orchestration_api/mcp_bridge.py
from mcp_server.tools.regional_profile import get_regional_sdg_profile
from mcp_server.tools.peer_regions import find_peer_regions
# etc.
```

**If Person 1 isn't done yet**, use stubs in `mcp_bridge.py`:

```python
def get_regional_sdg_profile(geo_id, sdg_id):
    return {
        "result": [{"indicator_code": "sdg_07_40", "value": 34.2, "time": "2022-01-01"}],
        "cypher": "-- STUB --",
        "metadata": {}
    }
```

Switch to real imports once Person 1 is ready.

---

## Mistral Tool Schema Format

Mistral uses OpenAI-compatible format (NOT Anthropic format):

```python
# CORRECT (Mistral)
{
    "type": "function",
    "function": {
        "name": "get_regional_sdg_profile",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": { "geo_id": {"type": "string"}, "sdg_id": {"type": "string"} },
            "required": ["geo_id", "sdg_id"]
        }
    }
}

# WRONG (Anthropic — do not use)
{ "name": "...", "description": "...", "input_schema": {...} }
```

---

## Testing

```bash
# Unit test SSE helper
pytest tests/orchestration_api/test_sse.py -v

# Integration test: does the relay produce a final event?
curl -N -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"geo_id": "EL30", "sdg_id": "SDG_7"}' | grep "final"
# Expected: one line containing '"type": "final"'
```

**Success criteria:** `POST /analyze` streams events, ends with a `final` event containing a non-empty `recommendation`.

---

## Full task list

See `docs/superpowers/plans/2026-02-28-sustaingraph-mvp.md` → **Chunk 2**
