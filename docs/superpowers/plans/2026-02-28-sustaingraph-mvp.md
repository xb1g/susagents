# SustainGraph MVP Implementation Plan

> **For Claude:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hackathon-ready MVP: MCP Server (Neo4j tools) + Orchestration API (3-agent Mistral relay + SSE) + Web Dashboard (live agent visualization) demonstrating end-to-end AI-driven sustainability recommendations from the SustainGraph knowledge graph.

**Architecture:** FastMCP server exposes 4 Neo4j Cypher tools as Python functions. FastAPI orchestration backend imports those functions directly (no HTTP between them), runs 3 sequential Mistral Large 3 agents with function calling, and streams SSE events. Next.js dashboard consumes SSE and renders live agent reasoning + final recommendation.

**Tech Stack:** Python 3.11+, `fastmcp`, `neo4j` driver, `fastapi`, `sse-starlette`, `mistralai` SDK (`mistral-large-latest` / Mistral Large 3 v25.12), Next.js 14, Tailwind CSS, shadcn/ui

**Spec:** `docs/superpowers/specs/2026-02-28-sustaingraph-mvp-design.md`

**Team:**
- Person 1 → Chunk 1 (MCP Server)
- Person 2 → Chunk 2 (Orchestration API) — depends on Chunk 1 interface
- Person 3 → Chunk 3 (Dashboard) — can start immediately, mock SSE data
- Person 4 → Chunk 4 (Data Validation + Integration)

---

## Shared Contracts (read before starting)

These are the interfaces between chunks. Agree on these first.

### MCP Tool Signatures (Chunk 1 → Chunk 2)

```python
# Every tool returns this shape
{
  "result": dict | list,     # the data
  "cypher": str,              # the exact Cypher query executed
  "metadata": dict            # node labels, relationship types traversed
}

def get_regional_sdg_profile(geo_id: str, sdg_id: str) -> dict: ...
def find_peer_regions(geo_id: str, sdg_id: str) -> dict: ...
def get_indicator_trend(indicator_id: str, geo_id: str) -> dict: ...
def map_sdg_to_policy(sdg_id: str, geo_id: str) -> dict: ...
```

### SSE Event Schema (Chunk 2 → Chunk 3)

```typescript
type SSEEvent =
  | { type: "agent_start";   agent: "analyst" | "strategist" | "localizer" }
  | { type: "tool_call";     tool: string; input: Record<string, string> }
  | { type: "tool_result";   output: unknown; cypher: string }
  | { type: "agent_thought"; text: string }
  | { type: "agent_done";    agent: string; summary: string }
  | { type: "final";         recommendation: Recommendation; traces: CypherTrace[] }
  | { type: "error";         message: string }

type Recommendation = {
  gap: string;           // "Attica scores 34% on SDG 7, 23% below EU avg"
  peer: string;          // "Jutland, Denmark"
  peer_success: string;  // "Improved from 31% to 71% in 7 years"
  policy_action: string; // "Prioritize offshore wind permitting reform..."
  policy_refs: string[]; // ["EGD Article 3.2", "CSR Scope 2"]
}

type CypherTrace = { tool: string; query: string; summary: string }
```

### Demo Scenario Constants (used by all chunks)

```
Region: Attica, Greece   → geo_id = "EL30"
SDG:    SDG 7            → sdg_id = "SDG_7"
Fallback region:         → geo_id = "EL"  (Greece national level)
```

---

## Chunk 1: MCP Server (Person 1)

**Files:**
- Create: `mcp_server/config.py`
- Create: `mcp_server/neo4j_client.py`
- Create: `mcp_server/tools/regional_profile.py`
- Create: `mcp_server/tools/peer_regions.py`
- Create: `mcp_server/tools/indicator_trend.py`
- Create: `mcp_server/tools/policy_mapping.py`
- Create: `mcp_server/server.py`
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/tools/__init__.py`
- Create: `tests/mcp_server/test_tools.py`

### Task 1.1: Project setup + config

- [ ] **Create `mcp_server/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", os.getenv("SUSTAINGRAPH_PASSWORD", ""))
NEO4J_DATABASE = os.getenv("DATABASE_NAME", "neo4j")
```

- [ ] **Create `.env` file at project root (if not exists)**

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
SUSTAINGRAPH_PASSWORD=your_password_here
DATABASE_NAME=neo4j
MISTRAL_API_KEY=your_mistral_api_key_here
```

- [ ] **Install dependencies**

```bash
pip install fastmcp neo4j python-dotenv
pip install pytest pytest-asyncio  # for tests
```

- [ ] **Commit**

```bash
git add mcp_server/config.py .env.example
git commit -m "feat: add mcp server config"
```

---

### Task 1.2: Neo4j client

- [ ] **Write the failing test first** (`tests/mcp_server/test_tools.py`)

```python
import pytest
from mcp_server.neo4j_client import run_query

def test_run_query_returns_result_and_cypher():
    # Uses real Neo4j — skip if not available
    pytest.importorskip("neo4j")
    result = run_query("RETURN 1 AS n", {})
    assert "result" in result
    assert "cypher" in result
    assert result["result"][0]["n"] == 1
```

- [ ] **Run test to verify it fails**

