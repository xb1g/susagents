# Masterplan: SustainGraph Agentic Intelligence Ecosystem (SGAIE)

## 1. Vision Statement
To transform the **SustainGraph** Knowledge Graph into an autonomous, proactive "Policy Brain" that enables AI Agents to diagnose sustainability gaps, identify successful peer-region strategies, and recommend localized, actionable policy interventions to achieve the UN Sustainable Development Goals (SDGs) by 2030.

---

## 2. Core Objectives
*   **Contextual Reasoning:** Enable AI Agents to understand the "why" behind regional sustainability performance by traversing the graph's interlinkages.
*   **Evidence-Based Recommendations:** Use Graph Data Science (GDS) to find "Peer Success Stories"—regions that shared similar constraints but achieved superior SDG outcomes.
*   **Policy-to-Action Mapping:** Close the loop between abstract global targets (SDGs) and local legislative frameworks (Ministries, EGD, CSR).
*   **Modular Intelligence:** Build an extensible MCP (Model Context Protocol) architecture so any LLM (GPT-4, Gemini, Claude) can "plug into" the SustainGraph as its primary source of truth.

---

## 3. The "Why" (The Value Proposition)
Sustainability data is currently **siloed** (spread across Eurostat, UN, and local PDFs) and **static** (reporting what happened, not what to do). 
By building an agentic layer on top of SustainGraph, we create:
1.  **Hyper-Localization:** Recommendations tailored to specific NUTS-3 regions or postal codes.
2.  **Synergy Discovery:** Identifying how an intervention in one SDG (e.g., SDG 7: Energy) might boost another (e.g., SDG 8: Decent Work).
3.  **Transparency:** Every recommendation is "traceable" back to a specific node and relationship in the graph, preventing AI hallucinations.

---

## 4. Technical Architecture

### Layer 1: The Knowledge Core (Neo4j + GDS)
*   **Source Data:** SustainGraph's existing `GeoArea`, `Indicator`, `Observation`, and `PolicyFramework` nodes.
*   **GDS Plugin:** Used for **Node Similarity** (finding peer regions) and **Centrality** (identifying "linchpin" indicators that impact the most SDGs).
*   **Vector Indexing:** Storing embeddings of policy documents (CSR reports, EGD directives) directly within Neo4j to enable Hybrid Search (Structured + Unstructured).

### Layer 2: The Interface Layer (MCP Server)
*   **Protocol:** Model Context Protocol (MCP).
*   **Function:** Exposes Cypher queries as "Tools" for AI Agents.
    *   *Tool: `get_regional_profile(geo_id)`*
    *   *Tool: `find_peer_success_cases(geo_id, target_sdg)`*
    *   *Tool: `map_sdg_to_ministry(sdg_id)`*

### Layer 3: The Agentic Brain (Orchestration)
*   **Framework:** LangChain or CrewAI.
*   **Strategy:** Multi-Agent Orchestration (see Section 5).

---

## 5. Agent Roles & Orchestration Logic

To provide a "Localized Strategy Recommendation," three specialized agents work in a relay:

### Agent A: The Diagnostic Analyst
*   **Goal:** Identify the most critical "Sustain-Gap."
*   **Process:** Queries `Observation` nodes for a `GeoArea`. Compares current trends against 2030 targets.
*   **Output:** A prioritized list of underperforming SDGs for a specific region.

### Agent B: The Peer-Discovery Strategist
*   **Goal:** Find "What worked elsewhere."
*   **Process:** Uses the `find_peer_success_cases` tool. Identifies regions with similar baseline profiles that improved their scores.
*   **Output:** A list of `Intervention` and `Transformation` nodes linked to those success stories.

### Agent C: The Localization & Compliance Officer
*   **Goal:** Ensure recommendations are viable.
*   **Process:** Cross-references identified interventions with the local `Ministry` and `PolicyFramework` nodes (e.g., "Is this intervention supported by the European Green Deal?").
*   **Output:** A final "Strategic Roadmap" including steps, responsible entities, and expected impact.

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
*   Deploy Neo4j with APOC and GDS plugins (Current status: Ready).
*   Implement **Text-to-Cypher** pipeline to allow agents to "speak" to the graph without hardcoded queries.
*   Build the initial **MCP Server** to expose the graph schema to the LLM.

### Phase 2: Intelligence Layer (Weeks 5-8)
*   Run GDS similarity algorithms to create a "Similarity Matrix" between all NUTS regions in the graph.
*   Ingest and embed unstructured policy PDFs (EGD/CSR) into the graph using Neo4j Vector Search.
*   Define the "SDG Weighting" logic (Enables/Reinforces/Targets) as agent prompts.

### Phase 3: Agent Orchestration (Weeks 9-12)
*   Develop the multi-agent relay (Analyst -> Strategist -> Localizer).
*   Build a **Human-in-the-Loop** dashboard where planners can review agent-generated strategies.
*   Conduct "Validation Runs" comparing agent recommendations against historical successful policy shifts in the graph.

---

## 7. Success Metrics (KPIs)
*   **Recommendation Accuracy:** Percentage of agent-suggested interventions that align with verified historical success cases.
*   **Traceability Score:** 100% of recommendations must include a "Cypher Trace" (the specific path in the graph that generated the advice).
*   **Cross-SDG Impact:** Measuring how many "secondary benefits" (synergies) the agent identifies per recommendation.

---

## 8. How to Use This for AI Agents
To start utilizing this project immediately for agents, point your agent framework (e.g., LangChain) to the Neo4j Bolt port and initialize the system with the following prompt:
> "You are the SustainGraph Intelligence Agent. You have access to a Knowledge Graph of UN SDGs, regional indicators, and policy interventions. Your goal is to help regions transition to sustainability by identifying peers who have already succeeded and mapping their actions to local frameworks."
