# SustainGraph MVP Design — Agentic Intelligence Ecosystem

**Date:** 2026-02-28
**Context:** Hackathon MVP (24–48 hours), team of 4
**Audience:** Technical/developers
**Goal:** Demonstrate end-to-end AI agent traversal of the SustainGraph Knowledge Graph, with live streaming visualization

---

## 1. Vision

A web dashboard where a developer picks a region and an SDG, then watches three AI agents work in real-time — querying the Neo4j graph, reasoning over results, and handing off to the next agent — culminating in a traceable, evidence-based policy recommendation.

**Demo scenario:** Attica, Greece × SDG 7 (Clean Energy)
→ Analyst finds -23% gap vs EU avg
→ Strategist finds Jutland, Denmark as peer success case
→ Localizer maps Jutland's offshore wind policy to EGD Article 3.2 + CSR Scope 2
→ Final recommendation with full Cypher trace

---

## 2. Architecture

Three independently deployable layers:

```
[Neo4j Graph DB]  (existing, Docker)
      ↓  Bolt (7687)
[MCP Server]           — Person 1 — Python/FastMCP
      ↓  tools imported as functions
[Orchestration API]    — Person 2 — FastAPI + Mistral AI API + SSE
      ↓  HTTP/SSE
[Web Dashboard]        — Person 3 — Next.js + React + Tailwind
      ↑
[Integration + Demo]   — Person 4 — Cypher queries, data validation, pitch
```

---

## 3. MCP Server (Person 1)

**Stack:** Python, `fastmcp`
**Connection:** Neo4j Bolt at `bolt://localhost:7687`

### Tools

| Tool | Parameters | Neo4j Traversal | Returns |
|---|---|---|---|
| `get_regional_sdg_profile` | `geo_id` | GeoArea → Observation → Indicator → SDG | Scores vs 2030 targets per SDG |
| `find_peer_regions` | `geo_id, sdg_id` | Cypher-based similarity on baseline+trajectory | List of regions that improved from similar baseline |
| `get_indicator_trend` | `indicator_id, geo_id` | Observation nodes over time | Year-by-year values |
| `map_sdg_to_policy` | `sdg_id, geo_id` | SDG → PolicyFramework → EGD/CSR/NDC | Applicable policy levers with descriptions |

Each tool response includes:
- `result`: structured data
- `cypher`: the raw Cypher query executed (used for graph trace in dashboard)
- `metadata`: node IDs, relationship types traversed

---

## 4. Orchestration API (Person 2)

**Stack:** FastAPI, `mistralai` Python SDK (`mistral-large-latest` / Mistral Large 3 v25.12), SSE via `sse-starlette`
- `devstral-2512` (Devstral 2) available for code-heavy subtasks if needed

### OpenCode-Style Agent Configs

```python
AGENTS = {
  "analyst": {
    "model": "mistral-large-latest",
    "prompt": "You are the Diagnostic Analyst. Given a region and SDG, use tools to identify the most critical sustainability gap. Compare current indicator values against 2030 targets. Be precise and cite specific numbers.",
    "tools": ["get_regional_sdg_profile", "get_indicator_trend"]
  },
  "strategist": {
    "model": "mistral-large-latest",
    "prompt": "You are the Peer-Discovery Strategist. Given an SDG gap from the Analyst, find peer regions that started from a similar baseline and improved significantly. Explain what made them succeed.",
    "tools": ["find_peer_regions", "get_indicator_trend"]
  },
  "localizer": {
    "model": "mistral-large-latest",
    "prompt": "You are the Localization & Compliance Officer. Given a peer success story from the Strategist, map their successful interventions to policy frameworks applicable to the target region. Identify specific EGD articles, CSR obligations, or NDC commitments.",
    "tools": ["map_sdg_to_policy"]
  }
}
```

### Endpoint

`POST /analyze`
Body: `{ "geo_id": "EL30", "sdg_id": "SDG_7" }`
Response: SSE stream

### SSE Event Schema

```
event: agent_start    { "agent": "analyst" }
event: tool_call      { "tool": "get_regional_sdg_profile", "input": {...} }
event: tool_result    { "output": {...}, "cypher": "MATCH ..." }
event: agent_thought  { "text": "Attica scores 34% on SDG 7..." }
event: agent_done     { "agent": "analyst", "summary": "..." }
event: agent_start    { "agent": "strategist" }
... (relay continues)
event: final          { "recommendation": {...}, "traces": [...] }
event: error          { "message": "..." }
```

### Relay Logic

Analyst runs → its `summary` is appended to Strategist's context → Strategist runs → its `summary` appended to Localizer's context → Localizer runs → all summaries + traces compiled into `final` event.

---

## 5. Web Dashboard (Person 3)

