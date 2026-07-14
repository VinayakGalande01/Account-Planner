# APEX — Layer 2: Evaluation Platform & Continuous Quality Framework

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
