# APEX — Layer 2: Evaluation Platform & Continuous Quality Framework
## Engineering Handbook

---

## SECTION J — Document Metadata

| Field | Value |
|---|---|
| **Document Name** | APEX Layer 2: Evaluation Platform & Continuous Quality Framework Engineering Handbook |
| **Document Version** | 1.0.0 |
| **Layer** | Layer 2 — Continuous Quality & Evaluation |
| **Owner** | Platform Engineering (Founding Team) |
| **Status** | Active — MVP Architecture |
| **Created** | July 2026 |
| **Last Updated** | July 2026 |
| **Review Cycle** | Quarterly, or upon any major architectural change |
| **Replaces** | `Apex_Evaluation_Platform_Architecture.md` (draft) |

### Dependencies

| Dependency | Description |
|---|---|
| Layer 1 — Observability | Provides `observability_traces`, `observability_spans`, `observability_payloads`, and `observability_business_metrics` as the primary telemetry data source for all evaluation activity. |
| APEX Production Pipeline | The 4-phase pipeline (Planner → Retriever → Reasoner → Narrator) whose outputs Layer 2 evaluates. |
| PostgreSQL | Single database instance hosting both Layer 1 and Layer 2 tables. |
| FastAPI (production backend) | Provides existing auth, tenant isolation (Row-Level Security), and database session management that Layer 2 reuses. |

### Related Documents

| Document | Purpose |
|---|---|
| `Apex_architectural_review_10_July.md` | Layer 1 — Dynamic Skill Architecture Design Review |
| `Apex_Evaluation_Platform_Architecture.md` | Original draft (superseded by this handbook) |
| `Launch_readiness.md` | Production launch readiness checklist |
| `README.md` | Project overview and local setup guide |

### Target Audience

| Audience | Usage |
|---|---|
| **Founding Engineers** | Primary implementors. Use as implementation specification. |
| **AI / Prompt Engineers** | Reference for benchmark design, prompt evaluation workflow, and grounding metrics. |
| **Backend Engineers** | Reference for database schema, FastAPI routes, and background job design. |
| **Future Contributors** | Onboarding reference explaining every architectural decision and its rationale. |
| **Product Stakeholders** | Executive summary (Section A) and Business Impact Score (Section 13.5) provide non-technical context. |

> [!IMPORTANT]
> This document is the **authoritative engineering reference** for Layer 2. Any implementation decision that deviates from this specification must be documented as an Architecture Decision Record (see Section D) before code is written.

---

## SECTION A — Vision

### Why Layer 2 Exists

APEX is an AI platform that generates sales intelligence, account plans, and strategic recommendations for enterprise sales teams. Every day, it produces hundreds of AI responses that influence how sales representatives prioritize accounts, engage stakeholders, and close deals.

Layer 1 (Observability) answers a necessary question: *"What happened?"* It records every trace, every span, every token, every grounding score. It creates a complete audit trail of the pipeline's behavior.

But knowing what happened is not the same as knowing whether it was good.

A trace record showing `grounding_score: HIGH` and `reasoning_confidence_pct: 82` tells you the system executed correctly. It does not tell you whether the recommendation was strategically sound, whether a sales rep acted on it, or whether it contributed to a deal progressing.

**Layer 2 exists to answer the harder question: "Was it better?"**

It is the difference between measuring that a heart monitor is functioning and measuring whether the patient is recovering.

### Why Evaluation Is Essential for AI Products

Traditional software ships with a specification. If the code produces the specified output, it is correct. The specification does not change between releases. Regression is binary: it either broke or it did not.

AI products do not work this way.

In an AI system, the "specification" is a statistical distribution over plausible outputs. There is no single correct answer to "what is the account strategy for Wipro given this data?" There are better and worse answers, and the boundary between them is human judgment informed by business context.

This creates a fundamental engineering problem: **how do you know if a change made the AI better?**

Without a structured evaluation layer, the answer is "gut feeling, user complaints, and production monitoring." This is not engineering. It is reactive maintenance.

Layer 2 converts that gut feeling into a measurable, reproducible, auditable system. Every prompt change, every model upgrade, every retrieval improvement must pass through the evaluation layer before it reaches users. The evaluation layer is what separates an AI product from an AI experiment.

### Why Layer 1 Alone Is Insufficient

Layer 1 is a perfect mirror of what happened. It records everything with fidelity. But it is structurally incapable of answering evaluative questions because it contains no ground truth, no expected outputs, no comparison baselines, and no quality judgments.

Consider three scenarios:

**Scenario 1**: A new Narrator prompt reduces average response length by 30%. Layer 1 records this. Is it better or worse? Layer 1 cannot say. Layer 2 can — because it compares narrative structure scores, human satisfaction ratings, and recommendation actionability scores between the old and new prompt against the Golden Dataset.

**Scenario 2**: A model upgrade improves grounding scores from 88% HIGH to 93% HIGH. Layer 1 records this. But did it also increase hallucination of specific deal amounts? Layer 1 cannot say. Layer 2 can — because it runs the grounding benchmark against golden test cases with known retrieval sets and detects claim-level accuracy changes.

**Scenario 3**: Production failure — a user query about a Wipro stakeholder returns a response about a different account's contacts. Layer 1 records the failure trace. Who is responsible for preventing this from happening again? Layer 1 cannot say. Layer 2 can — because it promotes this failure to the Failure Database, assigns an owner, identifies the root cause (PLANNER or RETRIEVER), creates a golden test case, and adds it to the regression suite.

Layer 1 is the instrument. Layer 2 is the laboratory that makes the instrument's readings meaningful.

### Why Evaluation Is One of APEX's Competitive Advantages

Most AI startup teams build and ship. They improve the AI by instinct, by user feedback, and by noticing obvious failures in production. This is fast in the short term and catastrophically expensive in the long term — because regressions accumulate invisibly, quality becomes impossible to communicate to customers, and every model upgrade becomes a gamble.

Enterprise customers do not buy AI products on faith. They buy AI products that can answer:

- "How do I know this is accurate?"
- "What happens when it makes a mistake?"
- "If I upgrade the model, will it get better or worse?"
- "Can you prove this improved my team's productivity?"

Most AI startups cannot answer these questions. APEX can — because Layer 2 makes every quality claim measurable, every improvement verifiable, and every business impact traceable.

The Business Impact Score (BIS) is particularly differentiated. It does not measure whether APEX is technically correct. It measures whether APEX created commercial value. A recommendation that is technically perfect but commercially ignored scores LOW. A recommendation that leads to a deal stage advancing scores VERY HIGH. This distinction — between AI accuracy and AI value — is what enterprise buyers are actually trying to purchase.

**The philosophy of Layer 2 is three words: Simple. Scalable. Measurable.**

Simple today: a Golden Dataset, a benchmark runner, a failure database, and a release gate. Simple enough that two founders can operate it without MLOps infrastructure.

Scalable tomorrow: nightly evaluation, canary releases, prompt registries, and multi-agent evaluation. The architecture is designed to grow into these capabilities without reconstruction.

Measurable forever: every quality claim has a number behind it. Every improvement has a before and after. Every release has a gate. Every business outcome has a score. Nothing is anecdotal.

---

## SECTION B — Layer Interaction

### APEX Layer Architecture

APEX is organized as a stack of independent, composable layers. Each layer has a defined responsibility, a clear interface to adjacent layers, and explicit boundaries about what it does not own.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0 — KERNEL                                               │
│  Core AI Pipeline: Planner → Retriever → Reasoner → Narrator   │
│  reasoning_engine.py · agent_pipeline.py · intent_classifier.py│
└────────────────────────────┬────────────────────────────────────┘
                             │ Execution telemetry (trace, spans, payload)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — OBSERVABILITY                                        │
│  What happened?                                                 │
│  observability/recorder.py · ObservabilityTrace                 │
│  ObservabilitySpan · ObservabilityPayload                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ Telemetry consumed as read-only data source
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — EVALUATION  ◄── THIS DOCUMENT                       │
│  Was it better?                                                 │
│  Golden Dataset · Benchmark Runner · BIS Engine                 │
│  Failure Database · Human Review · Release Gate                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ Quality signals fed into
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — MEMORY (Future)                                      │
│  What should be remembered?                                     │
│  User preferences · Account history · Session continuity        │
└────────────────────────────┬────────────────────────────────────┘
                             │ Memory quality evaluated by Layer 2
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 — SKILLS (Future)                                      │
│  What capabilities are available?                               │
│  Dynamic skill registry · Context assembly modules              │
└────────────────────────────┬────────────────────────────────────┘
                             │ Skill selection accuracy evaluated by Layer 2
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — REFLECTION (Future)                                  │
│  Did the output need correction?                                │
│  Validation · Self-correction · Retry logic                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ Reflection trigger rate evaluated by Layer 2
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6 — REGISTRY (Future)                                    │
│  What versions are in use?                                      │
│  Prompt registry · Model registry · Skill registry              │
└────────────────────────────┬────────────────────────────────────┘
                             │ Registry versions linked to benchmark runs
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 7 — DEPLOYMENT                                           │
│  Is this safe to release?                                       │
│  CI/CD · Release gates · Production monitoring                  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 2 Interfaces

#### Interface with Layer 0 (Kernel)

Layer 2 does **not** call the Kernel directly during normal evaluation. The relationship is indirect:

- During **benchmark runs**, Layer 2 invokes the Kernel via the same API endpoints that production uses, passing golden test case queries as inputs. This is an isolated, non-production invocation.
- During **production evaluation**, Layer 2 reads Layer 1 telemetry that was produced by Kernel executions. It never inspects Kernel internals.
- Layer 2 **writes benchmark results back to its own tables** (`eval_benchmark_results`). It never writes to Kernel state.

**What Layer 2 reads from Layer 0**: nothing directly. All Kernel outputs are mediated by Layer 1.

**What Layer 2 never does**: modify Kernel prompts, modify Kernel routing logic, modify reasoning engine state, or inject evaluation logic into production request paths.

#### Interface with Layer 1 (Observability)

This is Layer 2's primary data source. The interface is **read-only** from Layer 2's perspective.

Layer 2 reads from:
- `observability_traces` — for latency, token counts, cost, confidence scores, grounding scores
- `observability_spans` — for per-phase latency (Planner / Retriever / Reasoner / Narrator)
- `observability_payloads` — for prompt hashes, retrieved context summaries, reasoning packages
- `observability_prompts` — for prompt content referenced by hash
- `observability_business_metrics` — for raw business signal events (EMAIL_SENT, REPORT_DOWNLOADED, etc.)

Layer 2 **writes back one field** to Layer 1: the `bis_record_id` foreign key on `observability_traces`, linking a trace to its Business Impact Score record. This is the only write Layer 2 performs on a Layer 1 table, and it is additive — it never modifies existing Layer 1 data.

Layer 2 **never** modifies: trace content, span durations, payload content, prompt hashes, or business metric records.

#### Interface with Layer 3 (Memory — Future)

When the Memory layer is implemented:

- Layer 2 will evaluate **memory retrieval quality**: did the correct memories surface for the query?
- Layer 2 will evaluate **memory contamination**: did stale or irrelevant memories degrade response quality?
- Layer 2 will track **memory-assisted vs. memory-unaided benchmark scores** to quantify memory value.
- The Memory layer does **not** provide Layer 2 with any data. The interface is one-directional: Layer 2 evaluates Memory outputs by reading Layer 1 telemetry that includes memory context.

#### Interface with Layer 4 (Skills — Future)

When the Skills layer is implemented:

- Layer 2 will extend the Golden Dataset to include `expected_skills_activated` — the expected set of skills for a given query.
- Layer 2 will add a **Skill Selection Accuracy** metric to the benchmark suite.
- Layer 2 will evaluate **inter-skill consistency**: when multiple skills are activated simultaneously, do their instructions produce coherent outputs?
- The Skills layer does **not** drive Layer 2. Layer 2 evaluates skills as a downstream observer.

#### Interface with Layer 5 (Reflection — Future)

When the Reflection layer is implemented:

- Layer 2 will track the **reflection trigger rate** — what percentage of requests required self-correction.
- Layer 2 will evaluate whether reflection **improved** the output (pre-reflection score vs. post-reflection score).
- Layer 2 will flag cases where reflection was triggered but failed to improve quality — these become golden test cases for reflection failure analysis.

#### Interface with Layer 6 (Registry — Future)

When a Prompt or Skill Registry is implemented:

- Layer 2 will link every benchmark run to the exact registry version in use.
- Layer 2 will use registry version identifiers as benchmark metadata, replacing git SHA references for prompt tracking.
- The Registry will provide Layer 2 with the canonical mapping of `prompt_name → version → hash`, enabling named comparisons ("compare Narrator v3 vs. Narrator v4") rather than hash-based comparisons.

#### Interface with Layer 7 (Deployment)

This is Layer 2's most active interface in the MVP.

- Layer 2 **provides the release gate signal** via `ci_regression.sh` and `core/release/gate_engine.py`.
- Deployment reads the gate signal (exit code 0 = PASS, exit code 1 = FAIL) and blocks or allows the release.
- Layer 2 **provides the rollback trigger** when post-deploy monitoring detects a BIS drop or grounding degradation exceeding defined thresholds.
- Deployment executes the rollback; Layer 2 provides the evidence that a rollback is warranted.
- Layer 2 **never executes deploys, never triggers CI pipelines, and never modifies infrastructure state**. It provides signals; Deployment acts on them.

### Responsibility Boundary Table

| Responsibility | Layer 2 Owns | Layer 2 Does NOT Own |
|---|---|---|
| Benchmark execution | ✅ Runs pipeline against Golden Dataset | ❌ Does not own the pipeline itself |
| Quality scoring | ✅ Calculates all evaluation metrics | ❌ Does not score production responses in real-time |
| Release decision | ✅ Provides pass/fail signal | ❌ Does not execute the deployment |
| Failure detection | ✅ Flags low-quality traces from Layer 1 | ❌ Does not intervene in production requests |
| Human review queue | ✅ Manages reviewer workflow and scores | ❌ Does not make final quality judgments (humans do) |
| Golden Dataset | ✅ Owns the ground truth corpus | ❌ Does not own the production data schema |
| Business Impact Score | ✅ Calculates and tracks BIS | ❌ Does not own CRM data or revenue attribution |
| Prompt versioning | ✅ Tracks and compares prompt versions (via hashes) | ❌ Does not store or manage prompt content (Layer 1 owns this via `observability_prompts`) |
| Layer 1 data | ✅ Reads Layer 1 as a data source | ❌ Does not modify Layer 1 records (except `bis_record_id` additive FK) |
| Model management | ✅ Benchmarks models against Golden Dataset | ❌ Does not route traffic to models or manage model deployments |

---




---

## SECTION C — Startup Evolution Roadmap

This section defines the full maturity arc of Layer 2, from the first benchmark run to enterprise-grade evaluation infrastructure. It is organized as six distinct phases, each with clear objectives, features, success criteria, and risk posture.

The phases are not strict time-boxes. They are **capability stages**. A team of two founders can compress or expand the timeline. What matters is that no phase is skipped — the capabilities of each phase are the prerequisites for the next.

---

### Phase 1: MVP

**Objective**: Establish the minimum evaluation capability required to release software responsibly.

**Engineering Focus**: Schema migration, benchmark runner, regression CI gate.

**Business Focus**: Protect against invisible regressions before the first external user.

**Features**:
- Golden Dataset (30–50 hand-authored test cases, all intent types covered)
- Regression benchmark suite (< 3 minutes, CI-integrated)
- Basic benchmark result viewer (Next.js)
- `ci_regression.sh` release gate (blocks merges on BLOCK-level threshold failures)
- Failure Database (manual entry only)
- Core evaluation metrics: M-01 Intent Accuracy, M-02 Entity F1, M-09 JSON Validity, M-10 Latency

**Success Criteria**:
- [ ] 30+ golden test cases exist, covering every intent type
- [ ] `ci_regression.sh` runs and exits with code 0 or 1 in < 3 minutes
- [ ] CI pipeline blocks a merge on a deliberate regression (verified by introducing a known bad change)
- [ ] All BLOCK-level thresholds are defined and documented
- [ ] Zero releases made without passing the regression gate

**Risk Reduction**: Prevents the single most common early-stage AI startup failure — shipping a regression undetected because there was no systematic regression check.

---

### Phase 2: Internal Alpha

**Objective**: Establish quality visibility and the failure-to-golden pipeline.

**Engineering Focus**: Dashboards, failure database, human review queue, automatic failure flagging.

**Business Focus**: Build the internal feedback loop so every production failure becomes a future safeguard.

**Features**:
- Quality Dashboard (EQS trend, grounding trend, intent accuracy trend)
- Failure Dashboard (triage queue, severity breakdown, root cause distribution)
- Automatic failure flagging from Layer 1 (low grounding, low confidence, thumbs-down)
- Human review queue with 7-dimension scoring rubric
- Failure → Golden Dataset promotion workflow (manual, developer-initiated)
- Full evaluation metrics suite (M-01 through M-13)
- Grounding Score (M-05) — LLM-as-judge activated
- Recommendation Quality Score (M-08) — LLM-as-judge activated

**Success Criteria**:
- [ ] Every production failure with `grounding_score = LOW` is automatically flagged within 60 seconds
- [ ] Human review queue has at least 5 reviewed responses per week
- [ ] 10+ failures have been promoted to Golden Dataset as regression tests
- [ ] Quality Dashboard renders correct trend data for the past 30 days
- [ ] Golden Dataset has grown to 80+ cases

**Risk Reduction**: Closes the loop between production failures and test coverage. Prevents the accumulation of invisible technical debt in the evaluation suite.

---

### Phase 3: Closed Beta

**Objective**: Enable systematic prompt and model improvement.

**Engineering Focus**: Prompt comparison workflow, model benchmark runner, BIS Engine MVP.

