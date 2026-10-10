# APEX Query Pipeline — Technical Documentation
> **Commit-Ready Reference Document** | v2.1 | Last Updated: 2026-07-21
>
> This document explains every stage of the APEX AI query processing pipeline in detail, compares the old vs. new codebase with before/after diffs, and includes Marathi summaries in simple language so that any team member — technical or non-technical — can understand exactly what was changed and why.

---

## 📚 Table of Contents
1. [Pipeline Architecture Overview](#1-pipeline-architecture-overview)
2. [Layer 1: Intent Classification](#2-layer-1-intent-classification)
3. [Layer 2: Data Retrieval](#3-layer-2-data-retrieval)
4. [Layer 3: Reasoning Engine](#4-layer-3-reasoning-engine)
5. [Layer 4: Response Generation](#5-layer-4-response-generation)
6. [What Changed: Before vs. After (All 6 Components)](#6-what-changed-before-vs-after)
7. [New Files Created](#7-new-files-created)
8. [File-Level Summary Table](#8-file-level-summary-table)

---

## 1. Pipeline Architecture Overview

When a user types a query in the APEX chat (e.g., *"Bristol Myers Squibb account plan"* or *"generate email for Paul Brown"*), the following end-to-end pipeline executes:

```
User Query (frontend)
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    main.py — /api/chat endpoint                 │
│                                                                 │
│  1. Contact-to-Account auto-resolution (NEW)                    │
│  2. Chat History active account inheritance (NEW)               │
│  3. DB Checkpoint retrieval (zero-migration, from prev. sprint) │
│  4. Spawn streaming task                                        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│            agent_orchestrator.py — AccountPlanningAgent         │
│                                                                 │
│  LAYER 1: Intent Classification                                 │
│  LAYER 2: Data Retrieval + RAG Semantic Search                  │
│  LAYER 3: Multi-Threaded Reasoning (Crucible AI)                │
│  LAYER 4: Role-Specific Response Generation                     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
Streamed SSE response → Frontend UI renders sections
```

---

## 2. Layer 1: Intent Classification

**File:** [`intent_classifier.py`](file:///e:/Account%20Planner/backend/intent_classifier.py)

### What it does

The intent classifier reads the user's raw message and decides **what the user wants**. It works in 3 stages:

1. **Fast-path Regex Rules** — Instant pattern matching for known query types (no LLM call, < 1ms).
2. **Semantic Embedding Match** — Compares query embedding against known intent prototypes via SentenceTransformer.
3. **LLM Fallback (Gemini)** — Only used when confidence < 0.7 from the first two stages.

### Intent Types (IntentEnum)

| Enum Value | What It Routes | Example Query |
|:---|:---|:---|
| `RISK_ASSESSMENT` | Risk analysis pipeline | "What are the risks for BMS?" |
| `OPPORTUNITY_EXPANSION` | Upsell/cross-sell analysis | "Which deals can we expand?" |
| `PIPELINE_SUMMARY` | Deal listing | "Show all open deals" |
| `DRAFT_EMAIL` | Email drafting | "Generate email for Paul Brown" |
| `MEETING_AGENDA` | Agenda creation | "Create meeting agenda for Acme" |
| `SHOW_STAKEHOLDERS` | Contact map | "Who are the stakeholders at BMS?" |
| `REVIEW_RISKS` | Risk card | "Review risks for our top accounts" |
| **`CALCULATION_EXPLANATION`** *(NEW)* | Math audit | "How did you calculate $8.9M?" |

### Marathi (मराठी) — Layer 1

> **मराठी सोप्या भाषेत:**
>
> जेव्हा तुम्ही APEX मध्ये काहीतरी टाइप करता, तेव्हा `intent_classifier.py` हा फाइल सर्वात आधी चालतो. तो ठरवतो की **तुम्हाला नक्की काय हवे आहे** — email draft करायचे का? deals बघायचे का? risk check करायचे का?
>
> हे एखाद्या receptionist सारखे आहे — तुम्ही office मध्ये आलात, receptionist ऐकतो आणि म्हणतो "okay, तुम्हाला accounts department कडे पाठवतो" किंवा "तुम्हाला IT support कडे जायला हवे".

---

## 3. Layer 2: Data Retrieval

**Files:** [`agent_orchestrator.py`](file:///e:/Account%20Planner/backend/agent_orchestrator.py#L403-L487) → `DataRetrieval` class, [`data_engine.py`](file:///e:/Account%20Planner/backend/data_engine.py)

### What it does

After intent is determined, Layer 2 fetches the **actual CRM data** from the database:

1. **Account Matching** — Fuzzy name match against the accounts table.
2. **Opportunities, Contacts, Cases, Activities** — Filtered by matched `Account_ID`.
3. **RAG Semantic Search** — `vector_store.search_activities()` finds the 3 most semantically similar past activities to the current query.
4. **Intelligence Engine** — Computes stalled deals, churn risk scores, and pipeline health in real-time.
5. **Data Quality Check** — Scores CRM completeness (0.0–1.0). If < 40%, expands scope to portfolio averages.
6. **HITL Clarification Gate** — If no account was identified and the query uses planning keywords like "renewal", "churn", "competitor", it triggers a clarification prompt to the user.

### How DataEngine loads data (safe_query, NEW)

**Before (broken):**
```python
accounts = self.db.query(Account).filter(Account.user_id == self.user_id).all()
```
If Supabase dropped the TCP connection silently (after ~5 minutes idle), this would crash with:
```
psycopg2.OperationalError: server closed the connection unexpectedly
```

**After (fixed):**
```python
def safe_query(model):
    try:
        return self.db.query(model).filter(model.user_id == self.user_id).all()
    except Exception as e:
        print(f"  [WARNING] DB query failed on stale connection: {e}. Retrying once after rollback...")
        try:
            self.db.rollback()
        except Exception:
            pass
        return self.db.query(model).filter(model.user_id == self.user_id).all()

accounts = safe_query(Account)
```
Now if the connection is stale, it rolls back, reconnects, and retries **once** automatically.

### Marathi (मराठी) — Layer 2

> **मराठी सोप्या भाषेत:**
>
> Layer 1 ने ठरवले "okay, user ला Bristol Myers Squibb account plan हवे आहे." आता Layer 2 database मधून **actual data** आणतो — deals किती आहेत, contacts कोण आहेत, cases काय open आहेत.
>
> जुन्या code मध्ये एक problem होती: जर database शी connection जास्त वेळ idle राहिली (Supabase ने connection तोडली), तर program crash होत होता. आता आम्ही `safe_query` helper बनवला जो: **पहिल्यांदा try करतो → fail झालं → rollback → परत try करतो**. हे एखाद्या mobile call सारखे आहे — call drop झाला तर लगेच redial करतो!

---

## 4. Layer 3: Reasoning Engine

**File:** [`reasoning_engine.py`](file:///e:/Account%20Planner/backend/reasoning_engine.py)

### What it does

Layer 3 is the **Crucible AI engine** — it runs 4 parallel reasoning threads (AM perspective, VP perspective, SVP perspective, Data perspective) and synthesizes them into a `ConsensusOutput`.

Each thread calls:
1. `PreReasoningLayer` — Evidence selection + intelligence brief creation.
2. `DecisionFramer` — Classifies which analytical frame to use (health assessment, risk, expansion, etc.).
3. `NarrativeBuilder` — Generates causal theories and strategic narratives.
4. `ResponseGenerator` — Produces the final role-specific playbook.

### JSON Repair (NEW)

**Before (broken):** Gemini sometimes returned truncated JSON:
```python
result = json.loads(response_text)  # ← crashes if string is unterminated
```
Error:
```
[DecisionFramer Warning] LLM framing failed: Unterminated string starting at: line 4 column 16 (char 70)
```

**After (fixed):**
```python
try:
    result = json.loads(response_text)
except Exception:
    from reasoning_engine import repair_json_string
    repaired = repair_json_string(response_text)
    result = json.loads(repaired)
```
`repair_json_string()` is our own robust JSON healer that:
- Strips markdown code fences
- Adds missing closing braces `}` and brackets `]`
- Fixes unbalanced quotes
- Converts Python `None/True/False` → JSON `null/true/false`
- Removes trailing commas

### Marathi (मराठी) — Layer 3

> **मराठी सोप्या भाषेत:**
>
> Layer 3 हे APEX चे "brain" आहे. यात 4 जण parallel मध्ये विचार करतात — एक Account Manager च्या नजरेतून, एक VP च्या नजरेतून, एक SVP च्या, आणि एक pure data नजरेतून. मग सर्वांचे विचार एकत्र करून एक final answer बनतो.
>
> एक problem होती: Gemini AI कधी कधी incomplete JSON पाठवत होता (जसे sentence मध्यातच तुटली). मग program crash होत होता. आता आमचा `repair_json_string()` tool हे automatically fix करतो — तुटलेले JSON सांधून तयार करतो!

---

## 5. Layer 4: Response Generation

**File:** [`reasoning_engine.py`](file:///e:/Account%20Planner/backend/reasoning_engine.py) → `ResponseGenerator` class

### What it does

Takes the `ConsensusOutput` and generates a **role-specific formatted response**:

- **AM (Account Manager):** Tactical 7-day playbook with contact actions.
- **VP:** Strategic risk-opportunity matrix.
- **SVP:** Executive brief with financial impact and board-level recommendations.

The response is then streamed back to the frontend as SSE (Server-Sent Events) with structured sections:
```
__SECTION_HEADLINE__\n...
__SECTION_SUMMARY__\n...
__SECTION_TABLE__\n...
__SECTION_END__
```

### Marathi (मराठी) — Layer 4

> **मराठी सोप्या भाषेत:**
>
> शेवटी, तयार झालेला analysis user ला दाखवायला format केला जातो. Account Manager ला practical steps मिळतात ("या contact ला आज call करा"), VP ला risk summary मिळते, SVP ला financial figures मिळतात. हे frontend ला piece by piece streaming मध्ये पाठवले जाते — म्हणूनच response येत असताना sections एक एक दिसतात.

---

## 6. What Changed: Before vs. After

### Component 1: Supabase Connection Drop Fix

**File:** [`database.py`](file:///e:/Account%20Planner/backend/database.py)

**Before:**
```python
pool_recycle=1800,          # 30 minutes — too long, Supabase drops after ~5 min idle
connect_args={"connect_timeout": 3}
# No error handling in RLS cursor.execute()
if user_id:
    cursor.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
```

**After:**
```python
pool_recycle=300,           # 5 minutes — recycles before Supabase can drop it
connect_args={"connect_timeout": 5}
# Safe wrapper around RLS cursor.execute()
try:
    if user_id:
        cursor.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
    else:
        cursor.execute("SELECT set_config('app.current_user_id', '', true)")
except Exception as rls_err:
    print(f"  [WARNING] RLS set_config error (connection may be stale): {rls_err}")
```

**Impact:** Eliminates `psycopg2.OperationalError: server closed the connection unexpectedly` errors during and after long LLM calls.

**Marathi:**
> Supabase आमची database connection 5 मिनिटांनंतर तोडत होती, पण आमचा program 30 मिनिटांपर्यंत ती connection valid आहे असे समजत होता. आता आम्ही हे 5 मिनिटांवर आणले. त्यामुळे program नेहमी fresh connection वापरतो.

---

### Component 2: Query Classifier Timeout Fix

**File:** [`query_classifier.py`](file:///e:/Account%20Planner/backend/query_classifier.py)

**Before:**
```python
with httpx.Client(timeout=5.0) as client:   # Only 5 seconds — too short for cold start
```

**After:**
```python
with httpx.Client(timeout=12.0) as client:  # 12 seconds — covers model warm-up time
```

**Impact:** Eliminates `[CLASSIFIER ERROR] Failed to classify query: timed out` warnings.

**Marathi:**
> Query classifier एक local AI model वापरतो. Server restart झाल्यावर हा model warm-up होण्यास 8-10 सेकंद लागतात. जुन्या code मध्ये 5 सेकंदांचा timeout होता — म्हणून warm-up दरम्यान classify fail होत होते. आता 12 सेकंद दिले आहेत.

---

### Component 3: `str` Object Has No Attribute `dict` Fix

**Files:** [`agent_orchestrator.py`](file:///e:/Account%20Planner/backend/agent_orchestrator.py#L294-L301), [`main.py`](file:///e:/Account%20Planner/backend/main.py#L1391)

**Before:**
```python
# blindly calls .dict() without checking if object supports it
entities = intent.extracted_entities.model_dump() if hasattr(intent.extracted_entities, "model_dump") \
           else intent.extracted_entities.dict()   # ← crashes if extracted_entities is a str
```

**After:**
```python
entities = (
    intent.extracted_entities.model_dump() if hasattr(intent.extracted_entities, "model_dump") else
    intent.extracted_entities.dict() if hasattr(intent.extracted_entities, "dict") else
    intent.extracted_entities if isinstance(intent.extracted_entities, dict) else
    {}
)
```

**Impact:** Fixes the `Processing Error: 'str' object has no attribute 'dict'` crash shown in the screenshot when typing *"generate email for paul brown"*.

**Marathi:**
> जेव्हा session checkpoint resume होत होता, तेव्हा `intent` object एक string म्हणून load होत होता. Program त्यावर `.dict()` call करत होता — पण string ला `.dict()` नाही असतो! त्यामुळे crash होत होता. आता आम्ही पहिल्यांदा check करतो: "हे Pydantic object आहे का, plain dict आहे का, किंवा string आहे का?" आणि त्यानुसार handle करतो.

---

### Component 4: LLM JSON Repair

**Files:** [`decision_framer.py`](file:///e:/Account%20Planner/backend/decision_framer.py), [`narrative_builder.py`](file:///e:/Account%20Planner/backend/narrative_builder.py)

**Before:**
```python
result = json.loads(response_text)   # Single attempt — crashes on malformed JSON
```

**After:**
```python
try:
    result = json.loads(response_text)
except Exception:
    from reasoning_engine import repair_json_string
    repaired = repair_json_string(response_text)
    result = json.loads(repaired)
```

**Impact:** Prevents LLM framing cascade failures when Gemini returns unterminated strings.

**Marathi:**
> Gemini AI कधी कधी अर्धवट JSON पाठवतो. जुन्या code मध्ये हे directly parse करण्याचा प्रयत्न होत होता — fail होत होते. आता आमचा `repair_json_string()` function ते fix करतो — missing `}` `]` add करतो, quotes fix करतो — आणि मग parse करतो.

---

### Component 5: Calculation Transparency

**Files:** [`intent_classifier.py`](file:///e:/Account%20Planner/backend/intent_classifier.py), [`calculation_auditor.py`](file:///e:/Account%20Planner/backend/calculation_auditor.py) *(NEW)*, [`agent_orchestrator.py`](file:///e:/Account%20Planner/backend/agent_orchestrator.py#L501-L524)

**Before:** Math questions like *"How did you calculate $8.9M?"* were routed to generic ACCOUNT_PLAN — no breakdown shown.

**After:** Fast-path regex catches calculation queries → `CalculationAuditor.audit_account_metrics()` returns:

| Stalled Deal | Stage | Amount | Reason |
|:---|:---|:---|:---|
| ACC029 - Payroll Management | Demo Scheduled | **$4,169,000** | Stalled >30 days |
| ACC029 - Backup & Disaster Recovery | Solution Design | **$3,034,000** | Stalled >30 days |
| ACC029 - Mobile App Development | Prospecting | **$1,698,000** | Stalled >30 days |
| **TOTAL** | | **$8,901,000** | |

**Marathi:**
> आधी user ने "$8.9M कसे calculate केले?" विचारले तर APEX एक generic table दाखवत होता. आता `CalculationAuditor` सांगतो: "Payroll $4.1M + Backup $3M + Mobile $1.7M = $8.9M — हे 3 deals 30+ दिवस inactive आहेत म्हणून stalled म्हटले." पूर्ण transparency!

---

### Component 6: Email Draft — Contact-to-Account Resolution

**File:** [`main.py`](file:///e:/Account%20Planner/backend/main.py#L1593-L1628)

**Before:** Typing *"generate email for Paul Brown"* crashed with `'str' object has no attribute 'dict'` — email never drafted.

**After:** Two resolution layers auto-detect the account:

```python
# Layer A: Contact name lookup in CRM contacts table
for idx, row in contacts_df.iterrows():
    full_name = f"{row['First_Name']} {row['Last_Name']}".strip().lower()
    if full_name in query_lower:
        acc_match = accounts_df[accounts_df['Account_ID'] == row['Account_ID']]
        if not acc_match.empty:
            resolved_active_account = acc_match.iloc[0]['Account_Name']
            # "paul brown" → Account_ID=ACC029 → "Bristol Myers Squibb"

# Layer B: Chat history account inheritance
if not resolved_active_account and chat_history:
    for h_msg in reversed(chat_history):
        for acc_name in accounts_df['Account_Name'].tolist():
            if acc_name.lower() in h_msg.get("text", "").lower():
                resolved_active_account = acc_name
```

**Impact:** APEX auto-resolves "Paul Brown" → Bristol Myers Squibb and drafts the executive email immediately.

**Marathi:**
> Problem: User "generate email for Paul Brown" टाइप केला. "Paul Brown" हा account नाही — contact आहे. त्यामुळे system confused झाला आणि crash झाला.
>
> Fix: आता system पहिल्यांदा CRM contacts table मध्ये "Paul Brown" शोधतो → त्याचा `Account_ID` मिळवतो → Account Name: "Bristol Myers Squibb" → email draft सुरु! जर contact मिळाला नाही, तर मागील chat मध्ये कोणता account discuss केला ते पाहतो.

---

## 7. New Files Created

### [`calculation_auditor.py`](file:///e:/Account%20Planner/backend/calculation_auditor.py)

**Purpose:** Mathematical transparency engine. Generates step-by-step audits of all financial figures shown to users.

**Key API:**
```python
class CalculationAuditor:
    @staticmethod
    def audit_account_metrics(account_data: Dict[str, Any], query: str = "") -> Dict[str, Any]:
        # Returns: total_db_sum, active_sum, stalled_sum, itemized_deals, audit_narrative
```

**Marathi:**
> `calculation_auditor.py` हा नवीन file. याचे काम: कोणत्याही figure साठी step-by-step math दाखवणे. Database मधील सर्व deals list करतो, stalled कोणते ते identify करतो, dead/lost कुठले exclude केले ते explain करतो — सगळे markdown table format मध्ये.

---

## 8. File-Level Summary Table

| File | Action | What Changed | Why |
|:---|:---:|:---|:---|
| [`database.py`](file:///e:/Account%20Planner/backend/database.py) | MODIFIED | `pool_recycle` 1800s → 300s; RLS cursor try-except | Supabase drops idle connections after ~5 mins |
| [`data_engine.py`](file:///e:/Account%20Planner/backend/data_engine.py) | MODIFIED | `safe_query()` retry wrapper for all 5 table queries | Rollback and retry on stale connection errors |
| [`query_classifier.py`](file:///e:/Account%20Planner/backend/query_classifier.py) | MODIFIED | Timeout 5.0s → 12.0s | Covers LLM model warm-up time on cold start |
| [`intent_classifier.py`](file:///e:/Account%20Planner/backend/intent_classifier.py) | MODIFIED | Added `CALCULATION_EXPLANATION` enum + regex fast-path | Route math questions to CalculationAuditor |
| [`agent_orchestrator.py`](file:///e:/Account%20Planner/backend/agent_orchestrator.py) | MODIFIED | CALC fast-path; safe `.dict()` wrappers; fixed import | Crash fixes + calculation routing |
| [`main.py`](file:///e:/Account%20Planner/backend/main.py) | MODIFIED | Contact name resolver; history account inheritance; safe entities | Email drafting context auto-resolution |
| [`decision_framer.py`](file:///e:/Account%20Planner/backend/decision_framer.py) | MODIFIED | `json.loads()` → try/except with `repair_json_string()` | Handle Gemini unterminated JSON strings |
| [`narrative_builder.py`](file:///e:/Account%20Planner/backend/narrative_builder.py) | MODIFIED | Same JSON repair pattern (2 locations) | Same as above |
| [`calculation_auditor.py`](file:///e:/Account%20Planner/backend/calculation_auditor.py) | **NEW** | `CalculationAuditor` class with `audit_account_metrics()` | Math transparency — itemized deal breakdowns |

---

## 9. Git Commit Message

```
fix(pipeline): resolve 6 production bugs and add math transparency

- Fix Supabase idle connection drops (pool_recycle 1800s → 300s, RLS safe cursor)
- Add safe_query retry wrapper for all DataEngine DB queries
- Fix query classifier timeout (5s → 12s) to cover LLM warm-up
- Fix 'str' object has no attribute 'dict' in all serialization paths
- Add repair_json_string() fallback in DecisionFramer and NarrativeBuilder
- Add CALCULATION_EXPLANATION intent with CalculationAuditor math audit engine
- Add contact-name-to-account and chat-history account auto-resolution in /api/chat
- Create calculation_auditor.py for step-by-step $8.9M/$18.6M breakdown transparency
```

---

*Document prepared by APEX Engineering | Session `4a557cca-cf42-4286-82be-e5c211500262`*