```bash
pytest tests/mcp_server/test_tools.py::test_run_query_returns_result_and_cypher -v
```
Expected: ImportError or AttributeError (module doesn't exist yet)

- [ ] **Create `mcp_server/neo4j_client.py`**

```python
from neo4j import GraphDatabase
from mcp_server.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

_driver = None

def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver

def run_query(cypher: str, params: dict) -> dict:
    """Execute a Cypher query and return result + the query itself."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, params).data()  # .data() safely serializes all Neo4j types to plain dicts
    return {
        "result": result,
        "cypher": cypher,
        "metadata": {}
    }
```

- [ ] **Run test to verify it passes**

```bash
pytest tests/mcp_server/test_tools.py::test_run_query_returns_result_and_cypher -v
```
Expected: PASS (requires Neo4j running)

- [ ] **Commit**

```bash
git add mcp_server/neo4j_client.py mcp_server/__init__.py tests/
git commit -m "feat: add neo4j client with query runner"
```

---

### Task 1.3: Tool — `get_regional_sdg_profile`

Person 4 provides the validated Cypher. Until then, use this starting query and adjust.

- [ ] **Add test**

```python
# In tests/mcp_server/test_tools.py
from mcp_server.tools.regional_profile import get_regional_sdg_profile

def test_get_regional_sdg_profile_returns_shape():
    result = get_regional_sdg_profile(geo_id="EL30", sdg_id="SDG_7")
    assert "result" in result
    assert "cypher" in result
    # result may be empty list if data not present — that's OK for unit shape test
    assert isinstance(result["result"], list)
```

- [ ] **Create `mcp_server/tools/regional_profile.py`**

```python
from mcp_server.neo4j_client import run_query

CYPHER = """
MATCH (ga:GeoArea)
WHERE ga.EUcode = $geo_id OR ga.ISOalpha3code = $geo_id
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
MATCH (sm)<-[:HAS_METADATA]-(s:Series)<-[:HAS_SERIES]-(i:Indicator)
WHERE sm.seriesCode STARTS WITH $sdg_prefix
RETURN ga.name AS region, i.code AS indicator_code, i.description AS indicator_desc,
       o.value AS value, o.time AS time
ORDER BY o.time DESC
LIMIT 30
"""

def get_regional_sdg_profile(geo_id: str, sdg_id: str) -> dict:
    # sdg_id format: "SDG_7" → prefix "sdg_07" or similar — adjust based on actual data
    sdg_prefix = sdg_id.lower().replace("_", "")  # "sdg7" — Person 4 validates this
    data = run_query(CYPHER, {"geo_id": geo_id, "sdg_prefix": sdg_prefix})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata", "Indicator"]}
    return data
```

> **NOTE for Person 4:** Run this Cypher in Neo4j Browser with `geo_id="EL30"` and adjust the `sdg_prefix` filter to match how SDG codes are actually stored in the graph. Update the CYPHER constant accordingly.

- [ ] **Run test**

```bash
pytest tests/mcp_server/test_tools.py::test_get_regional_sdg_profile_returns_shape -v
```

- [ ] **Commit**

```bash
git add mcp_server/tools/regional_profile.py mcp_server/tools/__init__.py
git commit -m "feat: add get_regional_sdg_profile tool"
```

---

### Task 1.4: Tool — `find_peer_regions`

- [ ] **Add test**

```python
from mcp_server.tools.peer_regions import find_peer_regions

def test_find_peer_regions_returns_shape():
    result = find_peer_regions(geo_id="EL30", sdg_id="SDG_7")
    assert "result" in result
    assert "cypher" in result
```

- [ ] **Create `mcp_server/tools/peer_regions.py`**

```python
from mcp_server.neo4j_client import run_query

CYPHER = """
// Step 1: collect series codes for the target region matching the SDG prefix
MATCH (target:GeoArea)
WHERE target.EUcode = $geo_id OR target.ISOalpha3code = $geo_id
MATCH (target)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
WHERE sm.seriesCode STARTS WITH $sdg_prefix
WITH collect(DISTINCT sm.seriesCode) AS target_series, $geo_id AS target_geo_id

// Step 2: find peers that share those series codes (target_series carried via WITH)
MATCH (peer:GeoArea)
WHERE peer.EUcode <> target_geo_id AND peer.ISOalpha3code <> target_geo_id
MATCH (peer)<-[:REFERS_TO_AREA]-(:Observation)<-[:HAS_OBSERVATION]-(psm:SeriesMetadata)
WHERE psm.seriesCode IN target_series

WITH peer, count(DISTINCT psm.seriesCode) AS shared, size(target_series) AS total
WHERE shared >= 2
RETURN peer.name AS peer_name,
       peer.EUcode AS peer_geo_id,
       shared AS shared_indicators,
       total AS total_indicators
ORDER BY shared DESC
LIMIT 5
"""

def find_peer_regions(geo_id: str, sdg_id: str) -> dict:
    # Build prefix from sdg_id: "SDG_7" → "sdg_07" (zero-padded, underscore preserved)
    # Person 4 must validate the actual prefix against the graph — adjust if needed
    parts = sdg_id.lower().split("_")  # ["sdg", "7"]
    sdg_num = parts[-1].zfill(2)       # "07"
    sdg_prefix = f"sdg_{sdg_num}"      # "sdg_07"
    data = run_query(CYPHER, {"geo_id": geo_id, "sdg_prefix": sdg_prefix})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata"]}
    return data
```

- [ ] **Run test + commit**

```bash
pytest tests/mcp_server/test_tools.py::test_find_peer_regions_returns_shape -v
git add mcp_server/tools/peer_regions.py
git commit -m "feat: add find_peer_regions tool"
```

---

### Task 1.5: Tool — `get_indicator_trend`

- [ ] **Add test**

```python
from mcp_server.tools.indicator_trend import get_indicator_trend

def test_get_indicator_trend_returns_shape():
    result = get_indicator_trend(indicator_id="sdg_07_40", geo_id="EL30")
    assert "result" in result
    assert "cypher" in result
```

- [ ] **Create `mcp_server/tools/indicator_trend.py`**

```python
from mcp_server.neo4j_client import run_query

CYPHER = """
MATCH (ga:GeoArea)
WHERE ga.EUcode = $geo_id OR ga.ISOalpha3code = $geo_id
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata {seriesCode: $indicator_id})
RETURN o.time AS time, o.value AS value
ORDER BY o.time ASC
"""

def get_indicator_trend(indicator_id: str, geo_id: str) -> dict:
    data = run_query(CYPHER, {"geo_id": geo_id, "indicator_id": indicator_id})
    data["metadata"] = {"nodes": ["GeoArea", "Observation", "SeriesMetadata"]}
    return data
```

- [ ] **Run test + commit**

```bash
pytest tests/mcp_server/test_tools.py::test_get_indicator_trend_returns_shape -v
git add mcp_server/tools/indicator_trend.py
git commit -m "feat: add get_indicator_trend tool"
```

---

### Task 1.6: Tool — `map_sdg_to_policy`

- [ ] **Add test**

```python
from mcp_server.tools.policy_mapping import map_sdg_to_policy

def test_map_sdg_to_policy_returns_shape():
    result = map_sdg_to_policy(sdg_id="SDG_7", geo_id="EL30")
    assert "result" in result
    assert "cypher" in result
```

- [ ] **Create `mcp_server/tools/policy_mapping.py`**

```python
from mcp_server.neo4j_client import run_query

CYPHER = """
// Primary: try to find PolicyFrameworks linked to this SDG
OPTIONAL MATCH (s:SDG {code: $sdg_id})-[*1..2]-(pf:PolicyFramework)
WITH collect(DISTINCT pf) AS linked_pf

// Fallback: if no SDG→PolicyFramework path exists, return all frameworks
CALL {
  WITH linked_pf
  RETURN CASE WHEN size(linked_pf) > 0 THEN linked_pf
              ELSE [(pf:PolicyFramework) | pf][0..5]
         END AS frameworks
}
UNWIND frameworks AS pf
OPTIONAL MATCH (pf)-[:HAS_SUBPART]->(pa)
RETURN pf.name AS framework_name,
       pf.description AS description,
       collect(DISTINCT pa.name)[0..3] AS policy_areas
LIMIT 10
"""

def map_sdg_to_policy(sdg_id: str, geo_id: str) -> dict:
    # Person 4: run MATCH (s:SDG)-[r]-(pf:PolicyFramework) RETURN type(r), s.code LIMIT 10
    # in Neo4j Browser to confirm the relationship type and direction, then update CYPHER above.
    data = run_query(CYPHER, {"sdg_id": sdg_id, "geo_id": geo_id})
    data["metadata"] = {"nodes": ["SDG", "PolicyFramework"]}
    return data
```

> **NOTE for Person 4:** Check how `PolicyFramework` nodes link to `SDG` nodes. Run `MATCH (pf:PolicyFramework) RETURN pf LIMIT 5` in Neo4j Browser to see actual properties. Adjust CYPHER to filter by SDG if a relationship exists.

- [ ] **Run test + commit**

```bash
pytest tests/mcp_server/test_tools.py::test_map_sdg_to_policy_returns_shape -v
git add mcp_server/tools/policy_mapping.py
git commit -m "feat: add map_sdg_to_policy tool"
```

---

### Task 1.7: FastMCP server entry point

- [ ] **Create `mcp_server/server.py`**

```python
from fastmcp import FastMCP
from mcp_server.tools.regional_profile import get_regional_sdg_profile
from mcp_server.tools.peer_regions import find_peer_regions
from mcp_server.tools.indicator_trend import get_indicator_trend
from mcp_server.tools.policy_mapping import map_sdg_to_policy

mcp = FastMCP("SustainGraph")

mcp.tool()(get_regional_sdg_profile)
mcp.tool()(find_peer_regions)
mcp.tool()(get_indicator_trend)
mcp.tool()(map_sdg_to_policy)

if __name__ == "__main__":
    mcp.run()
```

- [ ] **Test server starts**

```bash
python mcp_server/server.py
```
Expected: Server starts without errors, prints "SustainGraph MCP server running"

- [ ] **Commit**

```bash
git add mcp_server/server.py
git commit -m "feat: add fastmcp server entry point"
```

---

## Chunk 2: Orchestration API (Person 2)

**Files:**
- Create: `orchestration_api/config.py`
- Create: `orchestration_api/agents/config.py`
- Create: `orchestration_api/agents/sse.py`
- Create: `orchestration_api/agents/orchestrator.py`
- Create: `orchestration_api/mcp_bridge.py`
- Create: `orchestration_api/main.py`
- Create: `tests/orchestration_api/test_sse.py`

**Prerequisite:** Chunk 1 must be importable (`mcp_server/` directory with tools). If Person 1 isn't done, stub the tool functions returning mock data.

### Task 2.1: Setup + dependencies

- [ ] **Install dependencies**

```bash
pip install fastapi sse-starlette mistralai uvicorn python-dotenv
```

- [ ] **Create `orchestration_api/config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MODEL = "mistral-large-latest"  # Mistral Large 3 v25.12
# Use "devstral-2512" (Devstral 2) for any code generation subtasks if needed
```

- [ ] **Add `MISTRAL_API_KEY` to `.env`**

```
MISTRAL_API_KEY=your_mistral_api_key_here
```

- [ ] **Commit**

```bash
git add orchestration_api/config.py orchestration_api/__init__.py
git commit -m "feat: add orchestration api config"
```

---

### Task 2.2: SSE event helpers

- [ ] **Write failing test** (`tests/orchestration_api/test_sse.py`)

```python
from orchestration_api.agents.sse import make_event

def test_make_event_formats_json():
    event = make_event("agent_start", {"agent": "analyst"})
    assert event["event"] == "agent_start"
    assert '"agent": "analyst"' in event["data"]

def test_make_event_handles_nested():
    event = make_event("tool_result", {"output": {"value": 42}, "cypher": "MATCH n"})
    assert "cypher" in event["data"]
```

- [ ] **Run tests to verify they fail**

```bash
pytest tests/orchestration_api/test_sse.py -v
```

- [ ] **Create `orchestration_api/agents/sse.py`**

```python
import json

def make_event(event_type: str, data: dict) -> dict:
    """Format an SSE event dict for sse-starlette."""
    return {
        "event": event_type,
        "data": json.dumps({**data, "type": event_type})
    }
```

- [ ] **Run tests to verify they pass**

```bash
pytest tests/orchestration_api/test_sse.py -v
```

- [ ] **Commit**

```bash
git add orchestration_api/agents/sse.py tests/orchestration_api/test_sse.py
git commit -m "feat: add sse event helpers"
```

---

### Task 2.3: MCP bridge (imports tools as callables)

- [ ] **Create `orchestration_api/mcp_bridge.py`**

```python
"""
Imports MCP tool functions directly as Python callables.
No HTTP — same process, direct function calls.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_server.tools.regional_profile import get_regional_sdg_profile
from mcp_server.tools.peer_regions import find_peer_regions
from mcp_server.tools.indicator_trend import get_indicator_trend
from mcp_server.tools.policy_mapping import map_sdg_to_policy

TOOLS = {
    "get_regional_sdg_profile": get_regional_sdg_profile,
    "find_peer_regions": find_peer_regions,
    "get_indicator_trend": get_indicator_trend,
    "map_sdg_to_policy": map_sdg_to_policy,
}

def call_tool(name: str, inputs: dict) -> dict:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOLS[name](**inputs)
```

> **If Chunk 1 isn't ready yet:** Replace the imports with stubs:
> ```python
> def get_regional_sdg_profile(geo_id, sdg_id):
>     return {"result": [{"indicator": "mock", "value": 34}], "cypher": "-- mock --", "metadata": {}}
> ```

- [ ] **Commit**

```bash
git add orchestration_api/mcp_bridge.py
git commit -m "feat: add mcp bridge for direct tool calls"
```

---

### Task 2.4: Agent configs (OpenCode-style)

- [ ] **Create `orchestration_api/agents/config.py`**

```python
import os
from mistralai import Mistral
from dotenv import load_dotenv
from orchestration_api.config import MODEL

load_dotenv()
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""))

# Mistral uses OpenAI-compatible function calling format
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_regional_sdg_profile",
            "description": "Get current SDG indicator scores for a region vs 2030 targets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "geo_id": {"type": "string", "description": "EU region code e.g. EL30"},
                    "sdg_id": {"type": "string", "description": "SDG code e.g. SDG_7"}
                },
                "required": ["geo_id", "sdg_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_peer_regions",
            "description": "Find regions that shared a similar SDG baseline and improved significantly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "geo_id": {"type": "string"},
                    "sdg_id": {"type": "string"}
                },
                "required": ["geo_id", "sdg_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_indicator_trend",
            "description": "Get year-by-year trend for a specific indicator in a region.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indicator_id": {"type": "string"},
                    "geo_id": {"type": "string"}
                },
                "required": ["indicator_id", "geo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_sdg_to_policy",
            "description": "Map an SDG gap to applicable policy frameworks (EGD, CSR, NDC).",
            "parameters": {
                "type": "object",
                "properties": {
                    "sdg_id": {"type": "string"},
                    "geo_id": {"type": "string"}
                },
                "required": ["sdg_id", "geo_id"]
            }
        }
    }
]

AGENTS = {
    "analyst": {
        "model": MODEL,
        "system": (
            "You are the Diagnostic Analyst for SustainGraph. Given a region and SDG, "
            "use your tools to identify the most critical sustainability gap. "
            "Compare current indicator values to EU averages and 2030 targets. "
            "Be precise — cite specific numbers and years. "
            "End with a one-paragraph summary of the gap finding."
        ),
        "tools": ["get_regional_sdg_profile", "get_indicator_trend"],
    },
    "strategist": {
        "model": MODEL,
        "system": (
            "You are the Peer-Discovery Strategist for SustainGraph. "
            "You receive a gap analysis from the Analyst. "
            "Use your tools to find peer regions that started from a similar baseline "
            "and achieved significant improvement. Explain what made them succeed. "
            "End with a one-paragraph summary naming the best peer region and their key intervention."
        ),
        "tools": ["find_peer_regions", "get_indicator_trend"],
    },
    "localizer": {
        "model": MODEL,
        "system": (
            "You are the Localization & Compliance Officer for SustainGraph. "
            "You receive a peer success story from the Strategist. "
            "Use your tools to map their successful interventions to policy frameworks "
            "applicable to the target region. Cite specific EGD articles, CSR obligations, or NDC commitments. "
            "End with a concrete 2-3 sentence policy recommendation the region can act on."
        ),
        "tools": ["map_sdg_to_policy"],
    }
}
```

- [ ] **Commit**

```bash
git add orchestration_api/agents/config.py orchestration_api/agents/__init__.py
git commit -m "feat: add opencode-style agent configs"
```

---

### Task 2.5: Orchestrator (3-agent relay with streaming)

- [ ] **Create `orchestration_api/agents/orchestrator.py`**

```python
import json
from typing import AsyncGenerator
from orchestration_api.agents.config import AGENTS, TOOL_SCHEMAS, client
from orchestration_api.agents.sse import make_event
from orchestration_api.mcp_bridge import call_tool

def _tools_for_agent(agent_name: str) -> list:
    """Return Mistral-format tool schemas for the given agent."""
    allowed = AGENTS[agent_name]["tools"]
    return [t for t in TOOL_SCHEMAS if t["function"]["name"] in allowed]

async def run_relay(geo_id: str, sdg_id: str) -> AsyncGenerator[dict, None]:
    """Run analyst → strategist → localizer relay, yielding SSE events."""

    context = ""  # accumulated summaries passed between agents
    traces = []   # cypher traces for final panel
    summaries = {}

    initial_user_message = (
        f"Analyze region {geo_id} for SDG {sdg_id}. "
        f"Use your tools to investigate and provide your findings."
    )

    for agent_name in ["analyst", "strategist", "localizer"]:
        agent = AGENTS[agent_name]
        yield make_event("agent_start", {"agent": agent_name})

        messages = [
            {"role": "system", "content": agent["system"]},
            {"role": "user", "content": (
                initial_user_message if not context
                else f"Previous findings:\n{context}\n\nNow perform your role for region {geo_id}, SDG {sdg_id}."
            )}
        ]

        tools = _tools_for_agent(agent_name)

        # Mistral agentic loop — keep going until finish_reason != "tool_calls"
        while True:
            response = client.chat.complete(
                model=agent["model"],
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            choice = response.choices[0]
            message = choice.message

            # Emit text content as agent thoughts
            if message.content and message.content.strip():
                yield make_event("agent_thought", {"text": message.content})

            # No more tool calls — agent is done
            if choice.finish_reason != "tool_calls" or not message.tool_calls:
                break

            # Add assistant message to history (serialize Pydantic model → plain dict for consistency)
            messages.append(message.model_dump())

            # Handle each tool call
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                yield make_event("tool_call", {
                    "tool": tool_name,
                    "input": tool_args
                })

                tool_output = call_tool(tool_name, tool_args)

                yield make_event("tool_result", {
                    "output": tool_output["result"],
                    "cypher": tool_output["cypher"]
                })

                traces.append({
                    "tool": tool_name,
                    "query": tool_output["cypher"],
                    "summary": f"{tool_name}({tool_args})"
                })

                # Mistral expects tool results as role="tool" messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output["result"])
                })

        # Extract final summary from last message text
        summary = message.content if message.content else f"{agent_name} completed."
        summaries[agent_name] = summary
        context += f"\n\n=== {agent_name.upper()} FINDINGS ===\n{summary}"

        yield make_event("agent_done", {"agent": agent_name, "summary": summary})

    # Build final recommendation
    # Extract peer name from strategist summary heuristically (first proper noun after "Peer:" or region name)
    # For the hackathon, the Localizer is prompted to name the peer explicitly — it will appear in policy_action
    yield make_event("final", {
        "recommendation": {
            "gap": summaries.get("analyst", ""),
            "peer": _extract_peer_name(summaries.get("strategist", "")),
            "peer_success": summaries.get("strategist", ""),
            "policy_action": summaries.get("localizer", ""),
            "policy_refs": _extract_policy_refs(summaries.get("localizer", "")),
        },
        "traces": traces
    })

def _extract_peer_name(strategist_summary: str) -> str:
    """Best-effort extraction of the peer region name from strategist output."""
    import re
    # Look for patterns like "Jutland, Denmark" or region names followed by country
    match = re.search(r'([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z]+)?)\s+(?:region|NUTS|achieved|improved)', strategist_summary)
    return match.group(1).strip() if match else "See peer analysis above"

def _extract_policy_refs(localizer_summary: str) -> list[str]:
    """Best-effort extraction of policy references like 'EGD Article 3.2'."""
    import re
    refs = re.findall(r'(?:EGD|CSR|NDC|Article|Directive)\s+[\w\s\.]+\d+[\.\d]*', localizer_summary)
    return [r.strip() for r in refs[:4]] if refs else []
```

- [ ] **Commit**

```bash
git add orchestration_api/agents/orchestrator.py
git commit -m "feat: add 3-agent relay orchestrator with sse streaming"
```

---

### Task 2.6: FastAPI app + `/analyze` endpoint

- [ ] **Create `orchestration_api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from orchestration_api.agents.orchestrator import run_relay

app = FastAPI(title="SustainGraph Orchestration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon — lock down for prod
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    geo_id: str = "EL30"
    sdg_id: str = "SDG_7"

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    return EventSourceResponse(
        run_relay(request.geo_id, request.sdg_id),
        media_type="text/event-stream"
    )

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Test the server starts**

```bash
uvicorn orchestration_api.main:app --reload --port 8000
```
Expected: Server starts, `GET /health` returns `{"status": "ok"}`

- [ ] **Smoke test the endpoint (in another terminal)**

```bash
curl -N -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"geo_id": "EL30", "sdg_id": "SDG_7"}'
```
Expected: SSE events stream to terminal

- [ ] **Commit**

```bash
git add orchestration_api/main.py
git commit -m "feat: add fastapi app with /analyze sse endpoint"
```

---

## Chunk 3: Web Dashboard (Person 3)

**Files:**
- Create: `dashboard/` (Next.js project)
- Create: `dashboard/lib/types.ts`
- Create: `dashboard/lib/constants.ts`
- Create: `dashboard/hooks/useSSEStream.ts`
- Create: `dashboard/components/AgentCard.tsx`
- Create: `dashboard/components/ToolCallCard.tsx`
- Create: `dashboard/components/AgentFeed.tsx`
- Create: `dashboard/components/Recommendation.tsx`
- Create: `dashboard/components/RegionSelector.tsx`
- Create: `dashboard/components/SDGSelector.tsx`
- Create: `dashboard/app/page.tsx`

**Can start immediately** — use mock SSE data until Chunk 2 is ready.

### Task 3.1: Next.js project setup

- [ ] **Scaffold Next.js project**

```bash
cd sustaingraph
npx create-next-app@latest dashboard \
  --typescript --tailwind --eslint --app \
  --no-src-dir --import-alias "@/*"