**Business Focus**: Make every prompt change a data-driven decision. Begin measuring business impact alongside technical quality.

**Features**:
- Prompt comparison workflow (A/B/C benchmark reports)
- Model benchmark runner (compare Llama, Qwen, DeepSeek, Mistral on identical datasets)
- Business Impact Score (BIS) — MVP version with Tier 1 and Tier 2 signals
- `bis_records` table and BIS event ingestion API
- Business Impact Dashboard (acceptance rate, time saved estimate)
- `observability_traces.bis_record_id` FK integration (Layer 1 ↔ Layer 2 bridge)
- Prompt Dashboard and Model Dashboard activated

**Success Criteria**:
- [ ] At least one prompt improvement has been validated through the prompt comparison workflow before being promoted to production
- [ ] BIS is calculated for > 90% of production traces
- [ ] Mean BIS category is visible in the Business Impact Dashboard
- [ ] Model benchmark has been run for at least 3 local models
- [ ] Prompt Dashboard shows at least 2 prompt versions in comparison history

**Risk Reduction**: Prevents prompt changes from being made based on intuition alone. Prevents model upgrades from being deployed without quality comparison evidence.

---

### Phase 4: Paid Beta

**Objective**: Harden the release process and activate the complete business measurement layer.

**Engineering Focus**: Full Release Dashboard, complete BIS signal taxonomy, regression report automation.

**Business Focus**: Demonstrate to early paying customers that APEX quality is measurably improving. Provide evidence of business value through BIS.

**Features**:
- Full Release Dashboard (Go/No-Go display, blocking issues, release history timeline)
- Complete BIS signal taxonomy (Tier 1 + 2 + 3 + negative signals all active)
- BIS weight configuration via `bis_weight_config` table (no code deploy required to adjust)
- Automated regression reports on every PR (version comparison diff)
- Rollback trigger integration (auto-flag when BIS drops > 15% post-deploy)
- Golden Dataset has 150+ cases with deliberate coverage of edge cases and competitor queries
- Reviewer calibration workflow active (10 calibration cases required for new reviewers)

**Success Criteria**:
- [ ] Every release includes a generated regression report comparing vs. the last approved baseline
- [ ] Rollback has been successfully triggered and executed at least once in a staging environment
- [ ] BIS weights have been adjusted at least once via the `bis_weight_config` table without a code deploy
- [ ] At least 2 early customers have been shown a BIS dashboard report
- [ ] Golden Dataset contains 150+ cases with < 5% stale or deprecated entries

**Risk Reduction**: Protects paying customers from regressions. Provides the evidence layer for customer success conversations. Establishes the commercial narrative that APEX measurably improves sales productivity.

---

### Phase 5: Production

**Objective**: Evaluation is fully operational, trusted, and integrated into every engineering workflow.

**Engineering Focus**: Evaluation coverage completeness, trend analysis, developer console polish.

**Business Focus**: Layer 2 is a customer-facing quality guarantee. Every quality claim is backed by a benchmark number.

**Features**:
- Developer Evaluation Console — all 8 capabilities operational (CLI + UI)
- Exportable evaluation reports (CSV, JSON, PDF)
- Trend Dashboard activated (all metrics, 90-day and 1-year views)
- Human review calibration running continuously (new reviewers calibrated before queue access)
- Golden Dataset 300+ cases — covers every production failure class observed to date
- All 8 dashboards operational and actively monitored
- Evaluation coverage > 95% (every intent type has 15+ golden cases)
- Mean human review queue processed within 48 hours

**Success Criteria**:
- [ ] No release has been made without passing the full regression gate in the past 90 days
- [ ] EQS trend is stable or improving over the past 60 days
- [ ] Mean time to failure triage (OPEN → IN_TRIAGE) < 48 hours for CRITICAL severity
- [ ] Business Dashboard is reviewed weekly as part of engineering standup
- [ ] All CRITICAL failures are promoted to golden test cases within 72 hours
- [ ] Evaluation coverage report shows > 95% of production intent types covered by golden cases

**Risk Reduction**: Layer 2 is now a load-bearing component of the engineering process, not an optional quality tool. Regressions cannot reach production undetected. Business value is continuously measured.

---

### Phase 6: Enterprise

**Objective**: Layer 2 scales to multi-tenant, multi-team enterprise operation with executive-facing reporting.

**Engineering Focus**: Distributed evaluation, enterprise dashboards, continuous nightly evaluation, audit compliance.

**Business Focus**: Layer 2 becomes a procurement differentiator. Enterprise buyers can see the evidence that APEX quality is managed at engineering-grade rigor.

**Features** *(documentation only — do not implement before Phase 5 is complete)*:
- Continuous nightly evaluation (full benchmark suite runs automatically each night)
- Canary release evaluation (5% traffic, real-time BIS comparison between canary and baseline)
- Executive KPI Dashboard (AI adoption, time saved organization-wide, revenue influence)
- Multi-tenant BIS isolation (each customer workspace has its own BIS tracking)
- ROI Analytics (BIS connected to actual CRM revenue fields)
- Prompt Registry integration (named prompt versions replace SHA256 hash references)
- Distributed benchmark execution (parallel workers for 1,000+ case datasets)
- Evaluation audit export (SOC 2 / enterprise compliance report generation)
- Cross-account trend analysis (which account types produce highest BIS)
- Multi-agent evaluation (when APEX spawns sub-agents, evaluate inter-agent quality)

**Success Criteria for Entry** (conditions required before starting Phase 6 work):
- Phase 5 complete and stable for > 60 days
- Golden Dataset > 500 cases
- EQS stable at > 80 for > 30 days
- At least 3 enterprise customers actively using APEX

---

## SECTION D — Architecture Decision Records (ADR)

Architecture Decision Records capture the decisions that shaped Layer 2's design. Every ADR documents not only the decision made, but the alternatives considered and the conditions under which the decision should be revisited.

This section is a living record. New ADRs must be added whenever a significant architectural decision is made. No ADR should ever be deleted — only superseded by a newer ADR that references it.

---

### ADR-001: Use PostgreSQL as the Sole Data Store

| Field | Value |
|---|---|
| **Decision** | Use PostgreSQL exclusively for all Layer 2 data: golden dataset, benchmark results, failure database, human reviews, BIS records, and configuration. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Layer 2 needs a data store for structured evaluation data with relational integrity (benchmark results reference golden cases, failures reference traces). Options evaluated included PostgreSQL, Redis (for fast queue-like access), a dedicated vector store (for semantic similarity search), and a time-series database (for metrics).

**Decision**: PostgreSQL exclusively.

**Reason**:
- APEX already operates a PostgreSQL instance for production data and Layer 1 observability. Adding a second data store doubles operational complexity for a 2-person team.
- All Layer 2 queries are analytical, not sub-millisecond operational. PostgreSQL's `PERCENTILE_CONT`, GIN indexes on JSONB, and window functions satisfy all query requirements.
- A single database simplifies backup, RLS policy management, and developer onboarding.
- PostgreSQL's JSONB type handles the flexible schema requirements (golden test case expected outputs, BIS signal events, benchmark metadata) without requiring schema migrations for every new field.

**Alternatives Considered**:
- **Redis**: Considered for fast failure queue access. Rejected — a PostgreSQL table with an indexed `status` column is sufficient for the expected failure queue volume (< 100 entries/day). Redis adds operational complexity (separate service, persistence configuration, connection management) without meaningful performance benefit at this scale.
- **ClickHouse / TimescaleDB**: Considered for trend analytics (latency percentiles, EQS over time). Rejected — PostgreSQL window functions are adequate for the expected data volume (< 10,000 benchmark results/month for the first year). Revisit if query latency exceeds 5 seconds on 6-month trend queries.
- **SQLite**: Considered for developer local evaluation. Rejected — differences in SQL dialect and JSONB handling between SQLite and PostgreSQL create divergence between local and production evaluation behavior.

**Trade-offs**:
- Accepted: PostgreSQL query performance for large analytical windows (> 1 year of benchmark data) will require attention. Mitigated by retention policies and table partitioning when needed.
- Accepted: PostgreSQL is not optimized for time-series append workloads. `eval_benchmark_results` growth will require monitoring. Mitigated by quarterly retention policy review.

**Review Trigger**: When PostgreSQL query latency for any dashboard query exceeds 3 seconds on 30-day windows with > 100,000 benchmark results, evaluate TimescaleDB extension or table partitioning.

---

### ADR-002: Do Not Use Redis

| Field | Value |
|---|---|
| **Decision** | Redis is explicitly excluded from the Layer 2 architecture. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Redis is a common addition to FastAPI applications for caching, queues, and rate limiting. Several Layer 2 use cases appear to benefit from Redis: the failure queue, BIS event streaming, and benchmark result caching.

**Decision**: No Redis.

**Reason**:
- Every Layer 2 operation that might benefit from Redis can be served by PostgreSQL at the expected scale for the next 12 months.
- Redis requires a separate service, persistence configuration, eviction policy management, and connection pooling. For a 2-person team, this operational overhead is not justified.
- "Premature optimization" applies: Redis should be added when a specific, measured PostgreSQL bottleneck justifies it — not speculatively.
- Background benchmark jobs (APScheduler) do not require a message broker. APScheduler with PostgreSQL persistence is sufficient for the scheduled benchmark use case.

**Trade-offs**:
- Accepted: benchmark job scheduling relies on APScheduler's PostgreSQL-backed job store rather than Redis-backed queues. This limits job distribution to a single process. Acceptable until benchmark volume exceeds single-process capacity.

**Review Trigger**: When concurrent benchmark runs exceed 10 simultaneously OR when benchmark job scheduling reliability falls below 99% (jobs not starting within 60 seconds of scheduled time), evaluate Redis or a PostgreSQL-native queue (pg-boss pattern).

---

### ADR-003: Use SHA256 Prompt Hashes for Prompt Identity

| Field | Value |
|---|---|
| **Decision** | Identify prompts by their SHA256 hash, not by name or version string. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Layer 1 already uses SHA256 hashes to track prompt versions (`observability_prompts.prompt_hash`). Layer 2 must reference the same prompts in benchmark runs and comparison reports.

**Decision**: Use SHA256 hashes as the canonical prompt identifier.

**Reason**:
- Deterministic: the same prompt text always produces the same hash. No naming conflicts, no version string collisions, no accidental reuse of version labels.
- Enables reproducibility: a benchmark run referencing `prompt_hash: abc123` can always retrieve the exact prompt text that was used, regardless of when the query is executed.
- Consistent with Layer 1: avoids a dual tracking system where Layer 1 uses hashes and Layer 2 uses names. One identifier serves both layers.
- Enables the replay engine: `core/replay/replayer.py` can reconstruct the exact context of any historical trace by referencing the prompt hashes from `observability_payloads`.

**Alternatives Considered**:
- **Semantic version strings** (e.g., `narrator_v3.2.1`): rejected because they require a separate registry to maintain the name → hash mapping, create coordination overhead between engineers ("who's incrementing the version?"), and do not prevent duplicate content under different names.
- **Timestamp-based IDs**: rejected because they are not content-addressable. Two identical prompts at different timestamps would have different IDs, making deduplication impossible.

**Trade-offs**:
- Accepted: SHA256 hashes are opaque. Benchmark reports show hashes rather than human-readable names until the Prompt Registry (Layer 6, future) is implemented. Mitigated by storing `prompt_version` as a human-readable label alongside the hash in `observability_prompts`.

**Review Trigger**: When a Prompt Registry (Layer 6) is implemented, migrate prompt comparison reports from hash references to named, versioned registry entries. The hash remains as the underlying identity; the name becomes an alias.

---

### ADR-004: Use Business Impact Score as a Primary Success Metric

| Field | Value |
|---|---|
| **Decision** | BIS is a first-class evaluation metric alongside EQS. Release gate thresholds and dashboard primary positions reflect this. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Traditional AI evaluation focuses on technical quality: accuracy, precision, recall, grounding, latency. These metrics answer "is the AI working correctly?" They do not answer "is the AI creating value?"

**Decision**: BIS is a primary success metric for Layer 2, not an ancillary reporting metric.

**Reason**:
- Enterprise customers purchase APEX to improve sales productivity and deal outcomes. Technical AI quality is a means to that end, not the end itself.
- A response with EQS 90 that no sales rep ever acts on has zero commercial impact. A response with EQS 72 that leads to a deal stage advancing has high commercial impact.
- BIS makes the distinction between AI quality and AI value explicit and measurable.
- Including BIS as a primary metric aligns the engineering team's incentives with customer outcomes, not with model accuracy optimization.
- BIS is a differentiated capability: most AI evaluation frameworks (MLFlow, Weights & Biases, LangSmith) do not measure downstream business impact. APEX can communicate quality in business terms, not just ML terms.

**Alternatives Considered**:
- **EQS only**: rejected because EQS measures technical quality, not commercial value. An AI team optimizing for EQS alone may produce a technically perfect but commercially ignored product.
- **User satisfaction score only**: rejected because user satisfaction is subjective and gameable (a response that feels good but leads to no action scores high on satisfaction but low on BIS).

**Trade-offs**:
- Accepted: BIS calculation depends on user behavior signals that may be delayed (CRM stage changes take days or weeks to register). BIS scores for recent traces will be incomplete. Mitigated by displaying BIS with a "confidence" indicator reflecting signal completeness.
- Accepted: BIS attribution is imperfect. A deal that advances after an APEX session may have advanced for reasons unrelated to APEX. BIS records correlation, not causation. Mitigated by transparency in BIS dashboards and calculation notes.

**Review Trigger**: Quarterly review of BIS weight configuration. If BIS scores become systematically gamed (e.g., reps artificially accepting recommendations to improve BIS), revisit the signal weighting model.

---

### ADR-005: Evaluate in Isolation — Never Affect Production

| Field | Value |
|---|---|
| **Decision** | Layer 2 evaluation runs in a separate process from production. It reads Layer 1 data as a data source. It never instruments production request paths. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Some evaluation architectures (e.g., shadow scoring, inline grading) evaluate responses in the production request path, scoring responses before they are returned to the user. This enables real-time quality gating.

**Decision**: Layer 2 never runs in the production request path.

**Reason**:
- Every millisecond added to the production request path degrades user experience. Grounding evaluation via LLM-as-a-judge adds 1–3 seconds per request. This is unacceptable.
- Evaluation should not be able to cause production failures. An evaluation bug should never result in a user-visible error.
- Separation of concerns: the evaluation layer must be independently deployable and independently releasable from the production pipeline.
- Post-hoc evaluation is sufficient for APEX's use case: production responses are already delivered to users; evaluating them after the fact does not reduce their value to users.

**Trade-offs**:
- Accepted: Layer 2 cannot prevent a bad response from reaching a user in real-time. Bad responses are detected after the fact and addressed through the failure database and golden dataset pipeline. Mitigated by the release gate, which prevents new regressions from reaching production in the first place.

**Review Trigger**: If a future use case requires real-time quality gating (e.g., blocking a response that scores LOW on grounding before it reaches the user), revisit this decision. At that point, a dedicated low-latency inline scorer (not the full Layer 2 evaluation suite) should be designed as a separate Layer 0 component.

---

### ADR-006: Configurable BIS Weights Without Code Deployment

| Field | Value |
|---|---|
| **Decision** | BIS signal weights are stored in `bis_weight_config` (PostgreSQL JSONB). Changing weights requires no code change and no deployment. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: Business priorities change. In one quarter, email engagement may be the most important signal (email-heavy sales cycle). In another, CRM updates may matter more (CRM-adoption quarter). Hardcoding weights in application code means every business priority shift requires a code change, a deployment, and a regression test run.

**Decision**: BIS weights are database-driven. The `bis_weight_config` table stores the active weight configuration as JSONB. The BIS engine loads the active configuration at calculation time.

**Reason**:
- Decouples business strategy decisions from engineering release cycles.
- Enables rapid experimentation: change weights, observe BIS distribution shift, revert if needed — all without touching code.
- Creates an auditable history of weight changes: every configuration version is preserved with `created_at`, `created_by`, and `notes`.
- The `CONSTRAINT single_active_config UNIQUE (is_active) WHERE (is_active = TRUE)` ensures exactly one active configuration at any time.

**Trade-offs**:
- Accepted: a misconfigured weight table could silently distort BIS scores. Mitigated by requiring all weight configuration changes to be reviewed by the architecture owner before activation, and by logging all configuration changes with justification notes.

**Review Trigger**: If BIS weight changes are made more than once per month, consider whether the weighting model is too volatile to be meaningful. Reassess the signal taxonomy and weight stability quarterly.

---

### ADR-007: Human Review Is the Source of Truth

| Field | Value |
|---|---|
| **Decision** | Automatic metrics (EQS, grounding score, recommendation quality) assist and accelerate human review. They never override it. A response that scores EQS 85 but receives Overall Satisfaction 2 from a human reviewer is classified as a failure. |
| **Status** | Active |
| **Date** | July 2026 |

**Context**: LLM-as-a-judge metrics are fast and scalable. They can score thousands of responses per hour. Human reviewers can score tens per week. There is a temptation to rely primarily on automatic metrics and treat human review as optional.

**Decision**: Human review is the source of truth. Automatic metrics are optimized to predict human review scores, not to replace them.

**Reason**:
- LLM-as-a-judge metrics exhibit known systematic biases: verbosity bias, positional bias, self-consistency failures, and model-specific blind spots. These biases compound over time and can drift from actual quality in unpredictable directions.
- Human reviewers — specifically, domain-expert sales professionals or sales engineers — carry contextual knowledge about what constitutes a useful recommendation that no metric can fully encode.
- The calibration loop (human scores → recalibrate automatic metrics → human scores again) is the mechanism that keeps Layer 2 honest. Without human review, automatic metrics drift toward measuring what they measure well, not what matters to users.

**Trade-offs**:
- Accepted: human review is slow. A 2-person team cannot review every production response. Mitigated by sampling strategy (prioritize low-EQS responses, random 5% sample of high-EQS responses for calibration) and by treating human review as a calibration process rather than a comprehensive audit.

