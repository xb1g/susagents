# Role Card: Person 1 — MCP Server

**You own:** The bridge between the Neo4j knowledge graph and the AI agents.

---

## Your Job in One Sentence

Build 4 Python functions that query Neo4j and return structured data + the raw Cypher query. The AI agents call these functions to "think" about the graph.

---

## What You're Building

```
mcp_server/
├── config.py              ← Neo4j connection env vars
├── neo4j_client.py        ← run_query() helper
├── server.py              ← FastMCP entry point (for MCP protocol support)
└── tools/
    ├── regional_profile.py   ← get_regional_sdg_profile()
    ├── peer_regions.py       ← find_peer_regions()
    ├── indicator_trend.py    ← get_indicator_trend()
    └── policy_mapping.py     ← map_sdg_to_policy()
```

---

## The One Rule

**Every tool function must return this exact shape:**

```python
{
    "result": list,    # list of dicts — the actual data
    "cypher": str,     # the exact Cypher string that was executed
    "metadata": dict   # node labels traversed (for display)
}
```

Person 2 relies on `result` for the agent. Person 3 shows `cypher` in the dashboard. Both break if this contract changes.

---

## Getting Started

```bash
# 1. Install dependencies
pip install fastmcp neo4j python-dotenv pytest

# 2. Make sure .env exists with Neo4j credentials
cat .env  # should have NEO4J_URI, NEO4J_USER, SUSTAINGRAPH_PASSWORD, DATABASE_NAME

# 3. Start Neo4j
docker compose up -d

# 4. Test connection
python -c "from mcp_server.neo4j_client import run_query; print(run_query('RETURN 1 AS n', {}))"
# Expected: {'result': [{'n': 1}], 'cypher': 'RETURN 1 AS n', 'metadata': {}}
```

---

## Your 4 Tools

### Tool 1: `get_regional_sdg_profile(geo_id, sdg_id)`
- **What it does:** Gets all SDG indicator observations for a region
- **Example call:** `get_regional_sdg_profile("EL30", "SDG_7")`
- **Returns:** List of `{indicator_code, value, time}` dicts
- **Key question for Person 4:** How are SDG 7 series codes stored? (`sdg_07_*`? `SDG7_*`?)

### Tool 2: `find_peer_regions(geo_id, sdg_id)`
- **What it does:** Finds other regions that share SDG 7 indicators with Attica
- **Example call:** `find_peer_regions("EL30", "SDG_7")`
- **Returns:** List of `{peer_name, peer_geo_id, shared_indicators}` dicts
- **Key question for Person 4:** What's the zero-padded format of series codes? (`sdg_07` not `sdg7`)

### Tool 3: `get_indicator_trend(indicator_id, geo_id)`
- **What it does:** Gets year-by-year values for one indicator in one region
- **Example call:** `get_indicator_trend("sdg_07_40", "EL30")`
- **Returns:** List of `{time, value}` dicts ordered by year

### Tool 4: `map_sdg_to_policy(sdg_id, geo_id)`
- **What it does:** Returns PolicyFramework nodes related to the SDG
- **Example call:** `map_sdg_to_policy("SDG_7", "EL30")`
- **Returns:** List of `{framework_name, description, policy_areas}` dicts
- **Key question for Person 4:** How does `PolicyFramework` link to `SDG` in the graph?

---

## Dependency on Person 4

**Wait for Person 4 to confirm:**
1. The exact format of series codes (e.g., `sdg_07_40` not `SDG_7_40`)
2. The actual relationship between `SDG` and `PolicyFramework` nodes
3. Whether `geo_id = "EL30"` matches `GeoArea.EUcode` or another property

Until then, start with the stub Cypher in the plan and mark `# TODO: validate with Person 4`.

---

## Stub for Person 2 (if you're not done)

If Person 2 needs to start before your tools are ready, tell them to use this in `mcp_bridge.py`:

```python
def get_regional_sdg_profile(geo_id, sdg_id):
    return {"result": [{"indicator_code": "sdg_07_40", "value": 34.2, "time": "2022-01-01"}],
            "cypher": "-- STUB --", "metadata": {}}
```

---

## Testing Your Tools

```bash
# Run all tool tests
pytest tests/mcp_server/ -v

# Quick smoke test against live Neo4j
python -c "
from mcp_server.tools.regional_profile import get_regional_sdg_profile
result = get_regional_sdg_profile('EL30', 'SDG_7')
print('Records:', len(result['result']))
print('Cypher:', result['cypher'][:80])
"
```

**Success criteria:** Each tool returns a non-empty `result` list for `geo_id="EL30"` and `sdg_id="SDG_7"`.

---

## Full task list

See `docs/superpowers/plans/2026-02-28-sustaingraph-mvp.md` → **Chunk 1**
