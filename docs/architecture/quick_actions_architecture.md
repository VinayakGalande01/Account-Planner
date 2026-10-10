# Architecture Specification: Quick-Actions Routing Layer & Environment

This document specifies the architecture and implementation guidelines for the **Quick-Actions Environment** surrounding the core APEX reasoning engine. 

Developers must adhere to these patterns when adding new quick-actions or modifying existing transactional features (e.g., Generate Email, Create Agenda, Show Stakeholders, Review Risks).

---

## 1. Architectural Philosophy: The "Routing Shell"

To keep the core reasoning engine (`reasoning_engine.py`, `agent_pipeline.py`) clean and robust, we do not modify the core 4-phase business intelligence pipeline to handle task-based transactional actions.

Instead, we wrap the core engine in a **Routing Shell**:

```
                  ┌──────────────────────────────────────────────┐
                  │                 CLIENT (UI)                  │
                  │   Sends structured event payload with:       │
                  │   - query: "Generate Executive Email"        │
                  │   - action_type: "EXEC_EMAIL"                │
                  │   - active_account: "Acme Corp"              │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │            BACKEND API (main.py)             │
                  │   Intercepts explicit action_types before   │
                  │   any NLP / embedding classification runs.   │
                  └──────────────────────┬───────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼ (Regular NLP Chat)                      ▼ (Quick Action)
        ┌───────────────────────┐                 ┌───────────────────────┐
        │   IntentClassifier    │                 │  QuickActionRouter    │
        │  (Semantic/Symbolic)  │                 │  (Deterministic Map)  │
        └───────────┬───────────┘                 └───────────┬───────────┘
                    │                                         │
                    ▼                                         ▼
        ┌───────────────────────┐                 ┌───────────────────────┐
        │   DataRetrieval fetch │                 │   DataRetrieval fetch │
        │    (Account Context)  │                 │    (Account Context)  │
        └───────────┬───────────┘                 └───────────┬───────────┘
                    │                                         │
                    ▼                                         ▼
        ┌───────────────────────┐                 ┌───────────────────────┐
        │    Reasoning Engine   │                 │  QuickActionHandlers  │
        │   (Crucible Threads)  │                 │  (Fast-path generator │
        │                       │                 │   or local mapping)   │
        └───────────────────────┘                 └───────────┬───────────┘
                                                              │
                                                              ▼
                                                  ┌───────────────────────┐
                                                  │  Structured UI Card   │
                                                  │  (Email, Agenda, etc.)│
                                                  └───────────────────────┘
```

By placing quick-actions in this outer environment, we achieve:
1. **Zero LLM routing errors**: Explicit button clicks bypass intent classification and entity extraction.
2. **Speed & Reliability**: Handlers run either deterministic local logic (e.g., stakeholders) or narrow, single-purpose LLM calls (e.g., email draft) rather than running long, multi-persona Crucible sessions.
3. **Structured Frontend Rendering**: Responses are returned as typed JSON objects which the UI renders as premium widgets, not generic markdown bubbles.

---

## 2. Intent Map & Structured Payload Contracts

All quick-actions must define a strict JSON response schema. This allows the React frontend to render custom components dynamically depending on the response type.

### A. Executive Email Handler (`EXEC_EMAIL`)
- **Execution Strategy**: Narrow LLM call generating only subject line and body.
- **Backend Schema**:
```typescript
interface ExecEmailResponse {
  type: "EXEC_EMAIL";
  subject: string;
  body: string;
  suggested_recipients: Array<{ name: string; role: string }>;
  send_later_hint?: string;
}
```

### B. Meeting Agenda Handler (`MEETING_AGENDA`)
- **Execution Strategy**: Short LLM generation structured into timed segments, using CRM contacts.
- **Backend Schema**:
```typescript
interface MeetingAgendaResponse {
  type: "MEETING_AGENDA";
  meeting_title: string;
  audience_type: "Executive" | "Technical" | "Commercial";
  duration_minutes: number;
  agenda_items: Array<{
    order: number;
    title: string;
    duration_min: number;
    owner: string;
    talking_points: string[];
    why_this_matters: string;
  }>;
  prep_checklist: string[];
  suggested_attendees: Array<{ name: string; role: string }>;
}
```

### C. Show Stakeholders Handler (`SHOW_STAKEHOLDERS`)
- **Execution Strategy**: **100% Deterministic**. No LLM execution. Pulls database contacts directly.
- **Backend Schema**:
```typescript
interface StakeholdersResponse {
  type: "STAKEHOLDERS";
  total_count: number;
  stakeholders: Array<{
    name: string;
    role: string;
    engagement_level: "High" | "Medium" | "Low";
    sentiment: "Champion" | "Neutral" | "Detractor";
    days_since_contact: number;
    is_decision_maker: boolean;
    risk_flag: "COLD_CONTACT" | "NONE";
    suggested_action: string;
  }>;
  influence_map: {
    high_influence_champions: string[];
    high_influence_detractors: string[];
    cold_stakeholders: string[];
  };
}
```

### D. Review Risks Handler (`REVIEW_RISKS`)
- **Execution Strategy**: **100% Deterministic**. Evaluates CRM opportunities, support cases, and activities metrics to bucket risks.
- **Backend Schema**:
```typescript
interface RiskReviewResponse {
  type: "RISK_REVIEW";
  revenue_at_risk_usd: number;
  risk_buckets: {
    single_threaded: Array<{ opp_name: string; value_usd: number; suggested_action: string }>;
    stalling_deals: Array<{ opp_name: string; days_stalled: number; stage: string }>;
    critical_cases: Array<{ case_id: string; priority: string; age_days: number }>;
    competitor_threat: Array<{ opp_name: string; competitor: string; value_usd: number }>;
  };
  risk_summary: string;
}
```

---

## 3. Extension Protocol: Adding a New Quick-Action

To add a new quick-action capability (e.g., `Generate Account Playbook`):

### Step 1: Register the Action Type
- Add the uppercase identifier (e.g., `GENERATE_PLAYBOOK`) to the frontend event trigger.
- Add it to the backend `QUICK_ACTION_INTENTS` set in `agent_orchestrator.py` or the dispatcher.

### Step 2: Implement the Handler
- Create a handler class in `backend/quick_actions_handler.py` inheriting from a base interface.
- Implement the `handle(account_data, query)` method returning the correct structured dict.
- **Rule**: If the output does not require natural language prose generation (like checklists, summaries, tables), pull it deterministically from `account_data` to keep latency sub-second.

### Step 3: Add the Frontend Renderer
- Build `src/components/quick-actions/PlaybookCard.tsx` parsing the new schema.
- Map the key in `ChatMessage.tsx`:
```tsx
if (response.type === "GENERATE_PLAYBOOK") return <PlaybookCard data={response} />;
```

---

## 4. Code Isolation Rules

- **Do NOT** import `quick_actions_handler.py` inside `reasoning_engine.py` or `data_engine.py`. This avoids circular dependencies.
- **Do NOT** use multi-persona Crucible consensus loops inside quick-actions. Quick-actions are targeted and single-threaded.
- Keep all local database query helpers required for stakeholder classification inside `quick_actions_handler.py` or `data_retrieval_layer.py`.