**Review Trigger**: If human review queue backlog exceeds 2 weeks regularly, reassess sampling strategy and review bandwidth. Consider adding external reviewers with domain expertise.

---

## SECTION E — Definition of Done

Layer 2 is "done" when it is actively preventing regressions, actively measuring business impact, and actively guiding engineering decisions. It is never done in the sense of no further work — it grows with the product.

The following criteria define "done" for each major capability. Every criterion is binary (measurable as true or false) and must be verified by a person, not assumed.

### E-1: Golden Dataset — Done When

- [ ] Contains 30+ cases covering every production intent type (verified by intent type coverage report)
- [ ] Every case has an assigned owner (verified by querying `owner_id IS NOT NULL` on all active cases)
- [ ] Every case has been reviewed and approved by the owner at least once (verified by `review_notes` field populated)
- [ ] At least 30 cases are tagged `[regression]` (verified by tag count query)
- [ ] At least 5 cases have been promoted from the Failure Database (verified by `source = PROMOTED_FROM_FAILURE` query)
- [ ] Golden Dataset growth rate is > 5 cases per sprint (verified by `created_at` distribution query)

### E-2: Regression Suite — Done When

- [ ] Full regression suite runs in < 3 minutes on a standard developer machine (verified by timing the CI run)
- [ ] CI gate script (`ci_regression.sh`) exits with code 1 when a deliberate regression is introduced (verified by a live test: introduce a known bad change, confirm CI blocks the merge)
- [ ] CI gate script exits with code 0 when all thresholds pass (verified by passing run in CI history)
- [ ] Regression suite has been integrated into the PR merge workflow (verified by CI configuration)
- [ ] All 7 BLOCK-level thresholds are defined, documented, and enforced in `gate_engine.py`

### E-3: Benchmark Runner — Done When

- [ ] All 13 evaluation metrics (M-01 through M-13) are implemented and tested in `core/metrics/`
- [ ] Benchmark runner can execute a full 50-case run without error (verified by a complete run)
- [ ] Benchmark results are persisted to `eval_benchmark_results` with correct data (verified by spot-checking 5 records against expected values)
- [ ] Benchmark results link correctly to golden dataset versions (verified by FK integrity check)
- [ ] Replay engine (`replayer.py`) can score at least 10 historical Layer 1 traces (verified by running replay on selected traces)

### E-4: Prompt Comparison — Done When

- [ ] Prompt A/B comparison workflow generates a comparison report showing all 7 metric columns
- [ ] At least one real prompt comparison has been run and the report has been reviewed
- [ ] The comparison report includes a "RECOMMENDATION" field with rationale
- [ ] Comparison results are stored in `eval_prompt_benchmarks` with correct prompt hash references
- [ ] A human decision (promote or reject) is required and recorded before any prompt is promoted to production

### E-5: Model Benchmark — Done When

- [ ] Model benchmark has been run for at least 3 local models (Llama, Qwen, and one other)
- [ ] Model comparison report shows all 6 comparison metrics per model
- [ ] Model benchmark results are stored in `eval_model_benchmarks`
- [ ] At least one model comparison report has been used as the basis for a model selection decision

### E-6: Human Review — Done When

- [ ] Reviewer queue is operational (responses appear in queue, can be scored, scores persist)
- [ ] All 7 scoring dimensions are implemented with correct 1–5 constraint enforcement
- [ ] At least 20 responses have been reviewed (verified by `eval_human_reviews` count)
- [ ] Calibration cases are available (10 pre-scored cases exist in the system)
- [ ] Cases where human score diverges significantly from EQS are automatically flagged

### E-7: Failure Database — Done When

- [ ] Automatic failure flagging is running in production (verified by checking `eval_failure_database` populates when a low-grounding trace is recorded in Layer 1)
- [ ] Failure → Golden Dataset promotion workflow is end-to-end functional (verified by promoting a test failure and confirming the golden case appears)
- [ ] All 5 required fields for CRITICAL failures (root cause, owner, resolution, regression test ID, prevention notes) are enforced by application validation
- [ ] At least one CRITICAL failure has been triaged, resolved, and promoted to a golden test case

### E-8: Release Dashboard — Done When

- [ ] Dashboard renders a Go/No-Go status based on the latest regression run
- [ ] Dashboard shows all BLOCK-level and WARN-level metrics with current values vs. thresholds
- [ ] Dashboard shows release history (last 10 releases with commit SHA, EQS, and status)
- [ ] Rollback trigger has been tested in a staging environment

### E-9: Business Impact Score — Done When

- [ ] BIS is calculated for > 90% of production traces (verified by `observability_traces LEFT JOIN bis_records` null count)
- [ ] `bis_record_id` FK is populated on `observability_traces` for all BIS-calculated traces
- [ ] BIS weight configuration is loaded from `bis_weight_config` table (not hardcoded)
- [ ] Business Impact Dashboard shows weekly mean BIS, acceptance rate, and time saved estimate
- [ ] At least one BIS weight configuration change has been made via the database without a code deploy

### E-10: Developer Console — Done When

- [ ] All 8 developer console capabilities are functional (run single, run suite, compare prompts, compare models, inspect failures, promote failure, generate report, export report)
- [ ] CLI interface (`python -m apex_eval`) supports the 4 primary commands
- [ ] Reports can be exported in at least 2 formats (CSV and Markdown as minimum)
- [ ] Console UI is accessible without production credentials (uses evaluation-specific auth scope)

---

## SECTION F — Layer Success Metrics

These metrics measure the health and effectiveness of Layer 2 itself — not the APEX pipeline it evaluates. They answer: "Is our evaluation platform working?"

These are **layer-level operational metrics**, not product quality metrics.

| Metric | Definition | Target | Measurement Method |
|---|---|---|---|
| **Regression Suite Runtime** | Wall-clock time for full regression benchmark (30 cases) to complete | < 3 minutes | CI run timestamps |
| **Regression Suite Reliability** | Percentage of scheduled CI regression runs that complete without error | > 99% | CI success rate over 30 days |
| **Golden Dataset Size** | Total active golden test cases | Growth of 5+ per sprint | `SELECT COUNT(*) FROM eval_golden_dataset WHERE status = 'ACTIVE'` |
| **Golden Dataset Coverage** | Percentage of production intent types represented by >= 15 golden cases each | 100% | Intent type distribution query |
| **Benchmark Execution Success Rate** | Percentage of benchmark runs that complete without error or timeout | > 98% | `eval_runs` status distribution |
| **Failure Detection Rate** | Percentage of production traces with `grounding_score = LOW` that have a corresponding `eval_failure_database` entry within 60 seconds | > 95% | Timestamp comparison query across both tables |
| **Failure Triage Rate** | Percentage of CRITICAL failures moved from OPEN to IN_TRIAGE within 48 hours | 100% | `eval_failure_database` status + timestamp analysis |
| **Failure Promotion Rate** | Percentage of FIXED failures that are promoted to the Golden Dataset as regression tests | > 80% | `regression_test_id IS NOT NULL` on FIXED failures |
| **Human Review Throughput** | Number of responses reviewed per week | > 10 per week minimum, > 20 per week target | `eval_human_reviews` weekly count |
| **Human Review Backlog** | Number of responses in queue awaiting review older than 72 hours | < 20 | Queue age analysis |
| **Human-Automatic Metric Alignment** | Correlation between EQS and human Overall Satisfaction score | Pearson r > 0.70 | Correlation query across `eval_benchmark_results` and `eval_human_reviews` |
| **BIS Coverage** | Percentage of production traces with a calculated BIS record | > 90% | `observability_traces` null bis_record_id count |
| **BIS Calculation Latency** | Time from Layer 1 business metric event to BIS record update | < 5 minutes | Event timestamp vs. `bis_records.calculated_at` |
| **Prompt Regression Frequency** | Number of prompt changes that required rollback due to benchmark failure | Target: 0 per sprint | Prompt comparison report history |
| **Evaluation Infrastructure Uptime** | Percentage of time the evaluation API and dashboards are available | > 99.5% | API health check monitoring |
| **Engineering Adoption** | Percentage of PRs that include a passing regression gate before merge | 100% | CI merge requirement enforcement |

### Layer Health Indicators

Three metrics serve as leading indicators of Layer 2 health. If any of these degrades, the evaluation platform itself is failing.

1. **Regression Suite Reliability < 95%**: The evaluation platform is unreliable. Engineers will stop trusting it.
2. **Human Review Backlog > 50 entries > 1 week old**: The human calibration loop is broken. Automatic metrics are drifting undetected.
3. **Golden Dataset Coverage < 80%**: Critical production intent types lack regression coverage. The evaluation platform has blind spots.

---

## SECTION G — Risk Register

The Risk Register documents the known risks to Layer 2's effectiveness. Each risk is assessed for impact and likelihood, with a defined mitigation strategy and review frequency.

> [!WARNING]
> Risks in this register are not hypothetical. Every risk described here has been observed in production AI evaluation systems at comparable scale. They are included because they will materialize if not actively managed.

---

### RISK-001: Evaluation Drift

| Field | Value |
|---|---|
| **Risk** | Automatic evaluation metrics (grounding score, recommendation quality) drift from actual quality over time as the LLM evaluator model changes or as production output distribution shifts. |
| **Impact** | HIGH — decisions are made based on metrics that no longer accurately reflect quality. Regressions are missed. False confidence grows. |
| **Likelihood** | HIGH — LLM evaluation drift is a documented phenomenon observed in production AI systems within 3–6 months of deployment. |

**Mechanism**: The grounding scorer and recommendation quality scorer use an LLM as a judge. As the judge model is updated (or as production outputs shift in style and format), the same underlying quality may receive different scores. Without recalibration, the metric appears to show improvement or regression when quality is actually stable.

**Mitigation**:
1. Human review is mandatory and continuous. Automatic metrics must be calibrated against human scores monthly.
2. A calibration dataset of 20 permanently-fixed responses with known human scores must be scored by the automatic evaluator monthly. Score drift > 0.3 points triggers a recalibration review.
3. When the judge LLM model is updated, the calibration dataset is immediately re-scored and drift is measured before the new model is used in production evaluation.

**Review Frequency**: Monthly calibration check. Immediate review whenever the judge model is changed.

---

### RISK-002: Golden Dataset Staleness

| Field | Value |
|---|---|
| **Risk** | Golden test cases become stale as the production system evolves — expected outputs reference outdated data models, deprecated intent types, or superseded recommendation formats. |
| **Impact** | HIGH — stale golden cases produce false regressions (failing on correct behavior) or false passes (passing on incorrect behavior). Both undermine trust in the evaluation platform. |
| **Likelihood** | MEDIUM — inevitable over 6+ months as the pipeline evolves. |

**Mechanism**: A golden test case authored in Q1 expects `expected_intent: "account_summary"`. In Q3, the intent is renamed to `"account_overview"` in the Planner. The golden case now shows a false regression every run.

**Mitigation**:
1. Every golden test case has an owner. Owners are notified of intent taxonomy or response schema changes.
2. Quarterly "Golden Dataset Audit" sprint task: review all ACTIVE cases for staleness. Deprecate or update stale cases.
3. If any benchmark run produces > 10% false regression rate (cases that fail but manually reviewing the actual output shows it is correct), a full Golden Dataset audit is triggered immediately.

**Review Frequency**: Quarterly audit. Immediate review when false regression rate exceeds 10%.

---

### RISK-003: Human Reviewer Inconsistency

| Field | Value |
|---|---|
| **Risk** | Different human reviewers score the same response differently, producing inconsistent ground truth that undermines metric calibration. |
| **Impact** | MEDIUM — calibration data becomes noisy. Metrics are calibrated against an inconsistent target. |
| **Likelihood** | HIGH — inter-reviewer variability is a fundamental challenge in any human evaluation system. |

**Mechanism**: Reviewer A scores "Business Usefulness" 4 for a response that Reviewer B scores 2. Both are responding to the same text. Without calibration, the human review corpus contains contradictory ground truth.

**Mitigation**:
1. Calibration cases (10 pre-scored responses with agreed "correct" scores) are required before a reviewer accesses the live queue.
2. Inter-reviewer agreement is measured monthly. Any reviewer with mean absolute disagreement > 1.0 points vs. consensus is paused and recalibrated.
3. The 5-point rubric behavioral anchors are specific enough to reduce ambiguity. "Actionability 5 = Specific + prioritized + named contact" leaves less room for interpretation than "Actionability 5 = Very actionable."

**Review Frequency**: Monthly inter-reviewer agreement analysis. Immediate calibration when a new reviewer joins.

---

### RISK-004: Prompt Overfitting to Golden Dataset

| Field | Value |
|---|---|
| **Risk** | Prompts are optimized to perform well on the Golden Dataset specifically, rather than on the general production distribution. The Golden Dataset becomes a leaderboard rather than a representative sample. |
| **Impact** | HIGH — benchmark scores improve while production quality stagnates or degrades. |
| **Likelihood** | MEDIUM — this is a known failure mode in AI evaluation ("Goodhart's Law for benchmarks"). |

**Mechanism**: A prompt engineer observes that golden test cases about "stakeholder analysis" score low. They add specific stakeholder handling instructions to the prompt. The golden test cases now pass. But the new instructions cause regressions on non-golden production queries that were previously handled correctly.

**Mitigation**:
1. The Golden Dataset must include a "held out" subset (minimum 10 cases) that is never used for prompt optimization — only for final regression verification. These cases must not be visible during prompt development.
2. Prompt changes must be accompanied by a production-trace evaluation: replay 50 recent random production traces through the new prompt and compare scores against the baseline. This detects distribution shift that golden-only optimization misses.
3. Quarterly "Golden Dataset refresh": add 10 new cases from recent production traffic that prompt engineers have not seen before. This continuously widens the target distribution.

**Review Frequency**: Every prompt promotion includes a production-trace replay evaluation. Quarterly held-out set refresh.

---

### RISK-005: Metric Gaming

| Field | Value |
|---|---|
| **Risk** | Engineers (or automated systems) optimize pipeline changes specifically to improve metric scores rather than actual quality. |
| **Impact** | HIGH — metrics become misleading. Stakeholders make decisions based on numbers that no longer reflect quality. |
| **Likelihood** | LOW initially; MEDIUM at team sizes > 5. |

**Mechanism**: If EQS is the sole release criterion and engineers are evaluated on EQS improvement, there is pressure to find ways to improve EQS without improving quality — for example, increasing narrative structure score (M-07) by adding empty required sections, improving JSON validity (M-09) by adding fallback schemas that always pass, or improving grounding score by shortening responses.

**Mitigation**:
1. The human review score is the source of truth. High EQS + low human score = failure, not success.
2. Multiple metrics in the EQS composite weight prevent single-metric gaming. Improving M-07 alone while M-08 and M-05 degrade produces a net-negative EQS.
3. Quarterly metric review: examine whether any metric has been consistently maxed out (near 100%) for > 60 days. If so, investigate whether this reflects genuine quality saturation or metric saturation.

**Review Frequency**: Quarterly metric review. Immediate investigation if any single metric consistently exceeds 98% for > 60 days.

---

### RISK-006: Business Impact Metric Bias

| Field | Value |
|---|---|
| **Risk** | BIS is biased toward recommendation types that naturally produce observable signals (email sends, report downloads) and systematically undervalues recommendation types where action is internal and unobservable (private notes, verbal follow-ups). |
| **Impact** | MEDIUM — some recommendation types appear low-value in BIS reports while actually being high-value. Pipeline development is biased toward signal-rich recommendation types. |
| **Likelihood** | HIGH — this bias is structural and inherent to any signal-based impact measurement. |

**Mitigation**:
1. BIS dashboard includes a "signal completeness" indicator per recommendation type. Recommendation types with low observable signal rates are annotated as "low signal coverage" rather than "low impact."
2. Quarterly review of BIS signal distribution: if any recommendation type consistently produces < 10% signal coverage, add a manual "impact check" process for that type (human reviewer confirms impact in a sample of cases).
3. Weight configuration acknowledges this bias: Tier 3 (passive engagement) signals are given low weight specifically because they are the most universally observable, preventing them from dominating BIS for all recommendation types.

**Review Frequency**: Quarterly BIS signal distribution analysis.

---

### RISK-007: False Confidence from High EQS

| Field | Value |
|---|---|
| **Risk** | A stable or improving EQS creates organizational confidence that the system is high quality, while important quality dimensions not captured by EQS degrade silently. |
| **Impact** | HIGH — production quality degrades in unmeasured dimensions while the team believes quality is improving. |
| **Likelihood** | MEDIUM — EQS is a weighted composite of 7 metrics. Dimensions outside those 7 are not measured. |

**Mechanism**: EQS is 90+ for 60 days. Team is confident. Meanwhile, strategic recommendation quality has degraded (the AI is now recommending EXPAND strategies for accounts in RECOVERY mode), which is not captured by any current metric. A customer churns after acting on a bad recommendation.

**Mitigation**:
1. Human review is the safeguard against EQS blind spots. Random sampling of high-EQS responses is mandatory — never only review low-EQS cases.
2. BIS provides an orthogonal signal. If EQS is high but mean BIS is declining, investigate.
3. Quarterly "dark corner" review: the engineering and product team deliberately searches for quality dimensions not currently captured by EQS and assesses whether they should be added as new metrics.

**Review Frequency**: Quarterly "dark corner" review. Continuous human review of random EQS samples.

---

### RISK-008: Storage Growth

| Field | Value |
|---|---|
| **Risk** | `eval_benchmark_results` and `bis_records` grow unboundedly, causing query performance degradation and storage cost growth. |
| **Impact** | MEDIUM — dashboard query latency increases. Storage costs grow. |
| **Likelihood** | HIGH — storage growth is guaranteed without a retention policy. |