cd dashboard
```

- [ ] **Install shadcn/ui + dependencies**

```bash
npx shadcn@latest init
# When prompted: Default style, Slate base color, CSS variables
npx shadcn@latest add card badge button select separator scroll-area
npm install lucide-react
```

- [ ] **Update `dashboard/app/layout.tsx`** to set dark background

```tsx
import type { Metadata } from "next"
import { Inter, JetBrains_Mono } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" })
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" })

export const metadata: Metadata = {
  title: "SustainGraph Intelligence",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${mono.variable} bg-zinc-950 text-zinc-100 antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

- [ ] **Commit**

```bash
git add dashboard/
git commit -m "feat: scaffold next.js dashboard"
```

---

### Task 3.2: Types and constants

- [ ] **Create `dashboard/lib/types.ts`**

```typescript
export type AgentName = "analyst" | "strategist" | "localizer"
export type AgentStatus = "waiting" | "active" | "done"

export type SSEEventType =
  | { type: "agent_start"; agent: AgentName }
  | { type: "tool_call"; tool: string; input: Record<string, string> }
  | { type: "tool_result"; output: unknown; cypher: string }
  | { type: "agent_thought"; text: string }
  | { type: "agent_done"; agent: AgentName; summary: string }
  | { type: "final"; recommendation: Recommendation; traces: CypherTrace[] }
  | { type: "error"; message: string }

export type Recommendation = {
  gap: string
  peer: string           // e.g. "Jutland, Denmark"
  peer_success: string
  policy_action: string
  policy_refs: string[]  // e.g. ["EGD Article 3.2", "CSR Scope 2"]
}

export type CypherTrace = {
  tool: string
  query: string
  summary: string
}

export type AgentStep =
  | { kind: "thought"; text: string }
  | { kind: "tool_call"; tool: string; input: Record<string, string> }
  | { kind: "tool_result"; output: unknown; cypher: string }
```

- [ ] **Create `dashboard/lib/constants.ts`**

```typescript
export const REGIONS = [
  { label: "Attica, Greece", value: "EL30" },
  { label: "Greece", value: "EL" },
  { label: "Jutland, Denmark", value: "DK05" },
  { label: "Germany", value: "DE" },
  { label: "France", value: "FR" },
]

export const SDGS = [
  { label: "SDG 7 — Affordable & Clean Energy", value: "SDG_7" },
  { label: "SDG 13 — Climate Action", value: "SDG_13" },
  { label: "SDG 11 — Sustainable Cities", value: "SDG_11" },
  { label: "SDG 8 — Decent Work", value: "SDG_8" },
]

export const AGENT_LABELS: Record<string, string> = {
  analyst: "Diagnostic Analyst",
  strategist: "Peer-Discovery Strategist",
  localizer: "Localization Officer",
}

export const AGENT_COLORS: Record<string, string> = {
  analyst: "text-blue-400",
  strategist: "text-purple-400",
  localizer: "text-green-400",
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
```

- [ ] **Create `dashboard/.env.local`** (Next.js reads this, not root `.env`)

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Create `dashboard/app/api/mock/route.ts`** for Person 3 to develop against before Chunk 2 is ready

```typescript
import { NextRequest } from "next/server"

// Mock SSE stream for local development — remove before demo
const MOCK_EVENTS = [
  { type: "agent_start", agent: "analyst" },
  { type: "agent_thought", text: "Querying SDG 7 indicators for Attica, Greece..." },
  { type: "tool_call", tool: "get_regional_sdg_profile", input: { geo_id: "EL30", sdg_id: "SDG_7" } },
  { type: "tool_result", cypher: "MATCH (ga:GeoArea {EUcode: 'EL30'})...", output: [{ indicator_code: "sdg_07_40", value: 34.2, time: "2022-01-01" }] },
  { type: "agent_thought", text: "Attica scores 34.2% on renewable energy share, 23% below EU average of 57%." },
  { type: "agent_done", agent: "analyst", summary: "Attica, Greece scores 34.2% on SDG 7 renewable energy share, significantly below the EU 2030 target of 42% and the current EU average of 57%." },
  { type: "agent_start", agent: "strategist" },
  { type: "tool_call", tool: "find_peer_regions", input: { geo_id: "EL30", sdg_id: "SDG_7" } },
  { type: "tool_result", cypher: "MATCH (target:GeoArea) WHERE target.EUcode = 'EL30'...", output: [{ peer_name: "West Jutland", peer_geo_id: "DK041", shared_indicators: 5 }] },
  { type: "agent_done", agent: "strategist", summary: "West Jutland, Denmark achieved 71% renewable share by 2022 from a 31% baseline in 2015 — driven by offshore wind permitting reform and municipal energy cooperatives." },
  { type: "agent_start", agent: "localizer" },
  { type: "tool_call", tool: "map_sdg_to_policy", input: { sdg_id: "SDG_7", geo_id: "EL30" } },
  { type: "tool_result", cypher: "MATCH (s:SDG {code: 'SDG_7'})--(pf:PolicyFramework)...", output: [{ framework_name: "European Green Deal", policy_areas: ["Energy", "Climate"] }] },
  { type: "agent_done", agent: "localizer", summary: "Attica should prioritize offshore wind permitting under EGD Article 3.2 and establish municipal energy cooperatives aligned with CSR Scope 2 reporting obligations." },
  { type: "final", recommendation: { gap: "Attica scores 34.2% renewable share, 23% below EU avg", peer: "West Jutland, Denmark", peer_success: "Improved from 31% to 71% in 7 years via offshore wind reform", policy_action: "Prioritize offshore wind permitting under EGD Article 3.2", policy_refs: ["EGD Article 3.2", "CSR Scope 2"] }, traces: [{ tool: "get_regional_sdg_profile", query: "MATCH (ga:GeoArea {EUcode: 'EL30'})...", summary: "Regional profile query" }] }
]

export async function POST(_req: NextRequest) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      for (const event of MOCK_EVENTS) {
        await new Promise(r => setTimeout(r, 800))
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
      }
      controller.close()
    }
  })
  return new Response(stream, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } })
}
```

> **Person 3:** Point `API_URL` to `/api/mock` in `constants.ts` during development. Switch back to `http://localhost:8000` before demo.

- [ ] **Commit**

```bash
git add dashboard/lib/ dashboard/.env.local dashboard/app/api/
git commit -m "feat: add types, constants, env config, and mock sse endpoint"
```

---

### Task 3.3: SSE stream hook

- [ ] **Create `dashboard/hooks/useSSEStream.ts`**

```typescript
"use client"
import { useState, useCallback, useRef } from "react"
import type { SSEEventType, AgentName, AgentStatus, AgentStep, Recommendation, CypherTrace } from "@/lib/types"
import { API_URL } from "@/lib/constants"

export type AgentState = {
  status: AgentStatus
  steps: AgentStep[]
  summary: string
}

export type StreamState = {
  agents: Record<AgentName, AgentState>
  recommendation: Recommendation | null
  traces: CypherTrace[]
  isStreaming: boolean
  error: string | null
}

const initialAgents = (): Record<AgentName, AgentState> => ({
  analyst:    { status: "waiting", steps: [], summary: "" },
  strategist: { status: "waiting", steps: [], summary: "" },
  localizer:  { status: "waiting", steps: [], summary: "" },
})

export function useSSEStream() {
  const [state, setState] = useState<StreamState>({
    agents: initialAgents(),
    recommendation: null,
    traces: [],
    isStreaming: false,
    error: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const analyze = useCallback(async (geoId: string, sdgId: string) => {
    // Reset state
    setState({ agents: initialAgents(), recommendation: null, traces: [], isStreaming: true, error: null })
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ geo_id: geoId, sdg_id: sdgId }),
        signal: abortRef.current.signal,
      })

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // Parse SSE lines
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""

        for (const line of lines) {
          if (!line.startsWith("data:")) continue
          try {
            const event: SSEEventType = JSON.parse(line.slice(5).trim())
            setState(prev => applyEvent(prev, event))
          } catch { /* skip malformed */ }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        setState(prev => ({ ...prev, error: err.message, isStreaming: false }))
      }
    } finally {
      setState(prev => ({ ...prev, isStreaming: false }))
    }
  }, [])

  return { state, analyze }
}

function applyEvent(prev: StreamState, event: SSEEventType): StreamState {
  switch (event.type) {
    case "agent_start":
      return { ...prev, agents: { ...prev.agents, [event.agent]: { ...prev.agents[event.agent], status: "active" } } }

    case "agent_thought":
      return addStep(prev, getActiveAgent(prev), { kind: "thought", text: event.text })

    case "tool_call":
      return addStep(prev, getActiveAgent(prev), { kind: "tool_call", tool: event.tool, input: event.input })

    case "tool_result":
      return addStep(prev, getActiveAgent(prev), { kind: "tool_result", output: event.output, cypher: event.cypher })

    case "agent_done":
      return { ...prev, agents: { ...prev.agents, [event.agent]: { ...prev.agents[event.agent], status: "done", summary: event.summary } } }

    case "final":
      return { ...prev, recommendation: event.recommendation, traces: event.traces }

    case "error":
      return { ...prev, error: event.message }

    default:
      return prev
  }
}

function getActiveAgent(state: StreamState): AgentName {
  const active = (Object.keys(state.agents) as AgentName[]).find(a => state.agents[a].status === "active")
  return active ?? "analyst"
}

function addStep(prev: StreamState, agent: AgentName, step: AgentStep): StreamState {
  return {
    ...prev,
    agents: {
      ...prev.agents,
      [agent]: { ...prev.agents[agent], steps: [...prev.agents[agent].steps, step] }
    }
  }
}
```

- [ ] **Commit**

```bash
git add dashboard/hooks/useSSEStream.ts
git commit -m "feat: add sse stream hook with state management"
```

---

### Task 3.4: ToolCallCard component

- [ ] **Create `dashboard/components/ToolCallCard.tsx`**

```tsx
"use client"
import { useState } from "react"
import { ChevronDown, ChevronRight, Zap } from "lucide-react"

type Props = {
  tool: string
  input: Record<string, string>
  cypher?: string
  output?: unknown
}

export function ToolCallCard({ tool, input, cypher, output }: Props) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-zinc-800 rounded-md overflow-hidden text-xs font-mono">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-zinc-900 hover:bg-zinc-800 text-left"
      >
        <Zap className="h-3 w-3 text-yellow-400 shrink-0" />
        <span className="text-yellow-300">{tool}</span>
        <span className="text-zinc-500">({JSON.stringify(input)})</span>
        {expanded ? <ChevronDown className="h-3 w-3 ml-auto" /> : <ChevronRight className="h-3 w-3 ml-auto" />}
      </button>

      {expanded && (
        <div className="px-3 py-2 space-y-2 bg-zinc-950">
          {cypher && (
            <div>
              <p className="text-zinc-500 mb-1">Cypher Query:</p>
              <pre className="text-green-400 whitespace-pre-wrap text-[10px] leading-relaxed">{cypher}</pre>
            </div>
          )}
          {output && (
            <div>
              <p className="text-zinc-500 mb-1">Result:</p>
              <pre className="text-zinc-300 whitespace-pre-wrap text-[10px]">
                {JSON.stringify(output, null, 2).slice(0, 500)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Commit**

```bash
git add dashboard/components/ToolCallCard.tsx
git commit -m "feat: add tool call card with cypher expansion"
```

---

### Task 3.5: AgentCard + AgentFeed components

- [ ] **Create `dashboard/components/AgentCard.tsx`**

```tsx
import { AGENT_LABELS, AGENT_COLORS } from "@/lib/constants"
import { ToolCallCard } from "./ToolCallCard"
import type { AgentName, AgentStatus, AgentStep } from "@/lib/types"
import { CheckCircle, Circle, Loader2 } from "lucide-react"

const StatusIcon = ({ status }: { status: AgentStatus }) => {
  if (status === "done")    return <CheckCircle className="h-4 w-4 text-green-400" />
  if (status === "active")  return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />
  return <Circle className="h-4 w-4 text-zinc-600" />
}

type Props = { name: AgentName; status: AgentStatus; steps: AgentStep[]; summary: string }

export function AgentCard({ name, status, steps, summary }: Props) {
  const color = AGENT_COLORS[name]
  const label = AGENT_LABELS[name]

  // Buffer: pair tool_call with subsequent tool_result
  const pairedSteps: Array<{ call?: AgentStep & { kind: "tool_call" }; result?: AgentStep & { kind: "tool_result" }; thought?: AgentStep & { kind: "thought" } }> = []
  let pendingCall: (AgentStep & { kind: "tool_call" }) | null = null

  for (const step of steps) {
    if (step.kind === "tool_call") { pendingCall = step }
    else if (step.kind === "tool_result" && pendingCall) {
      pairedSteps.push({ call: pendingCall, result: step })
      pendingCall = null
    } else if (step.kind === "thought") {
      pairedSteps.push({ thought: step })
    }
  }

  return (
    <div className={`border rounded-lg p-3 space-y-2 transition-all ${status === "waiting" ? "border-zinc-800 opacity-40" : "border-zinc-700"}`}>
      <div className="flex items-center gap-2">
        <StatusIcon status={status} />
        <span className={`font-semibold text-sm ${color}`}>{label}</span>
      </div>

      {status !== "waiting" && (
        <div className="space-y-2 pl-6">
          {pairedSteps.map((s, i) => (
            <div key={i}>
              {s.thought && <p className="text-zinc-400 text-xs leading-relaxed">{s.thought.text}</p>}
              {s.call && (
                <ToolCallCard
                  tool={s.call.tool}
                  input={s.call.input}
                  cypher={s.result?.cypher}
                  output={s.result?.output}
                />
              )}
            </div>
          ))}
          {status === "done" && summary && (
            <p className="text-zinc-300 text-xs border-l-2 border-zinc-600 pl-2 italic">{summary}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Create `dashboard/components/AgentFeed.tsx`**

```tsx
import type { StreamState } from "@/hooks/useSSEStream"
import { AgentCard } from "./AgentCard"
import type { AgentName } from "@/lib/types"

const AGENT_ORDER: AgentName[] = ["analyst", "strategist", "localizer"]

export function AgentFeed({ state }: { state: StreamState }) {
  return (
    <div className="space-y-3">
      {AGENT_ORDER.map(name => (
        <AgentCard
          key={name}
          name={name}
          status={state.agents[name].status}
          steps={state.agents[name].steps}
          summary={state.agents[name].summary}
        />
      ))}
    </div>
  )
}
```

- [ ] **Commit**

```bash
git add dashboard/components/AgentCard.tsx dashboard/components/AgentFeed.tsx
git commit -m "feat: add agent card and feed components"
```

---

### Task 3.6: Recommendation panel

- [ ] **Create `dashboard/components/Recommendation.tsx`**

```tsx
"use client"
import { useState } from "react"
import type { Recommendation, CypherTrace } from "@/lib/types"
import { ChevronDown, ChevronUp } from "lucide-react"

type Props = { recommendation: Recommendation | null; traces: CypherTrace[] }

export function RecommendationPanel({ recommendation, traces }: Props) {
  const [tracesOpen, setTracesOpen] = useState(false)

  if (!recommendation) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-600 text-sm">
        Recommendation will appear here after analysis
      </div>
    )
  }

  return (
    <div className="space-y-4 animate-in fade-in duration-500">
      <div className="space-y-3">
        <Section label="Sustainability Gap" color="text-red-400" content={recommendation.gap} />
        <Section label="Peer Success Story" color="text-purple-400" content={recommendation.peer_success} />
        <Section label="Policy Action" color="text-green-400" content={recommendation.policy_action} />
      </div>

      {traces.length > 0 && (
        <div>
          <button
            onClick={() => setTracesOpen(o => !o)}
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300"
          >
            {tracesOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Graph Traces ({traces.length} queries)
          </button>
          {tracesOpen && (
            <div className="mt-2 space-y-2">
              {traces.map((t, i) => (
                <div key={i} className="text-[10px] font-mono border border-zinc-800 rounded p-2">
                  <p className="text-yellow-400 mb-1">{t.tool}</p>
                  <pre className="text-green-400 whitespace-pre-wrap">{t.query}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Section({ label, color, content }: { label: string; color: string; content: string }) {
  return (
    <div className="border border-zinc-800 rounded-md p-3 space-y-1">
      <p className={`text-xs font-semibold uppercase tracking-wider ${color}`}>{label}</p>
      <p className="text-zinc-300 text-sm leading-relaxed">{content}</p>
    </div>
  )
}
```

- [ ] **Commit**

```bash
git add dashboard/components/Recommendation.tsx
git commit -m "feat: add recommendation panel with cypher traces"
```

---

### Task 3.7: Main page

- [ ] **Create `dashboard/components/RegionSelector.tsx`**

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { REGIONS } from "@/lib/constants"

export function RegionSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="bg-zinc-900 border-zinc-700">
        <SelectValue placeholder="Select region" />
      </SelectTrigger>
      <SelectContent>
        {REGIONS.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
      </SelectContent>
    </Select>
  )
}
```

- [ ] **Create `dashboard/components/SDGSelector.tsx`**

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { SDGS } from "@/lib/constants"

export function SDGSelector({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="bg-zinc-900 border-zinc-700">
        <SelectValue placeholder="Select SDG" />
      </SelectTrigger>
      <SelectContent>
        {SDGS.map(s => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
      </SelectContent>
    </Select>
  )
}
```

- [ ] **Create `dashboard/app/page.tsx`**

```tsx
"use client"
import { useState } from "react"
import { useSSEStream } from "@/hooks/useSSEStream"
import { RegionSelector } from "@/components/RegionSelector"
import { SDGSelector } from "@/components/SDGSelector"
import { AgentFeed } from "@/components/AgentFeed"
import { RecommendationPanel } from "@/components/Recommendation"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

export default function Home() {
  const [geoId, setGeoId] = useState("EL30")
  const [sdgId, setSdgId] = useState("SDG_7")
  const { state, analyze } = useSSEStream()

  return (
    <main className="min-h-screen p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="h-2 w-2 rounded-full bg-green-400" />
        <h1 className="text-lg font-semibold tracking-tight text-zinc-100">
          SustainGraph Intelligence
        </h1>
        <span className="text-xs text-zinc-500 font-mono">v0.1-mvp</span>
      </div>

      {/* 3-column layout */}
      <div className="grid grid-cols-[280px_1fr_360px] gap-4 flex-1">

        {/* Column 1: Input */}
        <div className="flex flex-col gap-4">
          <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
            <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Configure</h2>
            <div className="space-y-2">
              <label className="text-xs text-zinc-500">Region</label>
              <RegionSelector value={geoId} onChange={setGeoId} />
            </div>
            <div className="space-y-2">
              <label className="text-xs text-zinc-500">SDG Target</label>
              <SDGSelector value={sdgId} onChange={setSdgId} />
            </div>
            <Button
              onClick={() => analyze(geoId, sdgId)}
              disabled={state.isStreaming}
              className="w-full bg-green-600 hover:bg-green-700 text-white"
            >
              {state.isStreaming
                ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Analyzing…</>
                : "Analyze"}
            </Button>
          </div>

          {state.error && (
            <div className="border border-red-900 rounded-lg p-3 text-xs text-red-400">
              {state.error}
            </div>
          )}
        </div>

        {/* Column 2: Agent live feed */}
        <div className="border border-zinc-800 rounded-lg p-4 overflow-auto">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Agent Live Feed</h2>
          <AgentFeed state={state} />
        </div>

        {/* Column 3: Recommendation */}
        <div className="border border-zinc-800 rounded-lg p-4 overflow-auto">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">Recommendation</h2>
          <RecommendationPanel
            recommendation={state.recommendation}
            traces={state.traces}
          />
        </div>
      </div>
    </main>
  )
}
```

- [ ] **Run dev server and verify layout**

```bash
cd dashboard && npm run dev
```
Open `http://localhost:3000` — verify 3-column layout renders, selectors work, button is clickable.

- [ ] **Commit**

```bash
git add dashboard/app/page.tsx dashboard/components/RegionSelector.tsx dashboard/components/SDGSelector.tsx
git commit -m "feat: add main page with 3-column layout"
```

---

## Chunk 4: Data Validation + Integration (Person 4)

**Files:**
- Create: `cypher_queries/01_regional_profile.cypher`
- Create: `cypher_queries/02_peer_regions.cypher`
- Create: `cypher_queries/03_indicator_trend.cypher`
- Create: `cypher_queries/04_policy_mapping.cypher`
- Create: `scripts/validate_demo_data.py`

### Task 4.1: Explore the graph schema

- [ ] **Run these in Neo4j Browser (`http://localhost:7474`)**

```cypher
// 1. See all node labels
CALL db.labels()

// 2. See all relationship types
CALL db.relationshipTypes()

// 3. Find GeoArea for Attica
MATCH (ga:GeoArea)
WHERE ga.name CONTAINS "Attica" OR ga.EUcode = "EL30"
RETURN ga LIMIT 5

// 4. Find what SDG nodes look like
MATCH (s:SDG) RETURN s LIMIT 5

// 5. Find Indicator → SDG relationships
MATCH (i:Indicator)-[r]->(s:SDG) RETURN type(r), i, s LIMIT 5

// 6. Find PolicyFramework nodes
MATCH (pf:PolicyFramework) RETURN pf LIMIT 10

// 7. Find Series codes starting with SDG 7
MATCH (s:Series) WHERE s.code CONTAINS "sdg_07" OR s.code CONTAINS "SDG7"
RETURN s.code LIMIT 10
```

- [ ] **Document findings** — note the actual property names and relationship types used in the graph. Share with Person 1 to update Cypher queries.

---

### Task 4.2: Validate demo data path

- [ ] **Create `scripts/validate_demo_data.py`**

```python
"""Validate that the Attica × SDG 7 demo scenario has sufficient data."""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("SUSTAINGRAPH_PASSWORD", ""))
)

def check(label, query, params={}):
    with driver.session(database=os.getenv("DATABASE_NAME", "neo4j")) as s:
        result = list(s.run(query, params))
        status = "✅" if result else "❌"
        print(f"{status} {label}: {len(result)} records")
        if result:
            print(f"   Sample: {dict(result[0])}")
        return result

# Check GeoArea for Attica
check("GeoArea EL30", "MATCH (ga:GeoArea) WHERE ga.EUcode = $c RETURN ga", {"c": "EL30"})

# Check observations exist
check("Observations for EL30", """
    MATCH (ga:GeoArea {EUcode: 'EL30'})<-[:REFERS_TO_AREA]-(o:Observation)
    RETURN o LIMIT 3
""")

# Check SDG 7 indicators exist
check("SDG 7 indicators", """
    MATCH (s:Series) WHERE toLower(s.code) CONTAINS 'sdg_07' OR toLower(s.code) CONTAINS 'sdg07'
    RETURN s.code LIMIT 5
""")

# Check PolicyFramework
check("PolicyFrameworks", "MATCH (pf:PolicyFramework) RETURN pf.name LIMIT 5")

# Check peer regions
check("Peer regions with shared indicators", """
    MATCH (ga:GeoArea {EUcode: 'EL30'})<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
    WITH collect(DISTINCT sm.seriesCode) AS codes
    MATCH (peer:GeoArea)
    WHERE peer.EUcode <> 'EL30'
    MATCH (peer)<-[:REFERS_TO_AREA]-(:Observation)<-[:HAS_OBSERVATION]-(psm:SeriesMetadata)
    WHERE psm.seriesCode IN codes
    RETURN peer.name, count(DISTINCT psm.seriesCode) AS shared
    ORDER BY shared DESC LIMIT 5
""")

driver.close()
```

- [ ] **Run the validation**

```bash
python scripts/validate_demo_data.py
```

- [ ] **If any check fails:** Investigate in Neo4j Browser and update the Cypher templates in Chunk 1 tools accordingly. Share updates with Person 1.

---

### Task 4.3: Write and validate final Cypher queries

Using findings from Task 4.1, write the definitive versions of each query and save them.

- [ ] **Create `cypher_queries/01_regional_profile.cypher`** (replace with validated query)
- [ ] **Create `cypher_queries/02_peer_regions.cypher`**
- [ ] **Create `cypher_queries/03_indicator_trend.cypher`**
- [ ] **Create `cypher_queries/04_policy_mapping.cypher`**

Test each in Neo4j Browser with `EL30` and `SDG_7` parameters before handing to Person 1.

- [ ] **Commit**

```bash
git add cypher_queries/ scripts/
git commit -m "feat: add validated cypher queries and data validation script"
```

---

### Task 4.4: End-to-end integration test

Run this after all three chunks are complete.

- [ ] **Start all services**

```bash
# Terminal 1: Neo4j (already running via docker-compose)
docker compose up

# Terminal 2: Orchestration API
cd sustaingraph
uvicorn orchestration_api.main:app --port 8000

# Terminal 3: Dashboard
cd dashboard && npm run dev
```

- [ ] **Test the full flow**

1. Open `http://localhost:3000`
2. Select "Attica, Greece" + "SDG 7"
3. Click Analyze
4. Verify: all 3 agents activate sequentially
5. Verify: tool calls expand to show Cypher + results
6. Verify: recommendation panel populates at the end
7. Verify: Cypher Traces section is expandable

- [ ] **Fix any integration issues** — coordinate with Persons 1, 2, 3

- [ ] **Record a 60-second screen capture** for the pitch

- [ ] **Final commit**

```bash
git add .
git commit -m "feat: sustaingraph mvp - end to end working"
```

---

## Quick Start Reference

```bash
# 1. Environment
cp .env.example .env  # fill in passwords + MISTRAL_API_KEY

# 2. Neo4j
docker compose up -d

# 3. Python deps
pip install fastmcp neo4j fastapi sse-starlette mistralai uvicorn python-dotenv pytest

# 4. Orchestration API
uvicorn orchestration_api.main:app --port 8000 --reload

# 5. Dashboard
cd dashboard && npm install && npm run dev

# 6. Open http://localhost:3000
```

## Pitch Script (Person 4)

**Slide 1 — Problem (30s):** Sustainability data is siloed across Eurostat, UN, and local PDFs. Policy planners can't see the connections. They can't learn from what worked elsewhere.

**Slide 2 — Architecture (30s):** SustainGraph is a Neo4j knowledge graph of 17 SDGs, 200+ indicators, and EU policy frameworks. We built an MCP server that exposes it as AI tools, and a 3-agent Mistral Large relay that traverses it like a human analyst would — Diagnostic Analyst → Peer Strategist → Policy Localizer.

**Slide 3 — Live Demo (60s):** [run the demo, let the agents speak for themselves]
