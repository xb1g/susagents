# SustainGraph MVP — Team Briefing

**Hackathon | 24–48 hours | Team of 4**

---

## What We're Building

A web application where you pick a region and a UN Sustainable Development Goal, then watch three AI agents reason in real-time over a knowledge graph of EU sustainability data — and produce a traceable, evidence-based policy recommendation.

**The live demo:** Select *Attica, Greece* + *SDG 7 (Clean Energy)* → watch the agents think → get "Attica should adopt offshore wind permitting reform, aligned with EGD Article 3.2, based on what Jutland, Denmark achieved from the same baseline."

Every recommendation links back to a specific Cypher query that ran against the graph. That's the wow factor: **no hallucinations, full traceability.**

---

## The Stack (brief)

```
Neo4j Knowledge Graph  ←  our data (GeoAreas, SDG indicators, policy frameworks)
       ↓
MCP Server (Python/FastMCP)  ←  Person 1
  Exposes 4 Neo4j tools as Python functions

Orchestration API (FastAPI + Mistral AI)  ←  Person 2
  3 Mistral Large agents relay in sequence
  Streams every thought + tool call as SSE

Web Dashboard (Next.js)  ←  Person 3
  Consumes SSE, shows live agent reasoning + recommendation

Data Validation + Integration  ←  Person 4
  Validates the graph data, writes Cypher, runs integration, pitches
```

---

## The Three Agents

| Agent | Role | Tools it uses |
|---|---|---|
| **Analyst** | Finds the worst SDG gap in the target region | `get_regional_sdg_profile`, `get_indicator_trend` |
| **Strategist** | Finds peer regions that solved the same gap | `find_peer_regions`, `get_indicator_trend` |
| **Localizer** | Maps the peer's success to local policy frameworks | `map_sdg_to_policy` |

They run in sequence. Each agent's summary becomes context for the next.

---

## The Four Shared Contracts

**Read these before writing any code.** They are the interfaces between the four work streams.

### 1. MCP Tool Signatures (Person 1 → Person 2)

```python
# Every tool returns this exact shape
{ "result": list | dict, "cypher": str, "metadata": dict }

get_regional_sdg_profile(geo_id: str, sdg_id: str) -> dict
find_peer_regions(geo_id: str, sdg_id: str) -> dict
get_indicator_trend(indicator_id: str, geo_id: str) -> dict
map_sdg_to_policy(sdg_id: str, geo_id: str) -> dict
```

### 2. SSE Event Schema (Person 2 → Person 3)

```typescript
// Every event has a "type" field embedded in the JSON data
{ type: "agent_start",   agent: "analyst" | "strategist" | "localizer" }
{ type: "tool_call",     tool: string, input: {...} }
{ type: "tool_result",   output: unknown, cypher: string }
{ type: "agent_thought", text: string }
{ type: "agent_done",    agent: string, summary: string }
{ type: "final",         recommendation: {...}, traces: [...] }
{ type: "error",         message: string }
```

### 3. Demo Scenario (Person 4 → everyone)

```
Region:   Attica, Greece   →  geo_id = "EL30"
SDG:      SDG 7            →  sdg_id = "SDG_7"
Fallback: Greece national  →  geo_id = "EL"
```

Person 4 validates this path exists in the graph and provides the correct Cypher to Person 1.

### 4. API Endpoint (Person 2 → Person 3)

```
POST http://localhost:8000/analyze
Body: { "geo_id": "EL30", "sdg_id": "SDG_7" }
Response: text/event-stream (SSE)

GET http://localhost:8000/health
Response: { "status": "ok" }
```

---

## Environment Setup (everyone)

1. **Clone and enter the repo**

```bash
git clone <repo-url>
cd sustaingraph
```

2. **Copy and fill `.env`**

```bash
cp .env.example .env
# Fill in:
# SUSTAINGRAPH_PASSWORD=...
# MISTRAL_API_KEY=...       ← get this from the team lead
# DATABASE_NAME=neo4j
```

3. **Start Neo4j**

```bash
docker compose up -d
# Neo4j Browser: http://localhost:7474  (user: neo4j)
```

4. **Verify Neo4j is up**

```bash
curl http://localhost:7474
# Expected: Neo4j HTML page
```

---

## Key Files

| File | Purpose |
|---|---|
| `docs/superpowers/specs/2026-02-28-sustaingraph-mvp-design.md` | Full architecture spec |
| `docs/superpowers/plans/2026-02-28-sustaingraph-mvp.md` | Detailed task plan (your source of truth) |
| `docs/team/01-person1-mcp-server.md` | Role card: MCP Server |
| `docs/team/02-person2-orchestration-api.md` | Role card: Orchestration API |
| `docs/team/03-person3-dashboard.md` | Role card: Web Dashboard |
| `docs/team/04-person4-data-integration.md` | Role card: Data & Integration |

---

## Running the Full Stack

```bash
# Terminal 1 — Neo4j (already running via docker-compose)

# Terminal 2 — Orchestration API
uvicorn orchestration_api.main:app --port 8000 --reload

# Terminal 3 — Dashboard
cd dashboard && npm run dev

# Open http://localhost:3000
```

---

## Timeline Suggestion

| Hour | Goal |
|---|---|
| 0–2 | Everyone reads this doc. Person 4 starts graph exploration. Persons 1+2 set up Python env. Person 3 scaffolds Next.js. |
| 2–8 | Core implementation. Person 1: Neo4j tools. Person 2: agent configs + SSE. Person 3: components + mock SSE. Person 4: Cypher validation. |
| 8–16 | Integration. Person 4 coordinates. Fix Cypher queries with real data. Connect dashboard to real API. |
| 16–20 | End-to-end demo test. Fix bugs. |
| 20–24 | Polish, pitch prep, rehearsal. |

---

## Communication

- If your Cypher returns 0 results → **tell Person 4 immediately**
- If the SSE contract needs to change → **tell Persons 2 and 3 together**
- If Neo4j schema doesn't match expected node labels → **tell everyone**
- Commits go to `main`. Commit often. Small commits.