**Mitigation**:
1. Retention policies are defined in the schema (see Section 16). They must be implemented as scheduled PostgreSQL jobs within the first 90 days of operation.
2. Quarterly storage analysis: report total row counts for all `eval_*` tables. Trigger retention policy review if any table exceeds 1 million rows.
3. Table partitioning (by month) for `eval_benchmark_results` and `bis_records` when row counts exceed 500,000.

**Review Frequency**: Quarterly storage analysis. Immediate review if any dashboard query exceeds 5 seconds.

---

### RISK-009: Evaluation Cost Explosion

| Field | Value |
|---|---|
| **Risk** | LLM-as-a-judge calls for grounding scoring (M-05) and recommendation quality scoring (M-08) scale with benchmark run frequency and dataset size, producing unexpectedly high LLM API costs when cloud models are used as judges. |
| **Impact** | MEDIUM — evaluation costs become meaningful if cloud LLMs are used as the judge model. |
| **Likelihood** | LOW initially (local Ollama judge = near-zero cost); HIGH if cloud judge model adopted. |

**Mitigation**:
1. The judge model must be a local Ollama model for the MVP. Cloud judge models are an enterprise-phase consideration.
2. LLM-as-a-judge calls are batch-processed during benchmark runs, not triggered per production request.
3. If cloud judge models are adopted, implement a caching layer: identical response texts scored by the same judge model return cached scores rather than triggering new API calls.
4. Monitor total LLM-as-a-judge call volume weekly. Alert if weekly calls exceed 500 (at which point cost projection should be reviewed).

**Review Frequency**: Monthly cost monitoring when cloud judge models are in use.

---

## SECTION H — Future Evolution

> [!NOTE]
> This section is documentation only. None of these capabilities should be implemented before Phase 5 (Production) of the Startup Evolution Roadmap is complete and stable.

Layer 2 is designed to evolve without reconstruction. The MVP architecture is not a temporary scaffold — it is the permanent foundation. Future capabilities extend the foundation; they do not replace it.

### H-1: Continuous Nightly Evaluation

**Current state (MVP)**: Regression benchmark runs on every PR and on-demand.

**Future state**: A scheduled APScheduler job runs the full benchmark suite every night against the latest production commit. Each morning, an evaluation report is available showing overnight quality trends.

**Engineering path**: Extend `workers/nightly_runner.py` to trigger a FULL-type evaluation run on a cron schedule. The infrastructure (benchmark runner, result storage, dashboards) already supports this.

**Value**: Detects slow quality drift that point-in-time PR checks miss. An evaluation platform that only checks at release time misses the gradual accumulation of small regressions.

---

### H-2: Canary Release Evaluation

**Current state**: Binary release (old build → new build).

**Future state**: New build serves 5% of production traffic. Layer 2 compares BIS and EQS between the canary 5% and the baseline 95% in real time. Release proceeds only if canary metrics are not statistically worse.

