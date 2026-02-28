# Role Card: Person 3 — Web Dashboard

**You own:** The visual experience. Everything the judges see and interact with.

---

## Your Job in One Sentence

Build a dark, developer-aesthetic Next.js dashboard with 3 columns: a region/SDG picker on the left, a live agent feed in the middle that streams in real-time, and a recommendation panel on the right that appears when the analysis is complete.

---

## What You're Building

```
dashboard/
├── app/
│   ├── layout.tsx              ← dark bg, font setup
│   ├── page.tsx                ← 3-column layout
│   └── api/mock/route.ts       ← mock SSE for development (provided)
├── components/
│   ├── RegionSelector.tsx      ← dropdown: Attica, Greece / etc.
│   ├── SDGSelector.tsx         ← dropdown: SDG 7 / etc.
│   ├── AgentFeed.tsx           ← renders all 3 AgentCards
│   ├── AgentCard.tsx           ← one agent's steps (thoughts + tool calls)
│   ├── ToolCallCard.tsx        ← collapsible card: tool name + Cypher + result
│   └── Recommendation.tsx      ← final panel: gap / peer / policy + traces
├── hooks/
│   └── useSSEStream.ts         ← EventSource logic + state management
└── lib/
    ├── types.ts                ← SSE event types, Recommendation type
    └── constants.ts            ← REGIONS, SDGS, API_URL
```

---

## Getting Started

```bash
cd dashboard

# 1. Install
npm install

# 2. Create env file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 3. Run dev server
npm run dev
# Open http://localhost:3000
```

**You do NOT need Person 2 to be ready.** Use the mock SSE endpoint to develop:

```typescript
// In dashboard/lib/constants.ts, temporarily change:
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/mock"
// Switch back to "http://localhost:8000" before demo
```

The mock route at `dashboard/app/api/mock/route.ts` streams pre-canned events with 800ms delays — realistic enough to test your live streaming UI.

---

## The Layout (3 columns)

```
┌──────────────┬──────────────────────┬───────────────────┐
│ INPUT        │ AGENT LIVE FEED      │ RECOMMENDATION    │
│              │                      │                   │
│ Region:      │ ● Analyst [active]   │ [locked until     │
│ [Attica ▼]  │   ↳ tool_call        │  final event]     │
│              │     get_profile      │                   │
│ SDG:         │     [Cypher ▼]       │ Gap: -23%         │
│ [SDG 7  ▼]  │     [Result ▼]       │ Peer: Jutland, DK │
│              │                      │ Policy: EGD §3.2  │
│ [ANALYZE]    │ ● Strategist [wait]  │                   │
│              │ ● Localizer  [wait]  │ [Cypher Traces ▼] │
└──────────────┴──────────────────────┴───────────────────┘
```

**Column 1:** Region + SDG dropdowns + Analyze button (disabled while streaming)
**Column 2:** Three `AgentCard` components. Each shows: spinner/checkmark status, agent thoughts as they stream in, tool call cards (collapsible, show Cypher when expanded)
**Column 3:** Locked with a placeholder until the `final` SSE event arrives, then animates in

---

## The SSE Hook

`useSSEStream.ts` is the most important file. It:
1. Opens a `fetch` request to `POST /analyze` with the selected geo_id + sdg_id
2. Reads the response as a `ReadableStream` (standard `EventSource` doesn't support POST)
3. Parses each `data: {...}` line as a JSON object
4. Updates state based on the `type` field

```typescript
const { state, analyze } = useSSEStream()
// state.agents.analyst.status  →  "waiting" | "active" | "done"
// state.agents.analyst.steps   →  array of thoughts + tool calls
// state.recommendation         →  null until final event
// state.isStreaming             →  true while SSE is open
```

---

## SSE Events You'll Receive

These come from Person 2. Your hook handles all of them:

```typescript
{ type: "agent_start",   agent: "analyst" }           // set agent status → "active"
{ type: "agent_thought", text: "Attica scores..." }    // add thought step
{ type: "tool_call",     tool: "...", input: {...} }   // add tool_call step
{ type: "tool_result",   output: [...], cypher: "..." }// pair with previous tool_call
{ type: "agent_done",    agent: "analyst", summary: "..."}  // set status → "done"
{ type: "final",         recommendation: {...}, traces: [...] } // unlock right panel
{ type: "error",         message: "..." }              // show error state
```

---

## Component Responsibilities

### `AgentCard`
- Shows agent name + status icon (spinner when active, checkmark when done)
- Lists steps: thoughts as plain text, tool calls as `ToolCallCard` components
- Greys out when `status === "waiting"`

### `ToolCallCard`
- Shows: `tool_name(input_args)` header row
- Collapsed by default, expands on click
- Inside: Cypher query (syntax-highlighted green monospace), result JSON (truncated)

### `Recommendation`
- Shows nothing (placeholder text) until `state.recommendation` is non-null
- When it arrives: animates in with Gap / Peer / Policy sections as separate cards
- "Cypher Traces" accordion at the bottom — expandable list of all queries that ran

---

## Design Principles

- **Dark theme** — `bg-zinc-950` body, `border-zinc-800` cards
- **Monospace for code** — Cypher queries, tool names, JSON results use `font-mono`
- **Color per agent** — Analyst: `text-blue-400`, Strategist: `text-purple-400`, Localizer: `text-green-400`
- **Status colors** — waiting: `text-zinc-600`, active: `text-blue-400` + spinner, done: `text-green-400` + checkmark
- **Animate the recommendation** — use `animate-in fade-in` so it feels earned

---

## Tech Stack

```bash
# Already set up by create-next-app
# Additionally needed:
npx shadcn@latest init
npx shadcn@latest add card badge button select separator scroll-area
npm install lucide-react
```

Use `shadcn/ui` components for `Select`, `Button`, `Card`. Use `lucide-react` for icons (`Loader2`, `CheckCircle`, `Circle`, `ChevronDown`, `Zap`).

---

## Testing Your UI Without Person 2

1. Point `API_URL` to `/api/mock` in constants
2. Run `npm run dev`
3. Click Analyze — you should see all 3 agents activate sequentially with 800ms delays
4. Recommendation panel should appear after ~10 seconds

**Once Person 2 is ready:**
1. Start `uvicorn orchestration_api.main:app --port 8000 --reload` in another terminal
2. Change `API_URL` back to `http://localhost:8000`
3. Click Analyze — real Mistral agents, real Neo4j data

---

## Success Criteria

- [ ] All 3 agents show up with correct status transitions (waiting → active → done)
- [ ] Tool calls are visible and expand to show Cypher
- [ ] Recommendation panel populates at the end
- [ ] Cypher Traces section expands
- [ ] No console errors during a full run
- [ ] Demo looks impressive in a dark room on a projector

---

## Full task list

See `docs/superpowers/plans/2026-02-28-sustaingraph-mvp.md` → **Chunk 3**