**Stack:** Next.js 14, Tailwind CSS, shadcn/ui
**SSE client:** native `EventSource` API

### Layout (Single Page)

```
┌─────────────────────────────────────────────────────────┐
│  SUSTAINGRAPH INTELLIGENCE                    [dark bg] │
├──────────────┬──────────────────────┬───────────────────┤
│ INPUT        │ AGENT LIVE FEED      │ RECOMMENDATION    │
│              │                      │                   │
│ Region:      │ ● Analyst [active]   │ [locked until     │
│ [Attica ▼]  │   ↳ tool_call        │  final event]     │
│              │     get_profile      │                   │
│ SDG:         │     [Cypher shown]   │ SDG 7 Gap: -23%   │
│ [SDG 7  ▼]  │     [Result: {...}]  │                   │
│              │   ↳ thinking...      │ Peer: Jutland, DK │
│ [ANALYZE]    │                      │                   │
│              │ ● Strategist [next]  │ Policy: EGD §3.2  │
│              │ ● Localizer  [wait]  │                   │
│              │                      │ [Cypher Traces ▼] │
└──────────────┴──────────────────────┴───────────────────┘
```

### Key UI Behaviours

- Middle panel streams in real-time; tool calls are collapsible cards with syntax-highlighted Cypher
- Agent status indicators: `waiting → active → done` with color transitions
- Right panel animates in only when `final` event received
- Cypher traces section is expandable (for the technical wow moment)
- Dark theme, monospace font for tool calls and Cypher

---

## 6. Demo Scenario & Data Validation (Person 4)

**Responsibilities:**
- Write and validate all 4 Cypher queries used by MCP tools against the live graph
- Confirm the Attica × SDG 7 data path exists in Neo4j (GeoArea node `EL30`, SDG 7 indicators, Jutland node `DK05`)
- Identify fallback region/SDG pair if data is sparse
- Run end-to-end integration test before demo
- Prepare 3-slide pitch: Problem → Architecture → Live Demo

**Pre-validated Cypher queries to deliver to Person 1:**

```cypher
// Tool 1: Regional SDG profile
MATCH (ga:GeoArea {EUcode: $geo_id})-[:HAS_OBSERVATIONS]-(i:Indicator)-[:MEASURES]->(s:SDG)
MATCH (sm:SeriesMetadata)-[:HAS_OBSERVATION]->(o:Observation)-[:REFERS_TO_AREA]->(ga)
WHERE s.code = $sdg_id
RETURN i.code, i.description, o.value, o.time ORDER BY o.time DESC LIMIT 20

// Tool 2: Peer regions (baseline comparison)
MATCH (target:GeoArea {EUcode: $geo_id})-[:HAS_OBSERVATIONS]-(i:Indicator)-[:MEASURES]->(s:SDG {code: $sdg_id})
MATCH (peer:GeoArea)-[:HAS_OBSERVATIONS]-(i)
WHERE peer.EUcode <> $geo_id
WITH peer, collect(distinct i.code) as shared_indicators
WHERE size(shared_indicators) > 2
RETURN peer.name, peer.EUcode, size(shared_indicators) as overlap ORDER BY overlap DESC LIMIT 5

// Tool 3: Indicator trend
MATCH (ga:GeoArea {EUcode: $geo_id})
MATCH (sm:SeriesMetadata {seriesCode: $indicator_id})-[:HAS_OBSERVATION]->(o:Observation)-[:REFERS_TO_AREA]->(ga)
RETURN o.time, o.value ORDER BY o.time

// Tool 4: Policy mapping
MATCH (s:SDG {code: $sdg_id})--(pf:PolicyFramework)
RETURN pf.name, pf.description, pf.url LIMIT 10
```

---

## 7. Team Split

| Person | Owns | Hours |
|---|---|---|
| 1 | MCP Server + 4 Neo4j tools | 10–14h |
| 2 | FastAPI + Claude agent relay + SSE streaming | 12–16h |
| 3 | Next.js dashboard + SSE consumer + UI | 12–16h |
| 4 | Cypher validation + integration + demo script + pitch | 14–18h |

---

## 8. Cut List (explicitly out of scope)

- GDS Node Similarity algorithms (use Cypher-based comparison instead)
- Vector embeddings / PDF ingestion
- User authentication
- Multiple demo scenarios (one scenario, hardcoded)
- Mobile responsiveness
- Error recovery / retry logic in agents

---

## 9. Success Criteria

- [ ] `POST /analyze` returns a complete SSE stream end-to-end
- [ ] Dashboard shows all 3 agents with live tool call visualization
- [ ] Final recommendation references real graph data with Cypher traces
- [ ] Demo completes in under 90 seconds from click to recommendation
- [ ] Works on a local machine with Neo4j running in Docker