**Engineering path**: Requires traffic splitting at the API gateway level (outside Layer 2's scope). Layer 2's role is to provide the canary evaluation query: compare benchmark results and BIS records tagged with `build_variant = CANARY` vs. `build_variant = BASELINE`.

**Value**: Eliminates the binary risk of a full production release. Regressions affect only 5% of users before they are detected.

---

### H-3: Prompt Registry Integration

**Current state**: Prompts identified by SHA256 hash. Human-readable names stored alongside hashes in `observability_prompts`.

**Future state**: A Prompt Registry (Layer 6) provides a canonical named, versioned registry of all prompts. Layer 2 links benchmark runs to registry entries by name and version, enabling human-readable comparison reports ("Narrator v3.2 vs. Narrator v4.0") without manual hash lookup.

**Engineering path**: When the Prompt Registry is implemented, add a `registry_entry_id` field to `eval_prompt_benchmarks`. Maintain the SHA256 hash reference for backward compatibility. Benchmark reports use registry names when available, hashes when not.

**Value**: Makes prompt comparison reports accessible to non-engineer stakeholders. "Which Narrator version are we using?" becomes a answerable question without reading SHA256 hashes.

---

### H-4: Skills Evaluation

**Current state**: Pipeline is a fixed 4-phase structure. Skills architecture is a future consideration.

**Future state**: If a dynamic skill architecture is adopted (see `Apex_architectural_review_10_July.md`), Layer 2 adds a Group 11: Skill Benchmarks. Golden test cases include `expected_skills_activated`. The benchmark runner verifies skill selection accuracy alongside intent accuracy.

**Engineering path**: Add `expected_skills_activated` field to `eval_golden_dataset`. Add `skill_selection_accuracy` and `skill_consistency_score` metrics to `eval_benchmark_results`. Implement skill selection scorer in `core/metrics/skill_metrics.py`.

**Risk note**: Skill evaluation adds significant complexity to the Golden Dataset authoring process. Every case now requires not just expected outputs but expected skill activation sequences. This is a non-trivial maintenance burden. Only implement when the skills architecture is stable and in production.

---

### H-5: Memory Evaluation

**Current state**: APEX is stateless per request (no memory layer).

**Future state**: When session memory or account memory is added, Layer 2 evaluates whether memory retrieval improved response quality. Golden test cases include `expected_memory_context` and multi-turn evaluation flows.

**Engineering path**: Extend golden test case schema to support multi-turn conversations. Add `memory_relevance_score` metric measuring whether the retrieved memory was appropriate for the query.

---

### H-6: Reflection Evaluation

**Current state**: `reflection_triggered` is recorded in `observability_traces` but Layer 2 does not evaluate reflection quality.

**Future state**: Layer 2 scores pre-reflection and post-reflection outputs separately, measuring whether reflection improved quality. Cases where reflection was triggered but produced no improvement are flagged as Reflection Failures in the Failure Database.

**Engineering path**: Add `pre_reflection_eqs` and `post_reflection_eqs` fields to `eval_benchmark_results`. Implement reflection quality scorer in `core/metrics/reflection.py` that compares the two.

---

### H-7: Multi-Agent Evaluation

**Current state**: APEX is a single-agent pipeline.

**Future state**: If APEX evolves to spawn sub-agents (e.g., a specialized stakeholder analysis agent called by the main pipeline), Layer 2 evaluates inter-agent consistency: do the sub-agent's outputs contradict the main agent's outputs? Do sub-agent confidence scores propagate correctly?

**Engineering path**: Add agent graph topology to `eval_benchmark_results`. Add inter-agent consistency metrics. This is a significant architectural extension requiring dedicated design.

---

### H-8: LLM-as-Judge Improvements

**Current state**: Single LLM judge (local Ollama) for grounding and recommendation quality.

**Future state**: Ensemble judge: 3 independent LLM judges score each response. The median score is used. Disagreement across judges is flagged for human review.

**Engineering path**: Refactor `core/metrics/grounding.py` and `core/metrics/narrative.py` to support multiple judge calls with configurable ensemble strategy (median, mean, majority vote). Store per-judge scores alongside ensemble score.

**Value**: Ensemble judging reduces individual model bias and produces more stable scores. Disagreement between judges is itself a signal — responses that judges disagree about are inherently ambiguous and benefit from human review.

---

### H-9: Human-in-the-Loop Calibration Pipeline

**Current state**: Human calibration is periodic and manual (monthly calibration check).

**Future state**: An automated calibration pipeline continuously compares automatic metric predictions against human review scores. When drift exceeds thresholds, the calibration pipeline alerts the architecture owner and provides a suggested recalibration dataset.

**Engineering path**: Build a calibration scheduler in `workers/` that runs weekly, queries recent `eval_human_reviews` alongside `eval_benchmark_results`, computes Pearson correlation between EQS and Overall Satisfaction, and generates a calibration drift report.

---

### H-10: Enterprise Reporting & ROI Attribution

**Current state**: BIS measures correlation between AI recommendations and business signals.

**Future state**: BIS connects to actual CRM revenue fields. Revenue from deals influenced by APEX recommendations is attributed proportionally, producing a demonstrable ROI figure (e.g., "$2.3M in pipeline influenced by APEX recommendations in Q3").

**Engineering path**: Requires CRM integration with revenue field access (beyond the current contact/opportunity data used for account planning). Requires statistical attribution modeling (APEX-influenced vs. APEX-independent deal progression). This is a significant product and data science effort reserved for Phase 6.

---

## SECTION I — Engineering Handbook Notes

These are the operational guidelines for engineers working with Layer 2. They answer the practical question: "What do I do in situation X?"

Every guideline is a decision rule that should require no further deliberation when the situation is encountered.

---

### When Adding or Modifying a Prompt

```
1. Assign the new prompt a human-readable label (e.g., "narrator_v4_concise")
2. Register the prompt in the system BEFORE running benchmarks
   → python -m apex_eval register-prompt --label "narrator_v4_concise" --file ./prompts/narrator_v4.txt
3. Run a PROMPT_COMPARE benchmark against the current production prompt
   → python -m apex_eval compare-prompts --phase narrator --prompt-a [current_hash] --prompt-b [new_hash] --dataset regression
4. Review the comparison report — do NOT automatically promote based on EQS alone
5. Run a PRODUCTION_TRACE_REPLAY evaluation on 50 recent random production traces
   → python -m apex_eval replay --prompt-hash [new_hash] --trace-count 50
6. Review replay results alongside prompt comparison report
7. If promoting: record the decision rationale in the prompt comparison notes field
8. Merge the code change — CI regression gate runs automatically
9. After production deploy: monitor grounding_score distribution for 24 hours
```

> [!CAUTION]
> Never promote a new prompt to production based on benchmark scores alone. Always include the production-trace replay evaluation. The golden dataset is a sample; production distribution is the reality.

---

### When Changing the Retriever (`data_retrieval_layer.py`)

```
1. Before making changes: run the current RETRIEVER benchmark group and save the baseline
   → python -m apex_eval run --type retriever --note "pre-change baseline"
2. Make the retrieval changes
3. Re-run the RETRIEVER benchmark group
   → python -m apex_eval run --type retriever --note "post-change validation"
4. Compare precision and recall: both must meet thresholds (P >= 0.80, R >= 0.85)
5. If retrieval logic changed what records are returned, review affected golden test cases
   → Query: SELECT id, query, expected_retrieval_ids FROM eval_golden_dataset WHERE expected_retrieval_ids != '{}'
   → Update expected_retrieval_ids for any cases where the new behavior is correct
6. Update golden test case versions for any modified expected outputs
7. Confirm the regression suite passes before merging
```

> [!IMPORTANT]
> Retrieval changes that improve recall at the expense of precision (returning more records but less relevant ones) can produce responses that appear better (more context = more grounded claims) while actually containing more irrelevant information. Always review both metrics together.

---

### When Modifying the Planner (`intent_classifier.py` or Planner prompt)

```
1. Run the PLANNER benchmark group against the current baseline
   → python -m apex_eval run --type planner --note "pre-change baseline"
2. Make the Planner changes
3. Re-run the PLANNER benchmark group
   → python -m apex_eval run --type planner --note "post-change validation"
4. Intent Accuracy must be >= 95%. Any drop below 95% blocks the merge.
5. Entity F1 must be >= 0.90. Any drop below 0.85 blocks the merge.
6. Check the confidence calibration: does high-confidence still correlate with correct intent?
7. If the intent taxonomy changed (new intent, renamed intent, removed intent):
   a. Update all golden test cases that reference the changed intent
   b. Update the production INTENT_TAXONOMY documentation
   c. Run a full Golden Dataset audit before merging
8. Confirm the regression suite passes before merging
```

---

### When a Production Failure Occurs

```
1. Layer 1 automatic flagging creates an entry in eval_failure_database (OPEN status)
   → Verify the entry exists: SELECT * FROM eval_failure_database WHERE trace_id = [trace_id]
2. If automatic flagging did not create the entry, create it manually:
   → python -m apex_eval create-failure --trace-id [id] --severity [CRITICAL|HIGH|MEDIUM|LOW]
3. Triage the failure:
   a. Classify root cause (PLANNER | RETRIEVER | REASONER | NARRATOR | DATA | PROMPT | MODEL | UNKNOWN)
   b. Write root_cause_detail (what specifically went wrong, not just the category)
   c. Set severity (see severity SLA table in Section 12)
   d. Assign owner
   → Update status to IN_TRIAGE
4. Investigate and fix:
   a. Identify the code or prompt change that will prevent recurrence
   b. Implement the fix
   c. Write a test that would have caught this failure
5. Promote to Golden Dataset:
   → python -m apex_eval promote-failure --failure-id [id] --expected-output "[corrected expected output]"
   → This creates a golden test case and links it to the failure record
6. Verify the regression test passes with the fix applied
7. Update failure status to REGRESSION_ADDED
8. Write prevention_notes: what architectural or process change would prevent this class of failure in the future
```

> [!CAUTION]
> When promoting a failure to the Golden Dataset, the `expected` field must contain what the **correct** output should be — not the actual (incorrect) output. A golden test case that expects a wrong answer is worse than no golden test case at all.

---

### When Running a Release

```
Pre-release checklist:

[ ] 1. All open CRITICAL failures are resolved (status = FIXED or REGRESSION_ADDED)
[ ] 2. Regression suite passes (ci_regression.sh exits 0)
[ ] 3. If any prompts changed: prompt comparison report reviewed and decision recorded
[ ] 4. If any model changed: model comparison report reviewed and decision recorded
[ ] 5. Human review queue processed within the past 48 hours (< 20 unreviewed items)
[ ] 6. Release Dashboard shows Go status (no BLOCK-level threshold failures)
[ ] 7. EQS vs. previous release: no drop > 5 points

Post-deploy monitoring (first 24 hours):

[ ] 8. Monitor grounding_score distribution (alert threshold: > 10% LOW)
[ ] 9. Monitor P90 latency (alert threshold: > 20% increase from pre-deploy baseline)
[ ] 10. Monitor BIS for first 24 hours (alert threshold: > 15% drop in mean score)
[ ] 11. Monitor user thumbs-down rate (alert threshold: > 20% in any 1-hour window)
[ ] 12. Record release in eval_release_history with commit SHA, EQS, and approved_by
```

---

### When Adding a New Golden Test Case

```
1. Identify the test case source:
   - Is this a new scenario (MANUAL)?
   - Is this a promoted production failure (PROMOTED_FROM_FAILURE)?
   - Is this from user feedback (PROMOTED_FROM_FEEDBACK)?
2. Write the expected outputs for all applicable phases:
   - expected_intent (required)
   - expected_entities (required if query includes named entities)
   - expected_retrieval_ids (required for RETRIEVER benchmark cases)
   - expected_json_schema (required for NARRATOR benchmark cases)
   - expected_narrative_keywords (optional but recommended)
   - expected_business_outcome (required for BUSINESS benchmark cases)
3. Assign: owner_id, priority, tags (minimum one tag)
4. Add [regression] tag if this case should run in every PR check
5. Run the case immediately after creation to confirm it passes with the current build
   → python -m apex_eval run --type single --golden-id [new_id]
6. If it fails on the current build: investigate before tagging as [regression]
   Either the build has a bug (investigate) or the expected output is wrong (correct it)
```

---

### When the EQS Drops Unexpectedly Between Runs

```
1. Compare the two runs side-by-side:
   → python -m apex_eval compare-runs --run-a [previous] --run-b [current]
2. Identify which golden test cases newly failed
3. For each newly failing case: examine the actual output vs. expected output
4. Classify the cause:
   a. Code change regression → create a failure entry, investigate fix
   b. Golden test case is stale → update expected output if current behavior is correct
   c. Model non-determinism → rerun 3 times; if results are inconsistent, flag for investigation
   d. Infrastructure issue → check if the evaluation environment matches production
5. Do NOT dismiss an EQS drop as "expected variance" without investigating every newly failing case
6. If the drop exceeds 5 points vs. baseline: block the release until cause is identified and resolved
```

---

### Quarterly Maintenance Checklist

```
Every quarter, the following maintenance tasks are required:

[ ] Golden Dataset audit: review all ACTIVE cases for staleness; deprecate or update as needed
[ ] Metric calibration: run calibration dataset through automatic metrics; measure drift vs. human scores
[ ] BIS weight review: assess whether current weight configuration reflects current business priorities
[ ] Storage analysis: report row counts for all eval_* tables; review retention policy implementation
[ ] Risk register review: assess each RISK-00X entry for current likelihood and mitigation effectiveness
[ ] Layer success metrics review: report all 15 Layer success metrics; identify any degradation trends
[ ] "Dark corner" review: identify quality dimensions not currently measured by EQS
[ ] Held-out dataset refresh: add 10 new golden cases from recent production traffic that prompt engineers have not seen
[ ] Enterprise roadmap checkpoint: assess whether any Phase 6 capabilities should be accelerated
```

---

*This is the end of the extended Engineering Handbook sections.*

*The following sections (1 through 20) are the original architecture specification preserved in full.*

---



> **Document Type**: Architecture Specification — Full Engineering Design  
> **Layer**: 2 — Continuous Quality & Evaluation  
> **Depends On**: Layer 1 — Observability (`backend/observability/`)  
> **Status**: MVP Architecture — Ready for Implementation  
> **Team**: 2 Founders  
> **Stack**: FastAPI · PostgreSQL · Next.js  
> **Date**: July 2026  

---

## Preamble: What Layer 2 Is and Is Not

Layer 1 (`observability/recorder.py`, `ObservabilityTrace`, `ObservabilitySpan`, `ObservabilityPayload`, `ObservabilityBusinessMetric`) captures everything that *happened* during a pipeline execution. It records trace IDs, span durations, prompt hashes, grounding scores, confidence percentages, and token counts.

Layer 1 answers: **"What happened?"**

Layer 2 consumes that telemetry and applies structured judgement to it. It runs benchmark datasets, scores outputs, compares prompt versions, compares models, tracks failures, surfaces business impact, and gates releases.

Layer 2 answers: **"Was it better?"**

**Critical constraint**: Layer 2 must never touch a production request in flight. It is a pure observer and post-hoc evaluator. Every evaluation, score, and benchmark runs on data already committed to the database or on isolated replay environments. Production latency is never affected.

---

## SECTION 1 — Executive Summary

APEX operates a deterministic 4-phase pipeline:

```
Phase 1: Planner   → Intent + Entity Extraction → JSON
Phase 2: Retriever → Deterministic Pandas Filtering → Pipe-delimited Context
Phase 3: Reasoner  → Multi-Perspective Business Reasoning → SIP JSON
Phase 4: Narrator  → Response Contract Generation → Streaming Markdown
```

Layer 1 captures per-request telemetry across all four phases via `ObservabilityTrace`, `ObservabilitySpan`, and `ObservabilityPayload`. The `backend_git_commit` and `reasoning_engine_version` fields create a versioned audit trail per request.

Layer 2 uses this telemetry to answer nine strategic questions:

| # | Question | Answered By |
|---|---|---|
| 1 | Did Prompt V2 outperform Prompt V1? | Prompt Benchmark Suite |
| 2 | Did Model A outperform Model B? | Model Benchmark Suite |
| 3 | Did retrieval improve? | Retriever Precision/Recall Metrics |
| 4 | Did recommendation quality improve? | Business Impact Score |
| 5 | Did latency increase? | Latency Regression Tests |
| 6 | Did grounding decrease? | Grounding Score Trend Analysis |
| 7 | Did users actually like the output? | Human Review Workflow |
| 8 | Should this build be released? | Release Gate Engine |
| 9 | What business value did the AI deliver? | Business Impact Score (BIS) |

---

## SECTION 2 — Core Engineering Principles

These principles are non-negotiable. Any implementation decision that violates them requires explicit architectural justification.

| # | Principle | Rationale |
|---|---|---|
| 1 | Evaluation must never affect production execution | Layer 2 is a pure observer. Zero latency impact on production. |
| 2 | Every AI change must be measurable | If you cannot measure it, you cannot improve it. |
| 3 | Every failed production request must become a future benchmark | Failures are the most valuable training signal. |
| 4 | Every benchmark must be reproducible | Same inputs must produce the same evaluation result. |
| 5 | Human feedback is the source of truth | Automatic metrics assist humans. They never replace them. |
| 6 | Automatic metrics assist humans — they never replace them | LLM-as-a-judge drifts and biases. Humans calibrate the platform. |
| 7 | Evaluation must evolve independently from the AI pipeline | The evaluation codebase has its own release cycle. |
| 8 | Simple evaluation is preferred over complicated scoring systems | An 80% accurate simple metric beats a 90% accurate one no one understands. |

---

## SECTION 3 — Architecture Overview

### System Position

```
┌─────────────────────────────────────────────────────────┐
│                  APEX Production Pipeline                │
│  Planner → Retriever → Reasoner → Narrator → Response  │
└────────────────────────┬────────────────────────────────┘
                         │ Layer 1 Telemetry
                         │ (ObservabilityTrace, Spans, Payload)
                         ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL (Observability Tables)           │
│  observability_traces · observability_spans             │
│  observability_payloads · observability_business_metrics│
└────────────────────────┬────────────────────────────────┘
                         │ Consumed by
                         ▼
┌─────────────────────────────────────────────────────────┐
│              APEX Layer 2 — Evaluation Platform         │
│                                                         │
│  Golden Dataset   →  Benchmark Runner  →  Scorer       │
│       ↓                    ↓                ↓          │
│  Failure DB       →  Human Review     →  BIS Engine    │
│       ↓                    ↓                ↓          │
│  Release Gate     →  Dashboards       →  Reports       │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack Constraints

| Layer | Technology | Rationale |
|---|---|---|
| Database | PostgreSQL only | No Redis, no Kafka, no MLFlow. Single source of truth. |
| Backend | FastAPI | Consistent with production backend. |
| Frontend | Next.js | Consistent with production frontend. |
| Background Jobs | Python asyncio + APScheduler | No Celery, no Kubernetes CronJobs. Simple, self-contained. |
| Metrics | Pure Python + SQL | No external evaluation platforms, no LangSmith, no Weights and Biases. |
| LLM-as-Judge | Local Ollama (same model family as production) | Avoid cloud dependency for evaluation. |

---

## SECTION 4 — Folder Structure

The evaluation platform lives adjacent to the production backend. It is a separate FastAPI application sharing the same PostgreSQL database but with its own tables, routes, and background workers.

```
apex-eval/
│
├── backend/
│   ├── api/
│   │   ├── golden_dataset.py        # CRUD for golden test cases
│   │   ├── benchmark_runner.py      # Trigger benchmark runs
│   │   ├── evaluation_results.py    # Query benchmark results
│   │   ├── failure_db.py            # Failure triage and promotion
│   │   ├── human_review.py          # Reviewer queue and submission
│   │   ├── prompt_compare.py        # Prompt A/B/C comparison reports
│   │   ├── model_compare.py         # Model comparison reports
│   │   ├── release_gate.py          # Release decision API
│   │   └── bis_api.py               # Business Impact Score API
│   │
│   ├── core/
│   │   ├── runner.py                # Benchmark execution engine
│   │   ├── metrics/
│   │   │   ├── planner_metrics.py   # Intent accuracy, entity F1
│   │   │   ├── retriever_metrics.py # Precision, recall
│   │   │   ├── grounding.py         # Grounding scorer (LLM-as-judge)
│   │   │   ├── latency.py           # P50/P90/P99 calculations
│   │   │   ├── cost.py              # Token cost estimator
│   │   │   ├── narrative.py         # JSON schema + markdown structure
│   │   │   └── composite.py         # Weighted overall score
│   │   ├── bis/
│   │   │   ├── bis_engine.py        # Business Impact Score engine
│   │   │   ├── bis_signals.py       # Signal definitions and weights
│   │   │   └── bis_config.py        # Configurable weight registry
│   │   ├── release/
│   │   │   ├── gate_engine.py       # Pass/fail threshold logic
│   │   │   └── regression.py        # Version-over-version comparison
│   │   └── replay/
│   │       └── replayer.py          # Replay Layer 1 traces through scorer
│   │
│   ├── models/
│   │   ├── eval_models.py           # SQLAlchemy models for all eval tables
│   │   └── bis_models.py            # BIS tracking models
│   │
│   ├── workers/
│   │   ├── nightly_runner.py        # Scheduled benchmark execution
│   │   └── failure_promoter.py      # Auto-flag low-BIS traces
│   │
│   └── main.py                      # FastAPI app entrypoint
│
├── frontend/
│   └── src/
│       └── app/
│           ├── datasets/            # Golden dataset management UI
│           ├── benchmarks/          # Benchmark run history
│           ├── review/              # Human review queue
│           ├── failures/            # Failure database triage
│           ├── compare/
│           │   ├── prompts/         # Prompt A/B comparison view
│           │   └── models/          # Model comparison view
│           ├── release/             # Release gate dashboard
│           └── bis/                 # Business Impact dashboard
│
└── scripts/
    ├── ci_regression.sh             # CI/CD release gate script
    ├── seed_golden_dataset.py       # Bootstrap initial test cases
    └── export_benchmark_report.py   # PDF/CSV report generator
```

---

## SECTION 5 — Golden Dataset

### Purpose

The Golden Dataset is the immutable ground-truth corpus that every benchmark run is measured against. It is not a test database. It is a curated, human-reviewed, versioned collection of exemplary queries and their expected pipeline outputs.

Every test case in the Golden Dataset represents one of:

1. A common production query that must always work correctly
2. A known edge case that has failed before and must not regress
3. A business-critical scenario where failure is unacceptable
4. A deliberate stress test for a pipeline component

### Golden Test Case Structure

Each golden test case captures the expected correct behavior at every phase of the APEX pipeline.

```
golden_test_case:
  id:                    UUID
  version:               Integer (incremented on any modification)
  created_at:            Timestamp
  updated_at:            Timestamp
  owner_id:              UUID (references team member)
  status:                ACTIVE | DEPRECATED | UNDER_REVIEW
  source:                MANUAL | PROMOTED_FROM_FAILURE | PROMOTED_FROM_FEEDBACK
  tags:                  Array[String]
  priority:              CRITICAL | HIGH | MEDIUM | LOW
  review_notes:          Text

  # Input
  query:                 Text
  user_context:          JSONB

  # Expected Planner Output (Phase 1)
  expected_intent:       String
  expected_entities:     JSONB
  expected_confidence:   String         # HIGH | MEDIUM | LOW

  # Expected Retriever Output (Phase 2)
  expected_retrieval_ids:  JSONB
  expected_retrieval_count: Integer
  expected_filter_keys:    JSONB

  # Expected Reasoner Output (Phase 3)
  expected_reasoning_confidence_min: Integer
  expected_key_findings:   JSONB

  # Expected Narrator Output (Phase 4)
  expected_json_schema:    JSONB
  expected_narrative_keywords: Array[String]
  expected_recommendation_type: String

  # Business Outcome
  expected_business_outcome: String
  expected_bis_category:     String     # VERY_HIGH | HIGH | MEDIUM | LOW
```

### Versioning

- Every modification to a golden test case **requires a version increment**.
- The old version is preserved as a historical record, not deleted.
- Benchmark results always reference the exact version of the test case they were scored against.
- This ensures a benchmark result from Sprint 3 can still be compared against Sprint 8 with full fidelity.

### Ownership

Every golden test case must have exactly one owner. Ownership responsibilities:

- Review and approve proposed modifications
- Verify the expected outputs remain accurate when the production system changes
- Decide when a test case should be deprecated

Ownership does not block others from running the test. It gates modifications to the expected outputs.

### Review Process

```
Proposed Change (by any developer)
          │
          ▼
Owner Reviews → Is the expected output still correct?
          │
     ┌────┴────┐
   Yes          No
     │          │
     ▼          ▼
 Approve    Request correction before approval
     │
     ▼
 Version incremented
 Change logged with reason
 Previous version preserved
```

### Growth Strategy — How the Golden Dataset Grows

The Golden Dataset is never manually invented at scale. It grows organically from three sources:

| Source | Mechanism | Review Required |
|---|---|---|
| Manual creation | Developer identifies a critical scenario | Owner approval |
| Production failure promotion | Low-score or user-rejected trace flagged | Engineer triage + owner approval |
| User feedback promotion | User thumbs-down on a response | Engineer review |

**Production-to-Golden Promotion Pipeline**:

```
Production Request
       │
       ▼
Layer 1 Telemetry Written
       │
       ▼
Automatic Failure Flagging
(grounding_score = LOW OR reasoning_confidence_pct < 40 OR user_feedback = negative)
       │
       ▼
Failure Database Entry Created
       │
       ▼
Developer Triages Failure
(root cause identified, fix applied)
       │
       ▼
Promote to Golden Dataset
(expected output = corrected expected, not actual failure output)
       │
       ▼
Regression Test Created
(prevents recurrence)
```

### Long-Term Scale

| Phase | Target Size | Strategy |
|---|---|---|
| Sprint 1 | 20–50 cases | Hand-authored by founders, covering all 8 intent types |
| 3 months | 100–200 cases | Supplemented by promoted failures |
| 6 months | 300–500 cases | Every production failure class represented |
| 1 year | 500–1,000 cases | Systematic coverage of account size, industry, deal stage variants |

---

## SECTION 6 — Benchmark Suite

### Architecture

A benchmark run is a structured execution where the APEX pipeline is invoked against every golden test case in a specified subset, and the outputs are scored against expected values.

```
BenchmarkRun
    │
    ├── run_type:    FULL | REGRESSION | PROMPT_COMPARE | MODEL_COMPARE | SINGLE
    ├── trigger:     MANUAL | CI | SCHEDULED | DEVELOPER
    ├── model_config: (model name, temperature, context window)
    ├── prompt_config: (prompt versions for Planner, Reasoner, Narrator)
    │
    └── BenchmarkResult (one per golden test case)
            ├── scores per metric
            ├── latency measurements
            ├── token counts
            └── pass/fail verdict
```

### Benchmark Groups

#### Group 1: Planner Benchmarks

**Purpose**: Verify the intent classification and entity extraction phase.  
**Dataset**: All golden test cases.  
**Frequency**: Every pull request, every release.

Tests:
- Intent classification accuracy (exact match against expected_intent)
- Entity extraction F1 (partial credit for correct keys with wrong values)
- Confidence calibration (does the planner confidence label match actual accuracy?)
- Ambiguous query handling (does low-confidence correctly trigger fallback?)
- Edge case intent coverage (all intent types must be present)

#### Group 2: Retriever Benchmarks

**Purpose**: Verify the data retrieval and filtering phase.  
**Dataset**: Golden test cases with expected_retrieval_ids populated.  
**Frequency**: Every release, after any change to data_retrieval_layer.py.

Tests:
- Retrieval precision (what fraction of retrieved records were expected?)
- Retrieval recall (what fraction of expected records were retrieved?)
- Filter accuracy (were the correct filter keys applied?)
- Empty retrieval handling (graceful degradation when no data matches)
- Large account handling (performance with 500+ records)

#### Group 3: Reasoner Benchmarks

**Purpose**: Verify the business reasoning and confidence scoring phase.  
**Dataset**: Golden test cases with expected_reasoning_confidence_min and expected_key_findings.  
**Frequency**: After any change to reasoning_engine.py or intelligence_layer.py.

Tests:
- Confidence floor compliance (actual confidence must meet minimum threshold)
- Key finding presence (required findings appear in reasoning output)
- SIP JSON schema validity (structured intelligence package matches contract)
- Recommendation type correctness (recommendation category matches expected)
- No hallucination of data not present in retrieved context

#### Group 4: Narrator Benchmarks

**Purpose**: Verify the response generation and formatting phase.  
**Dataset**: All golden test cases.  
**Frequency**: After any change to Narrator prompts or response_blueprint.py.

Tests:
- JSON schema conformance (does the final JSON match expected_json_schema?)
- Narrative keyword presence (required phrases appear)
- Recommendation actionability (contains concrete next steps)
- Streaming completeness (response did not truncate mid-section)
- Markdown structure validity (headers, sections in correct order)

#### Group 5: End-to-End Benchmarks

**Purpose**: Validate full pipeline integration.  
**Dataset**: Critical golden test cases (PRIORITY = CRITICAL or HIGH).  
**Frequency**: Every release.

Tests:
- Full pipeline success rate
- End-to-end latency against P90 threshold
- Business outcome alignment
- Grounding across the full response
- Overall score against release threshold

#### Group 6: Regression Benchmarks

**Purpose**: Detect regressions introduced by new code changes.  
**Dataset**: Core regression set — golden test cases tagged [regression]. Minimum 30 cases.  
**Frequency**: Every pull request. Must complete in < 3 minutes.

Design constraint: The regression benchmark must be fast. If it slows down, developers stop running it. Cap the regression set at cases that complete within 3 minutes total wall-clock time.

#### Group 7: Business Benchmarks

**Purpose**: Verify that APEX recommendations align with expected business strategies.  
**Dataset**: Golden test cases with expected_business_outcome populated.  
**Frequency**: Weekly, or before major releases.

Tests:
- Recommendation strategy alignment (EXPAND vs. DEFEND vs. RECOVER correctly selected)
- Deal stage awareness (recommendations appropriate for deal stage)
- Competitor handling (correct defensive vs. aggressive posture)
- Executive-appropriate language (no operational jargon in executive summaries)

#### Group 8: Latency Benchmarks

**Purpose**: Enforce performance SLAs.  
**Dataset**: Representative sample of 20 golden test cases spanning simple/complex queries.  
**Frequency**: Every release.

Thresholds:
- P50 total pipeline: < 4,000ms
- P90 total pipeline: < 8,000ms
- P99 total pipeline: < 15,000ms
- Planner phase: < 1,500ms
- Retriever phase: < 500ms
- Narrator phase: < 3,000ms

#### Group 9: Token & Cost Benchmarks

**Purpose**: Prevent token budget overruns.  
**Dataset**: All golden test cases.  
**Frequency**: Every release, after any prompt change.

Tests:
- Prompt token count per phase (alert if > 20% above baseline)
- Total token count per request (alert if > 10,000 tokens)
- Cost per request (alert if > $0.05 per request at current pricing)
- Token efficiency ratio (output tokens / input tokens — detects verbose prompts)

#### Group 10: Grounding Benchmarks

**Purpose**: Verify the AI is not hallucinating.  
**Dataset**: Golden test cases with well-defined expected retrieval.  
**Frequency**: Every release. After any LLM model upgrade.

Tests:
- Grounding score distribution (must be >= 85% HIGH, <= 5% LOW)
- Hallucination detection (claims in response not traceable to retrieved context)
- Source citation accuracy (when APEX cites data, it must be retrievable)

---

## SECTION 7 — Evaluation Metrics

### Metric Design Philosophy

Every metric must satisfy four criteria:

1. **Calculable without human input** (or clearly document where human judgment is required)
2. **Bounded** (a score must have a minimum and maximum so trends are meaningful)
3. **Stable** (the same output scored twice should produce the same score)
4. **Explainable** (an engineer must be able to explain why a score is 0.72 and not 0.85)

### Metric Catalog

---

#### M-01: Intent Accuracy

**What it measures**: Whether the Planner correctly identified the user's intent.

**Calculation**:
```
Intent Accuracy = (Correct Intent Classifications / Total Test Cases) × 100
```
Exact string match against expected_intent. No partial credit.

**Why exact match**: Intent drives the entire downstream pipeline. A partially correct intent will cause the retriever, reasoner, and narrator to execute incorrect logic. Partial credit masks pipeline failures.

**Target**: >= 95%

**Limitation**: Intent accuracy measures the label, not the intent resolution quality. A correct intent label with wrong entities will still score 100% on this metric. Always pair with Entity Accuracy (M-02).

---

#### M-02: Entity Accuracy (F1)

**What it measures**: Whether the Planner correctly extracted structured entities (account name, timeframe, deal stage, competitor, etc.).

**Calculation**:
```
Entity Precision = Correct Entities Extracted / Total Entities Extracted
Entity Recall    = Correct Entities Extracted / Total Entities Expected
Entity F1        = 2 × (Precision × Recall) / (Precision + Recall)
```
Correct = entity key matches AND entity value matches (case-insensitive).

**Target**: F1 >= 0.90

**Limitation**: Does not measure entity normalization quality. "Wipro Limited" and "Wipro" may be the same entity but score as a mismatch. Requires normalization logic in the scorer.

---

#### M-03: Retriever Precision

**What it measures**: What fraction of retrieved records were in the expected retrieval set.

**Calculation**:
```
Retriever Precision = |Retrieved ∩ Expected| / |Retrieved|
```

**Target**: >= 0.80

**Limitation**: Precision alone does not penalize returning too few records. Always pair with Recall (M-04).

---

#### M-04: Retriever Recall

**What it measures**: What fraction of expected records were actually retrieved.

**Calculation**:
```
Retriever Recall = |Retrieved ∩ Expected| / |Expected|
```

**Target**: >= 0.85

**Limitation**: High recall with low precision means the retriever is fetching too broadly. Monitor both metrics together.

---

#### M-05: Grounding Score

**What it measures**: Whether every factual claim in the AI response is traceable to the retrieved context.

**Calculation Method**: LLM-as-a-judge.

The evaluator LLM receives the retrieved context and the response, then classifies each factual claim as:
- GROUNDED: Supported by the context
- EXTRAPOLATED: A reasonable inference from the context
- HALLUCINATED: Not supported by the context

```
grounding_score = grounded_claims / total_claims
```

**Score Mapping**:
- grounding_score >= 0.95 → HIGH
- grounding_score >= 0.80 → MEDIUM
- grounding_score < 0.80 → LOW

**Target**: >= 90% of responses score HIGH.

**Limitation**: LLM-as-a-judge is susceptible to positional bias, verbosity bias, and self-consistency failure. Requires periodic human calibration. Never use as a sole release blocker without human confirmation.

---

#### M-06: Reasoning Confidence Calibration

**What it measures**: Whether the Reasoner's internal confidence score (reasoning_confidence_pct) is calibrated — do high-confidence responses actually score better on human evaluation?

**Calculation**:
```
For each score bracket (0-40%, 40-60%, 60-80%, 80-100%):
  Calibration Error = |Expected Human Score - Actual Mean Human Score|
```

**Target**: Calibration error < 0.5 points on the 1-5 human scale per bracket.

**Limitation**: Requires >= 50 human reviews per confidence bracket to produce stable statistics.

---

#### M-07: Narrative Structure Score

**What it measures**: Whether the Narrator's response conforms to the expected structural contract.

**Calculation**: Deterministic. No LLM required.

```python
def score_narrative_structure(response_json, expected_schema):
    required_sections = expected_schema.get("required_sections", [])
    present_sections  = [s for s in required_sections if s in response_json]
    section_score     = len(present_sections) / len(required_sections)

    required_keywords = expected_schema.get("required_keywords", [])
    narrative_text    = extract_text(response_json)
    present_keywords  = [k for k in required_keywords if k.lower() in narrative_text.lower()]
    keyword_score     = len(present_keywords) / len(required_keywords) if required_keywords else 1.0

    return (section_score * 0.7) + (keyword_score * 0.3)
```

**Target**: >= 0.95

**Limitation**: Structural conformance does not measure quality. A response can have all required sections and still contain poor content.

---

#### M-08: Recommendation Quality Score

**What it measures**: Whether the AI's recommendation is specific, actionable, and appropriate for the business context.

**Calculation Method**: LLM-as-a-judge. Rated on three dimensions (1-5 each):
- Specificity: Is the recommendation concrete, or generic boilerplate?
- Actionability: Can a sales rep act on this immediately?
- Context appropriateness: Does it reflect the actual deal/account situation?

```
Recommendation Score = mean(specificity, actionability, context_appropriateness)
```

**Target**: Composite >= 3.5 / 5.0

**Limitation**: The scoring model may score its own generated recommendations more favorably. Use a different model family as the judge than the one that generated the response wherever possible.

---

#### M-09: JSON Validity

**What it measures**: Whether the pipeline's structured JSON output conforms to the declared response contract.

**Calculation**: Deterministic.

```
JSON Validity = Valid JSON responses / Total responses
Schema Conformance = Responses passing JSON Schema validation / Total responses
```

**Target**: JSON Validity = 100%. Schema Conformance >= 98%.

**Limitation**: A syntactically valid JSON with semantically wrong values scores 100% on this metric.

---

#### M-10: Phase Latency (P50 / P90 / P99)

**What it measures**: Time distribution for each pipeline phase.

**Calculation**: From ObservabilitySpan records.

```sql
SELECT
    stage_name,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms) AS p50_ms,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY duration_ms) AS p90_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) AS p99_ms
