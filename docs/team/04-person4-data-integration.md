# Role Card: Person 4 — Data Validation & Integration

**You own:** Making sure the demo actually works with real data — and delivering the pitch.

---

## Your Job in One Sentence

Explore the live Neo4j graph, validate that the Attica × SDG 7 data path exists, write the definitive Cypher queries for Person 1, coordinate integration between all four streams, and deliver a tight 2-minute pitch.

---

## Why Your Role Is Critical

The agents are only as good as the data they find. If the Cypher queries return 0 results — or return the wrong data — the demo fails silently. You are the ground truth for what's actually in the graph.

You don't need to write Python or JavaScript. Your deliverables are:
1. Validated Cypher queries
2. Confirmed `geo_id` and series code formats
3. A working end-to-end demo
4. A 2-minute pitch

---

## Getting Started — Explore the Graph

Open Neo4j Browser at `http://localhost:7474` (user: `neo4j`, password from `.env`).

Run these discovery queries **in order**. Document what you find.

```cypher
-- 1. What node labels exist?
CALL db.labels()

-- 2. What relationship types exist?
CALL db.relationshipTypes()

-- 3. Find GeoArea for Attica
MATCH (ga:GeoArea)
WHERE ga.name CONTAINS "Attica" OR ga.EUcode = "EL30" OR ga.ISOalpha3code = "EL30"
RETURN ga LIMIT 5

-- 4. What properties does GeoArea have?
MATCH (ga:GeoArea) RETURN keys(ga) LIMIT 3

-- 5. Find observations for Attica (any indicator)
MATCH (ga:GeoArea)
WHERE ga.name CONTAINS "Attica" OR ga.EUcode = "EL30"
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)
RETURN ga.name, ga.EUcode, count(o) AS observation_count

-- 6. What do Series codes look like?
MATCH (s:Series) RETURN s.code LIMIT 20
-- Look for patterns like "sdg_07_40" or "SDG7_40" etc.

-- 7. Find Series codes related to SDG 7
MATCH (s:Series)
WHERE toLower(s.code) CONTAINS 'sdg' AND (s.code CONTAINS '07' OR s.code CONTAINS '_7')
RETURN s.code, s.description LIMIT 20

-- 8. What do SDG nodes look like?
MATCH (s:SDG) RETURN s LIMIT 5

-- 9. How do PolicyFramework nodes look?
MATCH (pf:PolicyFramework) RETURN pf.name, pf.description LIMIT 10

-- 10. Is there a path from SDG to PolicyFramework?
MATCH (s:SDG)-[r*1..3]-(pf:PolicyFramework)
RETURN type(r[0]), s.code, pf.name LIMIT 5
```

---

## Your Key Deliverables for Person 1

After exploring, answer these questions and send to Person 1:

### 1. What is the correct `geo_id` for Attica?

```
Expected: EL30
Check: does MATCH (ga:GeoArea {EUcode: "EL30"}) RETURN ga work?
If not, try: MATCH (ga:GeoArea) WHERE ga.name CONTAINS "Attica" RETURN ga.EUcode, ga.ISOalpha3code
```

### 2. What is the SDG 7 series code prefix?

```
Expected: "sdg_07" (zero-padded, underscore)
Check: MATCH (s:Series) WHERE s.code STARTS WITH "sdg_07" RETURN s.code LIMIT 5
```

### 3. Does the Attica → SDG 7 data path exist?

```cypher
MATCH (ga:GeoArea)
WHERE ga.EUcode = "EL30" OR ga.name CONTAINS "Attica"
MATCH (ga)<-[:REFERS_TO_AREA]-(o:Observation)<-[:HAS_OBSERVATION]-(sm:SeriesMetadata)
WHERE sm.seriesCode STARTS WITH "sdg_07"
RETURN ga.name, sm.seriesCode, count(o) AS obs_count
```
If this returns 0 rows → use fallback `geo_id = "EL"` (Greece national level).

### 4. What is the PolicyFramework → SDG relationship?

```cypher
MATCH (pf:PolicyFramework)-[r]-(s:SDG)
RETURN type(r), pf.name, s.code LIMIT 10
-- or try:
MATCH (pf:PolicyFramework) RETURN pf.name, labels(pf) LIMIT 10
```

---

## Run the Validation Script

Once Person 1 has created `scripts/validate_demo_data.py`:

```bash
python scripts/validate_demo_data.py
```

Expected output:
```
✅ GeoArea EL30: 1 records
✅ Observations for EL30: 3 records
✅ SDG 7 indicators: 5 records
✅ PolicyFrameworks: 5 records
✅ Peer regions with shared indicators: 5 records
```

If anything shows ❌, investigate in Neo4j Browser and update Person 1's Cypher.

---

## Write the Definitive Cypher Queries

Save validated queries to `cypher_queries/`. These become the source of truth for Person 1's tools.

```bash
# Create the directory
mkdir -p cypher_queries
```

Format for each file:
```cypher
-- cypher_queries/01_regional_profile.cypher
-- Tool: get_regional_sdg_profile(geo_id="EL30", sdg_id="SDG_7")
-- Validated: [date] against graph v2.0.0

MATCH (ga:GeoArea)
WHERE ga.EUcode = $geo_id
...
```

---

## Integration Coordinator Role

You are the integration glue. At the 8-hour mark, pull all streams together:

**Checklist:**
- [ ] Person 1's tools return real data for `EL30` / `SDG_7`
- [ ] Person 2's `/analyze` endpoint streams events (test with `curl -N`)
- [ ] Person 3's dashboard renders the stream (open `http://localhost:3000`)
- [ ] The full flow completes end-to-end without errors
- [ ] Demo takes under 90 seconds from click to recommendation

**When something breaks:**
- 0 results from a tool → check Cypher with Person 1
- SSE events not appearing in dashboard → check CORS and `NEXT_PUBLIC_API_URL`
- Agent errors (Mistral API) → check `MISTRAL_API_KEY` in `.env`
- Neo4j connection refused → `docker compose up -d`

---

## The Pitch (2 minutes)

**Slide 1 — Problem (30 seconds)**

> "EU sustainability data is siloed. A policy planner in Attica can't see that Denmark solved their exact problem 7 years ago. They're working blind. We built SustainGraph to fix that."

**Slide 2 — Architecture (30 seconds)**

> "SustainGraph is a Neo4j knowledge graph of 17 SDGs, 200+ EU indicators, and all major policy frameworks — EGD, CSR, NDC. We built an MCP server that exposes this as AI tools, and a 3-agent Mistral Large relay: Diagnostic Analyst → Peer Strategist → Policy Localizer. Every recommendation is traced back to a specific Cypher query."

**[Switch to browser]**

**Slide 3 — Live Demo (60 seconds)**

> "Attica, Greece. SDG 7. Watch."

*Click Analyze. Let the agents speak. Don't narrate — let the UI do it.*

When `final` appears:
> "The graph found this. Not a language model guess. A graph traversal."

---

## Timeline

| Hour | Your action |
|---|---|
| 0–1 | Run all discovery Cypher queries. Document `geo_id`, series code format, PolicyFramework relationship. |
| 1–3 | Share findings with Person 1. Write `cypher_queries/` files. |
| 3–6 | Run validation script. Fix any ❌ findings with Person 1. |
| 8 | Integration check: pull all 3 streams together. |
| 12 | Full end-to-end run. Identify and fix any bugs. |
| 16 | Rehearse pitch. Time it. |
| 20+ | Final polish, backup demo (screen recording), pitch deck. |

---

## Full task list

See `docs/superpowers/plans/2026-02-28-sustaingraph-mvp.md` → **Chunk 4**