FROM observability_spans
WHERE start_time >= NOW() - INTERVAL '24 hours'
GROUP BY stage_name;
```

**Target**: See Section 6, Latency Benchmarks.

**Limitation**: Percentile latencies are sensitive to sample size. P99 at 100 requests/day is not statistically meaningful. Report alongside sample count.

---

#### M-11: Token Usage & Estimated Cost

**What it measures**: Token consumption and associated cost per pipeline phase and per model.

**Calculation**:
```
Cost = (prompt_tokens × input_price_per_token) + (completion_tokens × output_price_per_token)
```

Price table maintained in core/metrics/cost.py. Must be updated when model pricing changes.

**Target**: Mean cost per request < $0.02 for local LLM deployments.

**Limitation**: Token counts from local Ollama do not map directly to cloud pricing. Cost projections for cloud models are estimates.

---

#### M-12: Business Value Score (Input to BIS)

**What it measures**: The estimated likelihood that this response will produce a measurable business outcome.

**Calculation**: See Section 13.5 — Business Impact Score. This metric feeds the BIS Engine rather than standing alone.

---

#### M-13: Execution Quality Score (EQS — Overall Score)

**What it measures**: A single composite score representing overall pipeline performance for a benchmark run.

**Calculation**:

```
EQS = (
    Intent Accuracy      × 0.20  +
    Entity F1            × 0.15  +
    Retriever Precision  × 0.10  +
    Retriever Recall     × 0.10  +
    Grounding Score      × 0.20  +
    Narrative Structure  × 0.10  +
    Recommendation Quality × 0.15
) × 100
```

Weights are configurable in core/metrics/composite.py. Revisit quarterly.

**Target**: EQS >= 78 for release approval.

**Limitation**: Composite scores obscure component failures. An EQS of 78 could reflect strong grounding but weak retrieval, or vice versa. Always inspect component metrics alongside EQS. EQS is a release signal, not a diagnosis tool.

---

## SECTION 8 — Human Evaluation

### Why Human Evaluation Cannot Be Eliminated

Automatic metrics are fast, cheap, and reproducible. They are also systematically wrong in predictable ways:

- Grounding scorers hallucinate verdicts
- Recommendation quality scorers favor verbose over precise
- Narrative structure scorers miss semantic incoherence
- No automatic metric measures "would a VP of Sales trust this?"

Human evaluation is the calibration layer that keeps automatic metrics honest.

### Reviewer Workflow

```
1. Log into Developer Console → Human Review Queue
2. Select next unreviewed benchmark result
3. View side-by-side panel:
   Left:  Original query + retrieved context (what the AI saw)
   Right: AI response (what the AI produced)
4. Score each rubric dimension (see below)
5. Add optional free-text notes for low scores
6. Submit → score saved to human_reviews table
7. System auto-flags cases where human score diverges significantly from EQS
```

### Scoring Rubrics

All dimensions are scored 1–5. Half-points are not permitted (forces a decision).

| Dimension | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **Accuracy** | Multiple factual errors | At least one factual error | Technically accurate but incomplete | Accurate and reasonably complete | Fully accurate, nothing missing |
| **Business Usefulness** | Does not advance the deal | Marginally relevant | Somewhat helpful | Clearly useful to a sales rep | Would directly change rep behavior |
| **Trust** | Contains hallucinations | Likely contains hallucinations | Uncertain — some claims unverifiable | Appears grounded but can't fully verify | Fully grounded, every claim traceable |
| **Readability** | Unreadable | Hard to scan | Readable but poorly structured | Clear and well-organized | Exceptionally clear and concise |
| **Actionability** | No next steps | Vague next steps | Generic next steps | Specific next steps | Specific + prioritized + named contact |
| **Recommendation Quality** | Wrong strategy for this deal | Off-target recommendation | Generic recommendation | Good recommendation for this context | Recommendation I would act on immediately |
| **Overall Satisfaction** | 1 | 2 | 3 | 4 | 5 |

### Rubric Anti-Ambiguity Rules

1. A score of 3 must be the default for "uncertain." Reviewers must choose between "good" and "bad" — 3 is not a safe middle ground.
2. If a reviewer scores any dimension 1 or 2, a free-text explanation is required.
3. If grounding_score from Layer 1 is HIGH but the reviewer scores Trust <= 2, this is automatically flagged for a second review.
4. If two reviewers score the same response with Overall Satisfaction >= 2 points apart, the case is escalated for discussion.

### Human Reviewer Calibration

New reviewers must calibrate against 10 pre-scored calibration cases before joining the review queue. Their first 20 live reviews are spot-checked for consistency. Calibration is repeated if a reviewer's mean score diverges more than 0.5 points from consensus.

---

## SECTION 9 — Regression Testing

### Regression Suite Design

The regression suite is the safety net for every code change. It must be:

- **Fast**: < 3 minutes total runtime
- **Stable**: Same baseline produces the same pass/fail verdict
- **Non-flaky**: No test in the regression suite passes intermittently

The regression suite runs a fixed subset of the Golden Dataset (the [regression] tagged cases, minimum 30) against the current pipeline state and compares against the last approved baseline.

### Pass/Fail Thresholds

| Metric | Block Release | Warn Only |
|---|---|---|
| Intent Accuracy | < 93% | < 97% |
| Entity F1 | < 0.85 | < 0.92 |
| Grounding Score (% HIGH) | < 80% | < 90% |
| JSON Schema Conformance | < 98% | < 100% |
| EQS vs. Baseline | Drop > 5 points | Drop > 2 points |
| P90 Latency | Increase > 20% | Increase > 10% |
| Critical Hallucination Count | > 0 | N/A |

A **Critical Hallucination** is defined as: a statement in the response that references a specific factual claim (dollar amount, deal stage, contact name) that is verifiably absent from the retrieved context.

### Release Gate Logic

```
ci_regression.sh execution flow:

1. Run regression benchmark suite (30+ golden cases)
2. Calculate all metrics above
3. Compare each metric against threshold table
4. If ANY BLOCK condition met → exit code 1 → CI fails → merge blocked
5. If WARN conditions met but no BLOCK → exit code 0 with warnings logged
6. If all thresholds pass → exit code 0 → release proceeds
```

### Rollback Strategy

If production monitoring (Layer 1) detects a degradation after release:

| Signal | Threshold | Action |
|---|---|---|
| Mean BIS drop | > 15% vs. 7-day average | Alert + human review |
| Grounding LOW rate spike | > 10% of requests | Automatic rollback trigger |
| User thumbs-down rate | > 20% in 1 hour | Automatic rollback trigger |
| P99 latency spike | > 30% above baseline | Alert + human decision |

Rollback is to the last git commit that passed the regression gate. The failed release is automatically added to the Failure Database with root cause category REGRESSION.

### Regression Reports

Every regression run produces a versioned report:

```
Regression Report v{N}
Run: {timestamp}
Commit: {git_sha}
Compared Against: {baseline_git_sha}

SUMMARY
  Status: PASS | WARN | FAIL
  EQS Change: +2.3 points
  Grounding Change: -1.2% (WARN)
  Latency Change: +340ms P90 (WARN)

METRIC TABLE
  [Full metric table with current, baseline, delta, status columns]

INDIVIDUAL FAILURES
  [List of specific golden test cases that regressed]

IMPROVEMENTS
  [List of golden test cases that improved]
```

---

## SECTION 10 — Prompt Evaluation

### Architecture

Prompt evaluation answers: "Which version of our Planner / Reasoner / Narrator prompt performs better?"

The evaluation is structured as a controlled A/B/C experiment where identical inputs are passed through different prompt versions and outputs are scored independently.

### Prompt Benchmark Design

```
PromptBenchmarkRun {
  id:               UUID
  pipeline_phase:   PLANNER | REASONER | NARRATOR
  prompt_a_hash:    SHA256  ← references observability_prompts table
  prompt_b_hash:    SHA256
  prompt_c_hash:    SHA256 (optional)
  dataset_ids:      Array[UUID]
  status:           RUNNING | COMPLETE | FAILED
}

PromptBenchmarkResult {
  id:               UUID
  run_id:           UUID
  golden_id:        UUID
  prompt_hash:      SHA256
  intent_accuracy:  Float
  entity_f1:        Float
  grounding_score:  Float
  latency_ms:       Integer
  prompt_tokens:    Integer
  completion_tokens: Integer
  estimated_cost:   Decimal
  eqs:              Float
}
```

### Comparison Report Structure

```
Prompt Comparison Report
Phase: NARRATOR
Dataset: 45 golden test cases
Date: {timestamp}

┌──────────────────────┬──────────┬──────────┬──────────┐
│ Metric               │ Prompt A │ Prompt B │ Winner   │
├──────────────────────┼──────────┼──────────┼──────────┤
│ EQS                  │  76.4    │  81.2    │ B (+6.3%)│
│ Grounding (% HIGH)   │  88%     │  91%     │ B (+3pts)│
│ Recommendation Score │  3.4     │  3.7     │ B (+8.8%)│
│ P90 Latency          │ 3,200ms  │ 3,800ms  │ A (-19%) │
│ Prompt Tokens        │  1,840   │  2,210   │ A (-17%) │
│ Est. Cost / Request  │  $0.014  │  $0.019  │ A (-26%) │
│ Human Satisfaction   │  3.6     │  3.8     │ B (+5.6%)│
└──────────────────────┴──────────┴──────────┴──────────┘

RECOMMENDATION: Prompt B is superior on quality metrics.
At a cost premium of $0.005/request, the quality gain may justify
adoption if volume is < 10,000 requests/day.
```

### Decision Rules

No automatic promotion. A human must review every prompt comparison report and make a deliberate promotion decision. The report surfaces the trade-offs; the engineer makes the call.

---

## SECTION 11 — Model Evaluation

### Architecture

Model evaluation compares multiple LLMs against identical inputs from the Golden Dataset. Each model is evaluated in isolation on the same benchmark case, with the same prompt, same retrieved context, and same evaluation criteria. The only variable is the model.

### Supported Models

| Model Family | Priority | Notes |
|---|---|---|
| Llama 3.x (local) | Primary | Current production model |
| Qwen 2.5 (local) | Secondary | Strong code/structured output |
| DeepSeek V3 (local) | Tertiary | Strong reasoning |
| Mistral (local) | Tertiary | Fast, compact |
| Gemma 3 (local) | Tertiary | Google-optimized |
| OpenAI GPT-4o | Cloud benchmark | Cost baseline for comparison |
| Claude Sonnet | Cloud benchmark | Quality ceiling benchmark |

### Model Comparison Report

```
Model Comparison Report
Dataset: 30 golden test cases
Prompt: Narrator v3.2 (same across all models)

┌──────────────────────┬───────┬───────┬──────────┬──────────┬────────┐
│ Metric               │ Llama │ Qwen  │ DeepSeek │ Mistral  │ GPT-4o │
├──────────────────────┼───────┼───────┼──────────┼──────────┼────────┤
│ EQS                  │ 76.4  │ 78.1  │ 80.2     │ 72.3     │ 85.4   │
│ Grounding (% HIGH)   │ 88%   │ 86%   │ 91%      │ 82%      │ 94%    │
│ Recommendation Score │ 3.4   │ 3.6   │ 3.8      │ 3.1      │ 4.1    │
│ P90 Latency          │3,200ms│3,800ms│ 4,100ms  │ 2,100ms  │ 1,900ms│
│ Hallucination Rate   │ 4.2%  │ 3.8%  │ 2.1%     │ 6.4%     │ 1.2%  │
│ Est. Cost / Request  │ ~$0   │ ~$0   │ ~$0      │ ~$0      │ $0.035 │
└──────────────────────┴───────┴───────┴──────────┴──────────┴────────┘
```

---

## SECTION 12 — Failure Database

### Purpose

Every production failure that is captured, understood, and prevented from recurring is engineering ROI. The Failure Database transforms operational pain into architectural knowledge.

### Failure Sources

| Source | Trigger |
|---|---|
| Automatic (Layer 1) | grounding_score = LOW OR reasoning_confidence_pct < 40 |
| Automatic (Layer 1) | validation_passed = false |
| User feedback | Thumbs-down event from frontend |
| Benchmark failure | Golden test case produces score below threshold |
| Human review | Reviewer scores Overall Satisfaction <= 2 |
| Manual | Developer identifies failure during code review |

### Failure Record Schema

```
failure_database {
  id                UUID        PRIMARY KEY
  trace_id          UUID        REFERENCES observability_traces(trace_id)
  golden_id         UUID        REFERENCES golden_dataset(id) NULLABLE
  source            VARCHAR

  question          TEXT
  expected          TEXT
  actual            TEXT

  root_cause        VARCHAR     -- PLANNER | RETRIEVER | REASONER | NARRATOR | DATA | PROMPT | MODEL | UNKNOWN
  root_cause_detail TEXT
  severity          VARCHAR     -- CRITICAL | HIGH | MEDIUM | LOW

  status            VARCHAR     -- OPEN | IN_TRIAGE | FIXED | REGRESSION_ADDED | WONT_FIX | DUPLICATE
  resolution        TEXT
  resolution_commit VARCHAR
  resolution_date   TIMESTAMP

  regression_test_id UUID
  owner_id           UUID
  prevention_notes   TEXT
}
```

### Failure Lifecycle

```
OPEN
  │
  ▼ (engineer picks up)
IN_TRIAGE
  │
  ├─ Root cause identified
  ├─ Severity assessed
  │
  ▼ (fix applied)
FIXED
  │
  ├─ Resolution logged (commit SHA)
  ├─ Prevention notes written
  │
  ▼ (promote to prevent recurrence)
REGRESSION_ADDED
  (golden test case created, future regressions will be caught automatically)
```

### Severity Classification

| Severity | Definition | SLA |
|---|---|---|
| CRITICAL | Hallucination of a specific fact that could cause a wrong business decision | Fix in 24 hours |
| HIGH | Complete intent misclassification or retrieval failure for a common query | Fix before next release |
| MEDIUM | Quality degradation that makes the response less useful but not wrong | Fix within 2 sprints |
| LOW | Minor formatting issue or sub-optimal phrasing | Fix when convenient |

### Root Cause Taxonomy

| Root Cause | Description |
|---|---|
| PLANNER | Intent or entity extraction error |
| RETRIEVER | Incorrect data retrieved or filtered |
| REASONER | Reasoning engine produced incorrect confidence or recommendations |
| NARRATOR | Response format, structure, or grounding failure |
| DATA | Underlying CRM data was incorrect or missing |
| PROMPT | Prompt instruction was ambiguous or incorrect |
| MODEL | LLM-specific failure mode (hallucination, refusal, truncation) |
| UNKNOWN | Root cause not yet determined |

---

## SECTION 13 — Business Evaluation

### Metrics Tracked

These metrics are captured via ObservabilityBusinessMetric (Layer 1) and aggregated in Layer 2 dashboards.

| Metric | Data Source | Aggregation |
|---|---|---|
| Reports Generated | Layer 1 action_type = REPORT_GENERATED | Count per day/week |
| Reports Downloaded | Layer 1 action_type = REPORT_DOWNLOADED | Count per day/week |
| Recommendations Accepted | BIS Engine signal | Count + Rate |
| Recommendations Ignored | BIS Engine signal | Count + Rate |
| Emails Exported | Layer 1 action_type = EMAIL_EXPORTED | Count per day/week |
| Emails Sent | Layer 1 action_type = EMAIL_SENT | Count per day/week |
| Estimated Time Saved | BIS Engine calculation | Minutes per day/week |
| Estimated Revenue Influenced | BIS Engine calculation | $ per quarter |
| User Satisfaction | Human review mean scores | Weekly mean |
| Weekly Active Users | Session counts from Layer 1 | Unique users/week |
| Retention | Cohort analysis from session data | Weekly/Monthly |
| Adoption | Active users / Total licensed users | Percentage |
| Business Outcome Achieved | CRM update signals | Count per outcome type |

---

## SECTION 13.5 — Business Impact Score (BIS)

### The Core Problem BIS Solves

Standard AI evaluation frameworks measure proxy metrics — accuracy, precision, grounding, latency. These are engineering metrics. They answer "is the AI working correctly?" They do not answer "is the AI creating value for the customer?"

A response can score 90% on EQS — correct intent, correct retrieval, perfectly grounded, well-structured — and still be completely ignored by every sales rep who reads it. That response has zero business impact.

The Business Impact Score bridges AI quality metrics and real-world commercial outcomes.

**BIS answers**: "Did this AI recommendation lead to a measurable business action?"

### Business Impact Lifecycle

```
AI Recommendation Generated
           │
           ▼
  Viewed by User (Event: VIEWED)
           │
           ▼
  User Decision (Event: ACCEPTED | IGNORED | REJECTED)
           │
           ▼ (if accepted)
  Action Executed
  ┌─────────────────────────────────────┐
  │ EMAIL_SENT | MEETING_SCHEDULED      │
  │ OPPORTUNITY_UPDATED | NOTES_ADDED   │
  │ REPORT_DOWNLOADED | TASK_CREATED    │
  └─────────────────────────────────────┘
           │
           ▼
  CRM Outcome (if observable)
  ┌─────────────────────────────────────┐
  │ STAGE_ADVANCED | DEAL_WON           │
  │ RISK_MITIGATED | STAKEHOLDER_ADDED  │
  └─────────────────────────────────────┘
           │
           ▼
  Business Impact Score Calculated
  Category: VERY_HIGH | HIGH | MEDIUM | LOW | NO_IMPACT | UNKNOWN
           │
           ▼
  Trace Updated: bis_record_id linked
  (Layer 1 trace ↔ Layer 2 BIS bridge)
```

### Business Signal Taxonomy

#### Tier 1: Direct Business Actions (Highest Weight)

| Signal | Weight | Notes |
|---|---|---|
| DEAL_STAGE_ADVANCED | 0.30 | Strongest causal signal |
| DEAL_WON | 0.30 | Attribution is uncertain but recorded |
| RECOMMENDATION_ACCEPTED | 0.20 | Rep explicitly acted on recommendation |
| OPPORTUNITY_UPDATED | 0.15 | CRM change traceable to session |
| MEETING_SCHEDULED | 0.15 | Concrete next step created |

#### Tier 2: Engagement Actions (Medium Weight)

| Signal | Weight | Notes |
|---|---|---|
| EMAIL_SENT | 0.12 | Follow-through on a recommendation |
| REPORT_DOWNLOADED | 0.10 | Indicates utility |
| TASK_CREATED | 0.10 | Rep translated recommendation to action |
| NOTES_ADDED | 0.08 | Rep engaged with content enough to annotate |
| REPORT_EXPORTED | 0.08 | External sharing — high value signal |

#### Tier 3: Passive Engagement (Low Weight)

| Signal | Weight | Notes |
|---|---|---|
| RECOMMENDATION_VIEWED | 0.05 | Necessary but not sufficient |
| RECOMMENDATION_EXPANDED | 0.04 | Showed interest |
| RECOMMENDATION_COPIED | 0.04 | Used content somewhere |
| SESSION_RETURN | 0.03 | Rep came back, indicating value |

#### Negative Signals

| Signal | Weight | Notes |
|---|---|---|
| RECOMMENDATION_REJECTED | -0.10 | Explicit rejection |
| USER_FEEDBACK_NEGATIVE | -0.15 | Thumbs-down |
| NO_ACTION_24H | -0.05 | Viewed but nothing followed |

### BIS Scoring Formula

```python
def calculate_bis(signals: List[Signal], weights: Dict[str, float]) -> BISResult:
    """
    Modular, configurable BIS calculation.
    Weights are loaded from bis_weight_config table, not hardcoded.
    """
    raw_score = 0.0
    for signal in signals:
        weight = weights.get(signal.signal_type, 0.0)
        raw_score += weight * signal.confidence

    # Normalize to 0-100
    normalized = min(max(raw_score * 100, 0), 100)

    # Apply time decay (signals older than 14 days have reduced weight)
    time_decayed = apply_time_decay(normalized, signals)

    # Categorize
    category = categorize_bis(time_decayed)

    return BISResult(
        score=round(time_decayed, 2),
        category=category,
        contributing_signals=signals,
        weights_version=weights.get("_version")
    )

def categorize_bis(score: float) -> str:
    if score >= 80:   return "VERY_HIGH"
    if score >= 60:   return "HIGH"
    if score >= 35:   return "MEDIUM"
    if score >= 10:   return "LOW"
    if score > 0:     return "NO_IMPACT"
    return "UNKNOWN"
```

### BIS Configuration (Database-Driven)

Weights are stored in the database. Changing weights requires no deployment.

```sql
CREATE TABLE bis_weight_config (
    id            UUID PRIMARY KEY,
    version       INTEGER,
    is_active     BOOLEAN,
    config        JSONB,  -- {"DEAL_STAGE_ADVANCED": 0.30, ...}
    created_at    TIMESTAMP,
    created_by    UUID,
    notes         TEXT,
    CONSTRAINT single_active_config UNIQUE (is_active) WHERE (is_active = TRUE)
);
```

This allows business strategy adjustments without code changes or deployments.

### BIS × Layer 1 Trace Integration

Every ObservabilityTrace can optionally link to a BISRecord:

```sql
ALTER TABLE observability_traces
ADD COLUMN bis_record_id UUID REFERENCES bis_records(id);
```

This creates a single query path from raw telemetry to business impact:

```sql
SELECT
    t.trace_id,
    t.user_query,
    t.selected_intent,
    t.grounding_score,
    t.reasoning_confidence_pct,
    b.score AS bis_score,
    b.category AS bis_category
FROM observability_traces t
LEFT JOIN bis_records b ON t.bis_record_id = b.id
WHERE t.created_at >= NOW() - INTERVAL '7 days'
ORDER BY b.score DESC;
```

### BIS Productivity Estimates

| Activity | Estimated Time Saved | Confidence |
|---|---|---|
| Account summary generated | 45 minutes manual research avoided | MEDIUM |
| Stakeholder map generated | 30 minutes | MEDIUM |
| Email draft generated | 20 minutes | HIGH |
| Meeting agenda generated | 15 minutes | HIGH |
| Risk assessment generated | 60 minutes | LOW |
| Full account plan generated | 3-4 hours | LOW |

---

## SECTION 14 — Dashboards

Each dashboard is designed around one engineering question. If a dashboard requires more than one question to justify it, split it.

### Dashboard 1: Quality Dashboard

**Question**: Is pipeline accuracy improving over time?

**Primary Metrics**: EQS trend (rolling 30-day), Intent Accuracy trend, Grounding Score distribution (% HIGH / MEDIUM / LOW), Entity F1 trend, Human Satisfaction mean trend.

**Key Views**: Line charts for 90-day trends. Current week vs. last week comparison table. Red/amber/green status indicators vs. release threshold.

---

### Dashboard 2: Benchmark Dashboard

**Question**: How did the latest benchmark run perform vs. baseline?

**Primary Metrics**: Latest run EQS vs. previous EQS. Per-metric comparison table. Individual golden test case results. Regression cases that newly failed.

**Key Views**: Run comparison selector. Golden dataset pass/fail heatmap by benchmark group. Top 10 worst-performing test cases.

---

### Dashboard 3: Prompt Dashboard

**Question**: Which prompt version is most efficient?

**Primary Metrics**: EQS per prompt version, Latency per prompt version, Token count, Cost per request, Grounding rate.

**Key Views**: Side-by-side comparison table. Trade-off scatter plot (Quality vs. Cost vs. Latency). Prompt version history timeline.

---

### Dashboard 4: Model Dashboard

**Question**: Which model provides the best quality-cost-latency balance?

**Primary Metrics**: EQS per model, Hallucination rate, P90 Latency, Cost per request, Human satisfaction.

**Key Views**: Model comparison radar chart (5 dimensions). Cost-quality frontier (which models are Pareto-optimal?). Model-specific failure pattern analysis.

---

### Dashboard 5: Failure Dashboard

**Question**: What is currently broken and what is the triage status?

**Primary Metrics**: Open failures by severity. Failure rate trend. Mean time to resolution by severity. Root cause distribution. Failures promoted to Golden Dataset this month.

**Key Views**: Failure queue (sortable by severity, age, root cause). Failure detail panel. Promotion button (promote failure to golden dataset).

---

### Dashboard 6: Release Dashboard

**Question**: Is this build safe to release?

**Primary Metrics**: Regression suite pass/fail status (large green/red banner). All metric thresholds with current values. Comparison vs. last released build. Human review approval status.

**Key Views**: Go / No-Go decision display. Blocking issue list. Warning issue list. Release history timeline.

---

### Dashboard 7: Business Dashboard

**Question**: What is our average Business Impact Score this week?

**Primary Metrics**: Mean BIS (weekly). BIS distribution. Recommendation Acceptance Rate trend. Total estimated time saved. Estimated revenue influenced. Top performing recommendation types.

**Key Views**: BIS funnel (recommendations generated → viewed → accepted → action → CRM outcome). Acceptance rate by recommendation category. User engagement heat map.

---

### Dashboard 8: Trend Dashboard

**Question**: How are all metrics shifting over time?

**Primary Metrics**: All key metrics over configurable windows (7d / 30d / 90d / 1 year).

**Key Views**: Multi-metric overlay chart. Anomaly annotations (releases, model changes, prompt changes marked on timeline). Correlation view. Quarterly summary table.

---

## SECTION 15 — Release Pipeline

### Complete Release Workflow

```
Developer writes code change
        │
        ▼
Local Benchmark Run (developer console)
   - Run regression benchmark subset locally
   - Inspect any failures before committing
        │
        ▼
Pull Request Created
        │
        ▼
CI — Automated Regression Suite
   - Full regression benchmark runs (~30 cases)
   - Must complete in < 3 minutes
   - Exit code 1 on any BLOCK condition → PR merge blocked
        │
        ▼ (CI passes)
Prompt Comparison (if prompts changed)
   - Benchmark new prompt version against current
   - Generate comparison report
   - Developer reviews trade-offs and makes promotion decision
        │
        ▼ (if model changed)
Model Comparison
   - Benchmark new model against current on full dataset
   - Human reviews model comparison report
        │
        ▼
Human Review
   - Reviewer evaluates 10+ benchmark results from this run
   - Must achieve mean Overall Satisfaction >= 3.5
   - Reviewer signs off
        │
        ▼
Release Approval
   - EQS >= 78
   - All BLOCK thresholds passed
   - Human sign-off received
        │
        ▼
Deploy to Production
        │
        ▼
Post-Deploy Monitoring (Layer 1)
   - Monitor grounding_score distribution
   - Monitor P90 latency
   - Monitor BIS for first 24 hours
        │
        ▼
Production Feedback Collection
   - User thumbs-up/down tracked
   - Business signal events collected
   - Failures auto-flagged to Failure Database
        │
        ▼
Golden Dataset Update
   - New failures promoted as regression tests
   - Dataset grows by ~5-10 cases per release cycle
```

---

## SECTION 16 — Database Design

All Layer 2 tables live in the same PostgreSQL database as Layer 1, using a consistent naming convention: `eval_*` prefix.

```sql
-- ─────────────────────────────────────────────────
-- GOLDEN DATASET
-- ─────────────────────────────────────────────────
CREATE TABLE eval_golden_dataset (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version                     INTEGER NOT NULL DEFAULT 1,
    status                      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    source                      VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
    priority                    VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    tags                        TEXT[] DEFAULT '{}',
    owner_id                    UUID NOT NULL,

    query                       TEXT NOT NULL,
    user_context                JSONB DEFAULT '{}',

    expected_intent             VARCHAR(100) NOT NULL,
    expected_entities           JSONB DEFAULT '{}',
    expected_confidence         VARCHAR(10) DEFAULT 'HIGH',

    expected_retrieval_ids      JSONB DEFAULT '{}',
    expected_retrieval_count    INTEGER,
    expected_filter_keys        JSONB DEFAULT '{}',

    expected_reasoning_confidence_min INTEGER DEFAULT 60,
    expected_key_findings       JSONB DEFAULT '{}',

    expected_json_schema        JSONB DEFAULT '{}',
    expected_narrative_keywords TEXT[] DEFAULT '{}',
    expected_recommendation_type VARCHAR(100),

    expected_business_outcome   VARCHAR(100),
    expected_bis_category       VARCHAR(20),

    review_notes                TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_golden_status   ON eval_golden_dataset(status);
CREATE INDEX idx_golden_priority ON eval_golden_dataset(priority);
CREATE INDEX idx_golden_intent   ON eval_golden_dataset(expected_intent);
CREATE INDEX idx_golden_tags     ON eval_golden_dataset USING GIN(tags);


-- ─────────────────────────────────────────────────
-- EVALUATION RUNS
-- ─────────────────────────────────────────────────
CREATE TABLE eval_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type            VARCHAR(30) NOT NULL,
    trigger             VARCHAR(20) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    model_name          VARCHAR(100),
    model_version       VARCHAR(50),
    prompt_versions     JSONB DEFAULT '{}',
    backend_git_commit  VARCHAR(40),
    golden_tag_filter   TEXT[],
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_by          UUID,
    notes               TEXT
);

CREATE INDEX idx_eval_runs_status ON eval_runs(status);
CREATE INDEX idx_eval_runs_type   ON eval_runs(run_type);
CREATE INDEX idx_eval_runs_commit ON eval_runs(backend_git_commit);


-- ─────────────────────────────────────────────────
-- BENCHMARK RESULTS (per golden case per run)
-- ─────────────────────────────────────────────────
CREATE TABLE eval_benchmark_results (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                      UUID NOT NULL REFERENCES eval_runs(id),
    golden_id                   UUID NOT NULL REFERENCES eval_golden_dataset(id),
    golden_version              INTEGER NOT NULL,
    trace_id                    UUID,

    intent_match                BOOLEAN,
    entity_precision            DECIMAL(5,4),
    entity_recall               DECIMAL(5,4),
    entity_f1                   DECIMAL(5,4),
    planner_confidence          VARCHAR(10),

    retriever_precision         DECIMAL(5,4),
    retriever_recall            DECIMAL(5,4),
    retrieval_count_actual      INTEGER,

    json_valid                  BOOLEAN,
    json_schema_conformant      BOOLEAN,
    narrative_structure_score   DECIMAL(5,4),
    narrative_keyword_score     DECIMAL(5,4),

    grounding_score             DECIMAL(5,4),
    grounding_category          VARCHAR(10),
    recommendation_score        DECIMAL(5,4),

    total_latency_ms            INTEGER,
    planner_latency_ms          INTEGER,
    retriever_latency_ms        INTEGER,
    narrator_latency_ms         INTEGER,
    prompt_tokens               INTEGER,
    completion_tokens           INTEGER,
    estimated_cost_usd          DECIMAL(10,6),

    eqs                         DECIMAL(5,2),
    pass_fail                   VARCHAR(10),

    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_benchmark_run       ON eval_benchmark_results(run_id);
CREATE INDEX idx_benchmark_golden    ON eval_benchmark_results(golden_id);
CREATE INDEX idx_benchmark_pass_fail ON eval_benchmark_results(pass_fail);


-- ─────────────────────────────────────────────────
-- HUMAN REVIEWS
-- ─────────────────────────────────────────────────
CREATE TABLE eval_human_reviews (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    benchmark_result_id     UUID REFERENCES eval_benchmark_results(id),
    trace_id                UUID,
    reviewer_id             UUID NOT NULL,
    review_type             VARCHAR(20) DEFAULT 'BENCHMARK',

    accuracy_score          SMALLINT NOT NULL CHECK (accuracy_score BETWEEN 1 AND 5),
    business_usefulness     SMALLINT NOT NULL CHECK (business_usefulness BETWEEN 1 AND 5),
    trust_score             SMALLINT NOT NULL CHECK (trust_score BETWEEN 1 AND 5),
    readability_score       SMALLINT NOT NULL CHECK (readability_score BETWEEN 1 AND 5),
    actionability_score     SMALLINT NOT NULL CHECK (actionability_score BETWEEN 1 AND 5),
    recommendation_quality  SMALLINT NOT NULL CHECK (recommendation_quality BETWEEN 1 AND 5),
    overall_satisfaction    SMALLINT NOT NULL CHECK (overall_satisfaction BETWEEN 1 AND 5),

    notes                   TEXT,
    flags                   TEXT[],
    time_spent_seconds      INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_human_reviews_reviewer  ON eval_human_reviews(reviewer_id);
CREATE INDEX idx_human_reviews_benchmark ON eval_human_reviews(benchmark_result_id);


-- ─────────────────────────────────────────────────
-- FAILURE DATABASE
-- ─────────────────────────────────────────────────
CREATE TABLE eval_failure_database (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID,
    golden_id               UUID REFERENCES eval_golden_dataset(id),
    source                  VARCHAR(30) NOT NULL,

    question                TEXT NOT NULL,
    expected                TEXT,
    actual                  TEXT NOT NULL,

    root_cause              VARCHAR(20),
    root_cause_detail       TEXT,
    severity                VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',

    status                  VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    resolution              TEXT,
    resolution_commit       VARCHAR(40),
    resolution_date         TIMESTAMPTZ,

    regression_test_id      UUID REFERENCES eval_golden_dataset(id),
    owner_id                UUID,
    prevention_notes        TEXT,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_failure_status     ON eval_failure_database(status);
CREATE INDEX idx_failure_severity   ON eval_failure_database(severity);
CREATE INDEX idx_failure_root_cause ON eval_failure_database(root_cause);


-- ─────────────────────────────────────────────────
-- RELEASE HISTORY
-- ─────────────────────────────────────────────────
CREATE TABLE eval_release_history (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    release_version         VARCHAR(30) NOT NULL,
    backend_git_commit      VARCHAR(40) NOT NULL,
    run_id                  UUID REFERENCES eval_runs(id),
    status                  VARCHAR(20) NOT NULL,
    eqs_at_release          DECIMAL(5,2),
    approved_by             UUID,
    release_notes           TEXT,
    rollback_reason         TEXT,
    deployed_at             TIMESTAMPTZ,
    rolled_back_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_release_commit ON eval_release_history(backend_git_commit);
CREATE INDEX idx_release_status ON eval_release_history(status);


-- ─────────────────────────────────────────────────
-- PROMPT BENCHMARKS
-- ─────────────────────────────────────────────────
CREATE TABLE eval_prompt_benchmarks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_phase      VARCHAR(20) NOT NULL,
    prompt_hashes       JSONB NOT NULL,
    dataset_ids         UUID[],
    run_ids             JSONB,
    winner              VARCHAR(10),
    decision_notes      TEXT,
    created_by          UUID,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);


-- ─────────────────────────────────────────────────
-- MODEL BENCHMARKS
-- ─────────────────────────────────────────────────
CREATE TABLE eval_model_benchmarks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    models_tested       TEXT[],
    prompt_hash         VARCHAR(64),
    dataset_ids         UUID[],
    run_ids             JSONB,
    winner              VARCHAR(100),
    decision_notes      TEXT,
    created_by          UUID,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);


-- ─────────────────────────────────────────────────
-- BUSINESS IMPACT SCORE RECORDS
-- ─────────────────────────────────────────────────
CREATE TABLE bis_records (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id                UUID,
    user_id                 UUID,
    workspace_id            UUID,
    recommendation_type     VARCHAR(100),
    signal_events           JSONB DEFAULT '[]',
    weights_version         INTEGER,
    raw_score               DECIMAL(5,2),
    normalized_score        DECIMAL(5,2),
    category                VARCHAR(20),
    time_saved_est_minutes  INTEGER,
    revenue_influence_est   DECIMAL(12,2),
    calculation_notes       TEXT,
    calculated_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_bis_trace        ON bis_records(trace_id);
CREATE INDEX idx_bis_category     ON bis_records(category);
CREATE INDEX idx_bis_calculated   ON bis_records(calculated_at);
CREATE INDEX idx_bis_user         ON bis_records(user_id);


-- ─────────────────────────────────────────────────
-- BIS WEIGHT CONFIGURATION (Database-driven, no code deploy needed)
-- ─────────────────────────────────────────────────
CREATE TABLE bis_weight_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version     INTEGER NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT FALSE,
    config      JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    created_by  UUID,
    notes       TEXT,
    CONSTRAINT single_active_config UNIQUE (is_active) WHERE (is_active = TRUE)
);


-- ─────────────────────────────────────────────────
-- RETENTION POLICIES
-- ─────────────────────────────────────────────────
-- eval_benchmark_results: retain 1 year
-- eval_human_reviews:     retain 2 years (important training signal)
-- eval_failure_database:  retain indefinitely (historical knowledge)
-- eval_release_history:   retain indefinitely (compliance and audit)
-- bis_records:            retain 1 year
-- eval_golden_dataset:    retain indefinitely (source of truth)
```

---

## SECTION 17 — Developer Experience

### Developer Evaluation Console

The Developer Evaluation Console is the primary interface for developers working on the APEX pipeline. It provides fast, low-friction access to all evaluation capabilities.

### Core Capabilities

**1. Run Single Benchmark**  
Select a golden test case → Select pipeline mode (current / specific commit / specific prompt version) → Run → View side-by-side panel (query / expected / actual / scores).

**2. Run Complete Benchmark Suite**  
Select benchmark group → Select model and prompt versions → Run → Monitor progress with live metric updates → View full benchmark report on completion.

**3. Compare Prompts (A/B/C)**  
Select pipeline phase → Select Prompt A (current) and Prompt B (candidate) → Select dataset → Run Comparison → View side-by-side report with winner recommendation.

**4. Compare Models**  
Select models (multi-select) → Select benchmark dataset → Run → View model comparison report with radar chart and cost-quality table.

**5. Inspect Failures**  
View failure database with filters (severity, status, root cause, date) → Click failure → View detail (query / expected / actual / root cause) → Update status / Assign owner / Add resolution notes.

**6. Promote Failure to Golden Dataset**  
From failure detail view → Click Promote → Fill expected output (correct expected — NOT the failure output) + Priority + Owner + Tags → Submit.

**7. Generate Evaluation Report**  
Select run or date range → Select format (HTML / Markdown) → Generate → View complete evaluation report.

**8. Export Benchmark Report**  
Select format (CSV / JSON / PDF) → Export → Download structured benchmark data.

### CLI Interface (for CI/CD)

```bash
# Run regression suite
python -m apex_eval run --type regression --commit HEAD

# Compare prompts
python -m apex_eval compare-prompts \
  --phase narrator \
  --prompt-a sha256:abc123 \
  --prompt-b sha256:def456 \
  --dataset regression

# Generate release report
python -m apex_eval release-report --run-id {uuid} --output ./reports/

# Check release gate (Exit 0 = PASS, Exit 1 = FAIL)
python -m apex_eval gate-check --run-id {uuid}
```

---

## SECTION 18 — Future Enterprise Roadmap

> **Note**: The following capabilities are documented for architectural awareness only. None should be implemented before the MVP is stable and proven in production.

| Capability | Description | Complexity |
|---|---|---|
| **Continuous Nightly Evaluation** | Full benchmark run every night. Trends surfaced each morning. | Medium |
| **Canary Releases** | New pipeline version serves 5% of traffic. BIS and EQS compared in real time between canary and baseline. | High |
| **A/B Testing** | Different prompt or model versions randomly assigned to user cohorts. Statistical significance testing applied. | High |
| **Multi-Model Routing Evaluation** | Evaluate which queries should route to which model based on complexity, cost, and quality. | High |
| **Multi-Agent Evaluation** | Evaluate agent collaboration quality when APEX spawns sub-agents. Inter-agent grounding and consistency scoring. | Very High |
| **Memory Evaluation** | Measure whether user memory improves response relevance over time. | High |
| **Skills Evaluation** | If dynamic skill architecture is adopted, evaluate skill selection accuracy and inter-skill consistency. | High |
| **Cloud Benchmarking** | Run benchmark datasets against cloud-hosted APEX instances with real traffic profiles. | Medium |
| **Distributed Evaluation** | Parallel benchmark execution across multiple workers for 1,000+ case golden datasets. | Medium |
| **Prompt Registry Integration** | Version-controlled prompt registry with governance workflow and production promotion pipeline. | High |
| **ROI Analytics** | Connect BIS to actual CRM revenue data. Calculate true AI-attributed revenue. | Very High |
| **Executive KPI Dashboards** | C-suite dashboard: AI adoption, time saved, revenue influence across the organization. | Medium |
| **Forecast Accuracy** | Compare APEX deal health predictions against actual outcomes over time. Requires 6+ months of data. | High |
| **Cross-Account BIS Trends** | Identify which account types and deal profiles produce highest business impact from APEX. | Medium |

---

## SECTION 19 — Startup Roadmap

### Sprint 1: Foundation — Golden Dataset (Weeks 1–2)

**Goal**: Establish the evaluation ground truth.

- [ ] Design and migrate eval_golden_dataset PostgreSQL table
- [ ] Seed 30–50 golden test cases (manually authored, covering all 8 intent types)
- [ ] Build basic Golden Dataset CRUD API (FastAPI)
- [ ] Build minimal Next.js UI for viewing and editing golden test cases
- [ ] Define golden test case review workflow (promotion, versioning)
- [ ] Tag 30 cases as [regression] priority

**Exit Criteria**: 30+ golden test cases exist. Every intent type is covered. Regression subset identified.

---

### Sprint 2: Benchmark Runner (Weeks 3–4)

**Goal**: Be able to run a benchmark and see a score.

- [ ] Build core/runner.py — executes pipeline against golden cases, writes results
- [ ] Implement M-01 through M-09 metrics in core/metrics/
- [ ] Build eval_runs and eval_benchmark_results tables
- [ ] Build basic benchmark result viewer in Next.js
- [ ] Build ci_regression.sh — runs regression suite, exits with pass/fail
- [ ] Integrate CI script into GitHub Actions
- [ ] Implement core/replay/replayer.py — score existing Layer 1 traces

**Exit Criteria**: Running ci_regression.sh produces a pass/fail result in < 3 minutes.

---

### Sprint 3: Evaluation Dashboards (Weeks 5–6)

**Goal**: Visibility into quality trends and failures.

- [ ] Build Quality Dashboard (EQS trend, grounding trend, intent accuracy trend)
- [ ] Build Failure Dashboard (open failures, severity breakdown, triage queue)
- [ ] Build eval_failure_database table + CRUD API
- [ ] Build automatic failure flagging (low grounding, low confidence, thumbs-down)
- [ ] Build human review queue UI and scoring interface
- [ ] Build eval_human_reviews table
- [ ] Implement Failure → Golden Dataset promotion workflow

**Exit Criteria**: Failures are automatically flagged. Developers can triage failures and promote to golden dataset. Human review queue is operational.

---

### Sprint 4: Release Gates & BIS (Weeks 7–8)

**Goal**: Production quality assurance and business impact measurement.

- [ ] Implement release gate engine (core/release/gate_engine.py)
- [ ] Build Release Dashboard (go/no-go status, blocking issues, metric comparison)
- [ ] Implement BIS Engine (core/bis/bis_engine.py)
- [ ] Build bis_records and bis_weight_config tables
- [ ] Connect observability_traces to BIS via bis_record_id FK
- [ ] Build Business Impact Dashboard
- [ ] Implement BIS event ingestion API
- [ ] Build Prompt Comparison workflow (report generation)
- [ ] Build Model Comparison workflow (report generation)

**Exit Criteria**: Every release runs the gate check. BIS is calculated for all production traces. Business Dashboard shows weekly acceptance rate and estimated time saved.

---

### Post-Sprint 4: Ongoing Cadence

- Golden Dataset grows by 5–10 cases per release cycle
- Human review queue processes 20+ responses per week
- Prompt comparison runs before every prompt change
- Model evaluation runs quarterly or before major model upgrades
- Failure database reviewed weekly; all CRITICAL failures promoted to golden dataset

---

## SECTION 20 — Implementation Checklist

### Architecture
- [x] Layer 2 architecture defined
- [x] Technology stack constraints documented
- [x] Folder structure specified
- [x] Database schema designed (eval_* table prefix)
- [x] Integration with Layer 1 observability documented (bis_record_id FK, trace replay)

### Golden Dataset
- [x] Golden test case schema designed (all 4 pipeline phases covered)
- [x] Versioning strategy defined
- [x] Ownership model defined
- [x] Review process defined
- [x] Production failure → golden dataset promotion pipeline designed
- [x] Growth strategy documented (20 → 1,000 cases over 1 year)

### Evaluation Metrics
- [x] M-01: Intent Accuracy
- [x] M-02: Entity Accuracy (F1)
- [x] M-03: Retriever Precision
- [x] M-04: Retriever Recall
- [x] M-05: Grounding Score (LLM-as-judge)
- [x] M-06: Reasoning Confidence Calibration
- [x] M-07: Narrative Structure Score (deterministic)
- [x] M-08: Recommendation Quality Score (LLM-as-judge)
- [x] M-09: JSON Validity (deterministic)
- [x] M-10: Phase Latency P50/P90/P99
- [x] M-11: Token Usage & Estimated Cost
- [x] M-12: Business Value Score (BIS input)
- [x] M-13: Execution Quality Score (EQS — weighted composite)

### Benchmark Suite
- [x] Group 1: Planner Benchmarks
- [x] Group 2: Retriever Benchmarks
- [x] Group 3: Reasoner Benchmarks
- [x] Group 4: Narrator Benchmarks
- [x] Group 5: End-to-End Benchmarks
- [x] Group 6: Regression Benchmarks (< 3 min, CI-integrated)
- [x] Group 7: Business Benchmarks
- [x] Group 8: Latency Benchmarks (P50/P90/P99 thresholds)
- [x] Group 9: Token & Cost Benchmarks
- [x] Group 10: Grounding Benchmarks

### Human Evaluation
- [x] Reviewer workflow designed (7-step queue process)
- [x] Scoring rubrics defined (7 dimensions, 1-5 scale, behavioral anchors)
- [x] Anti-ambiguity rules specified (score 3 = default uncertain, mandatory notes at 1-2)
- [x] Reviewer calibration process designed (10 calibration cases)

### Regression Testing
- [x] Pass/fail thresholds defined (BLOCK and WARN levels)
- [x] Release gate logic specified (exit codes for CI)
- [x] Rollback strategy designed (automatic trigger conditions)
- [x] Regression report format specified

### Business Impact Score
- [x] BIS lifecycle designed (Recommendation → Viewed → Accepted → Action → CRM → Score)
- [x] Business signal taxonomy defined (Tier 1 / 2 / 3 / Negative)
- [x] BIS formula specified (configurable, database-driven weights)
- [x] Layer 1 trace integration specified (bis_record_id FK)
- [x] Productivity estimates documented
- [x] BIS Dashboard specified (funnel view, acceptance rate, time saved)

### Failure Database
- [x] Failure sources defined (6 sources: automatic, user, benchmark, review, manual)
- [x] Failure record schema designed
- [x] Failure lifecycle documented (OPEN → IN_TRIAGE → FIXED → REGRESSION_ADDED)
- [x] Severity classification defined (CRITICAL 24h SLA → LOW)
- [x] Root cause taxonomy defined (8 categories)

### Dashboards
- [x] Quality Dashboard (accuracy trend)
- [x] Benchmark Dashboard (run vs. baseline)
- [x] Prompt Dashboard (version comparison)
- [x] Model Dashboard (quality-cost-latency balance)
- [x] Failure Dashboard (triage status)
- [x] Release Dashboard (go/no-go)
- [x] Business Dashboard (BIS and business metrics)
- [x] Trend Dashboard (all metrics over time)

### Release Pipeline
- [x] Complete release workflow documented (11 stages)
- [x] CI gate script specified
- [x] Prompt comparison workflow specified
- [x] Model comparison workflow specified
- [x] Post-deploy monitoring specified

### Developer Experience
- [x] Developer console capabilities defined (8 core capabilities)
- [x] CLI interface specified (4 primary commands)
- [x] Report generation specified (HTML / Markdown / CSV / JSON / PDF)

### Roadmap
- [x] 4-sprint startup roadmap with exit criteria
- [x] Enterprise future roadmap documented (14 capabilities)
- [x] No enterprise features included in MVP

---

> *This document is the authoritative architecture specification for APEX Layer 2.*  
> *Implementation decisions that deviate from this specification require a documented architectural decision record (ADR).*  
> *Layer 1 reference: `backend/observability/recorder.py`, `backend/models/observability_models.py`*
