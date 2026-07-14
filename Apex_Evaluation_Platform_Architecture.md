# APEX — Evaluation Platform & Continuous Quality Framework (MVP Refinement)

> **Document Type**: Architecture Specification  
> **Status**: MVP Refinement  
> **Domain**: Layer 2 — Continuous Quality & Evaluation  

This document specifies the complete architecture for the APEX Evaluation Platform.

The purpose of Layer 2 is NOT to improve the AI. Its purpose is to measure, benchmark, compare, validate, and continuously improve every change made to the APEX pipeline.

This layer builds directly on top of Layer 1 (Observability).
Layer 1 answers: *"What happened?"*
Layer 2 answers: *"Was it better?"*

---

## SECTION 1 — Executive Summary

APEX already contains a deterministic multi-phase pipeline:
`Planner` → `Retriever` → `Reasoner` → `Narrator`

Layer 1 captures telemetry. Layer 2 consumes that telemetry to evaluate:
- Prompt quality
- Retrieval quality
- Reasoning quality
- Grounding
- Latency
- Cost
- Business usefulness
- User satisfaction
- Release quality

Layer 2 must never modify production responses. It only evaluates them as an out-of-band observer.

---

## SECTION 2 — Core Engineering Principles

Follow these principles strictly:
1. Evaluation must never affect production execution latency or reliability.
2. Every AI change must be measurable.
3. Every failed production request should become a future benchmark.
4. Every benchmark should be reproducible.
5. Human feedback is the source of truth.
6. Automatic metrics assist humans. They never replace them.
7. Evaluation must evolve independently from the AI pipeline.
8. Simple evaluation is preferred over complicated scoring systems.

---

## SECTION 3 — MVP Objectives

Design an Evaluation Platform that allows APEX to answer:
- Did Prompt V2 outperform Prompt V1?
- Did Model A outperform Model B?
- Did retrieval improve?
- Did recommendation quality improve?
- Did latency increase?
- Did grounding decrease?
- Did users actually like the output?
- Should this build be released?

---

## SECTION 4 — Architecture

Design an evaluation architecture suitable for a 2 Founder Team prioritizing operational simplicity.

**Tech Stack**: FastAPI, PostgreSQL, Next.js
**Exclusions**: No Kubernetes, No Redis, No Kafka, No MLFlow, No LangSmith, No external evaluation platforms.
Architecture must be PostgreSQL-first.

### Folder Structure
```text
apex-eval/
├── backend/
│   ├── api/                 # FastAPI routes for dashboards & triggers
│   ├── core/
│   │   ├── runner.py        # Benchmark execution engine
│   │   ├── metrics.py       # Scoring algorithms
│   │   └── bis_engine.py    # Business Impact calculation
│   ├── db/                  # PostgreSQL models
│   └── workers/             # Background benchmark jobs
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboards/  # Quality, BIS, Prompt views
│   │   │   ├── datasets/    # Golden dataset management
│   │   │   └── failures/    # Failure triage queue
│   │   └── components/
└── scripts/
    └── ci_regression.sh     # Release gate script
```

---

## SECTION 5 — Golden Dataset

The Golden Dataset is the immutable source of truth for pipeline correctness.

- **Structure**:
  - `Gold Queries`
  - `Expected Intent`, `Expected Entities`, `Expected Retrieval`
  - `Expected JSON`, `Expected Narrative`, `Expected Recommendation`
  - `Expected Business Outcome`
- **Versioning**: Every test case requires a version increment upon modification.
- **Ownership**: Every test case must be assigned an owner.
- **Review Process**: Modifications to expected outputs require a secondary peer review.
- **Growth Strategy**: Production failures (low BIS, user thumbs-down) are reviewed and promoted into the Golden Dataset via the Developer Console.

---

## SECTION 6 — Benchmark Suite

Benchmarks are grouped to evaluate specific components or end-to-end behavior:
- **Planner Benchmarks**: Tests intent classification and entity extraction.
- **Retriever Benchmarks**: Tests precision and recall of semantic search.
- **Reasoner Benchmarks**: Tests multi-perspective business logic.
- **Narrator Benchmarks**: Tests structural constraints and formatting.
- **End-to-End Benchmarks**: Tests the complete pipeline flow.
- **Regression Benchmarks**: Core set of tests that must pass before any release.
- **Business Benchmarks**: Tests alignment with expected business strategies.
- **Latency / Token / Grounding Benchmarks**: Non-functional validations.

---

## SECTION 7 — Evaluation Metrics

Automatic metrics serve to scale evaluation.

- **Planner Accuracy**: Exact match for intent + F1 score for entity extraction.
- **Retriever Precision / Recall**: Overlap percentage between retrieved chunks and expected chunks.
- **Grounding**: LLM-as-a-judge score evaluating if the response is strictly supported by context.
- **Reasoning Confidence**: Delta between internal confidence scores and baseline expectations.
- **Narrative Structure**: Deterministic validation of JSON schemas and Markdown structures.
- **Recommendation Quality**: LLM-as-a-judge evaluation of actionability.
- **Latency**: P50/P90/P99 ms duration per phase.
- **Token Usage / Cost**: Exact count mapped to model pricing.
- **Business Value**: Estimated downstream value.
- **Execution Quality (Overall Score)**: Weighted combination of the above.

*Limitations*: LLM metrics are susceptible to drift and bias, requiring periodic human calibration.

---

## SECTION 8 — Human Evaluation

Human reviewers calibrate the platform.

**Reviewer Workflow**: Log into console → Select evaluation queue → View Query/Context/Output side-by-side → Submit scores via rubric.

**Scoring Rubrics (1-5 Scale)**:
- **Accuracy**: Is it factually correct?
- **Business Usefulness**: Does it advance the deal?
- **Trust**: Are there hallucinations?
- **Readability**: Is it concise and well-formatted?
- **Actionability**: Are next steps explicit?
- **Recommendation Quality**: Aligns with strategic goals?
- **Overall Satisfaction**: Pass/Fail aggregate.

---

## SECTION 9 — Regression Testing

Every release must automatically execute the complete benchmark suite.

- **Pass Thresholds**: E.g., 95% Planner Accuracy, 0 Critical Hallucinations.
- **Fail Thresholds**: E.g., >5% latency degradation, Intent regression.
- **Release Gates**: CI script blocks merges on threshold failures.
- **Rollback Strategy**: Automatic rollback triggered if post-deploy monitoring detects a 10% drop in BIS.
- **Regression Reports**: Generates version comparison diffs automatically on PRs.

---

## SECTION 10 — Prompt Evaluation

Compare Prompts (A/B/C) systematically.

Compare based on:
- Quality (Reasoning accuracy, formatting adherence)
- Latency (Time to first token)
- Grounding (Hallucination rate)
- Cost & Tokens
- Execution Quality
- Business Value

**Output**: Tabular comparison reports highlighting trade-offs (e.g., Prompt B is 5% more accurate but uses 20% more tokens).

---

## SECTION 11 — Model Evaluation

Compare foundational models using identical benchmark datasets.

**Models**: Llama, Qwen, DeepSeek, Mistral, Gemma, OpenAI, Claude.
**Compare**:
- Latency
- Quality
- Grounding
- Cost
- Hallucination
- Business usefulness

---

## SECTION 12 — Failure Database

Every production failure becomes future knowledge.

- **Store**: Question, Expected, Actual, Root Cause, Severity, Resolution, Regression Test link, Owner, Status, Future Prevention notes.
- **Lifecycle**:
  1. Flagged via low BIS or feedback.
  2. Triaged by an engineer (Root Cause identified).
  3. Fixed in code/prompt.
  4. Promoted to Golden Dataset to prevent regression.

---

## SECTION 13 — Business Evaluation

Measure product value empirically.

**Metrics**:
- Reports Generated / Downloaded
- Recommendations Accepted / Ignored
- Emails Exported / Sent
- Time Saved
- Revenue Influenced
- User Satisfaction
- Weekly Active Users (WAU)
- Retention & Adoption
- Business Outcome achieved

---

## SECTION 13.5 — Business Impact Score (BIS)

Traditional frameworks measure technical quality. The Business Impact Score measures if the AI created value for the customer.

**Objectives**: Measure downstream effect. Was it accepted? Was CRM updated? Did the deal progress?

**Business Impact Lifecycle**:
AI Recommendation → Viewed by User → Accepted/Ignored → Action Executed → CRM Updated → Opportunity Progressed → Business Outcome Recorded → Business Impact Score Calculated.

**Suggested Business Signals**:
- *User Engagement*: Viewed, Expanded, Copied, Downloaded, Exported.
- *User Actions*: Accepted, Rejected, Task Created, Meeting Scheduled, Notes Added.
- *CRM Outcomes*: Stage Advanced, Revenue Increased, Risk Mitigated.
- *Productivity Metrics*: Estimated Time Saved, Manual Research Avoided. Include Confidence and Calculation Method.

**Business Impact Categories**:
VERY HIGH, HIGH, MEDIUM, LOW, NO IMPACT, UNKNOWN.

**Business Impact Formula**:
Modular scoring engine combining weighted signals (e.g., Acceptance, CRM Update, User Feedback). Must remain configurable without application code changes.

**Business Impact Dashboard**:
Track Acceptance/Rejection rates, Total exports, Time saved, Revenue influence, Average BIS, and best/worst performing recommendation types across Daily/Weekly/Monthly trends.

**Trace Integration**:
Every observability trace must optionally reference its BIS record, creating complete visibility from reasoning to business value.

---

## SECTION 14 — Dashboards

Each dashboard answers one engineering question.

- **Quality Dashboard**: Is accuracy improving?
- **Benchmark Dashboard**: How did the latest run perform?
- **Prompt Dashboard**: Which prompt is most efficient?
- **Model Dashboard**: Which model provides the best ROI?
- **Failure Dashboard**: What is currently breaking?
- **Release Dashboard**: Is this build safe?
- **Business Dashboard**: What is our average BIS this week?
- **Trend Dashboard**: How are metrics shifting over time?

---

## SECTION 15 — Release Pipeline

**Workflow**:
1. Developer
2. Local Benchmark
3. Regression Suite
4. Prompt Comparison
5. Model Comparison
6. Human Review
7. Approval
8. Production
9. Production Monitoring
10. Feedback
11. Golden Dataset Update

---

## SECTION 16 — Database Design

PostgreSQL schema concept:

```sql
-- Golden Dataset
CREATE TABLE golden_dataset (
    id UUID PRIMARY KEY,
    query TEXT,
    expected_intent VARCHAR,
    expected_entities JSONB,
    expected_retrieval JSONB,
    expected_business_outcome VARCHAR,
    expected_recommendation TEXT,
    expected_json JSONB,
    expected_narrative TEXT,
    version INT,
    owner_id UUID
);

-- Evaluation Runs
CREATE TABLE evaluation_runs (
    id UUID PRIMARY KEY,
    run_type VARCHAR,
    model_version VARCHAR,
    prompt_version VARCHAR,
    status VARCHAR
);

-- Benchmark Results
CREATE TABLE benchmark_results (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES evaluation_runs,
    golden_id UUID REFERENCES golden_dataset,
    latency_ms INT,
    token_usage INT,
    cost DECIMAL,
    grounding_score DECIMAL,
    overall_score DECIMAL
);

-- Failure Database
CREATE TABLE failures (
    id UUID PRIMARY KEY,
    trace_id UUID,
    question TEXT,
    expected TEXT,
    actual TEXT,
    root_cause TEXT,
    severity VARCHAR,
    status VARCHAR,
    owner_id UUID
);

-- Human Reviews
CREATE TABLE human_reviews (
    id UUID PRIMARY KEY,
    benchmark_id UUID REFERENCES benchmark_results,
    accuracy_score INT,
    business_usefulness INT,
    trust INT,
    readability INT
);
```
*(Additional tables: `release_history`, `prompt_benchmarks`, `model_benchmarks`, `business_evaluations` following similar relational structures with appropriate indexes and retention policies).*

---

## SECTION 17 — Developer Experience

**Developer Evaluation Console**:
- Run single benchmark
- Run complete benchmark suite
- Compare prompts side-by-side
- Compare models
- Inspect failures
- Promote failures into golden dataset
- Generate evaluation reports
- Export benchmark reports

---

## SECTION 18 — Future Enterprise Roadmap

*(Documentation Only)*
- Continuous nightly evaluation
- Canary releases
- A/B Testing
- Multi-model routing evaluation
- Multi-agent evaluation
- Memory evaluation
- Skills evaluation
- Cloud benchmarking
- Distributed evaluation
- Prompt Registry integration

---

## SECTION 19 — Startup Roadmap

- **Sprint 1**: Golden Dataset
- **Sprint 2**: Benchmark Runner
- **Sprint 3**: Evaluation Dashboard
- **Sprint 4**: Release Gates
- **Future**: Enterprise Evaluation Platform

---

## SECTION 20 — Final Deliverables

- [x] Complete Architecture
- [x] Folder Structure
- [x] Database Schema
- [x] Evaluation Metrics
- [x] Golden Dataset Design
- [x] Benchmark Strategy
- [x] Failure Database
- [x] Developer Console
- [x] Dashboard Wireframes (Conceptualized in UI requirements)
- [x] Release Workflow
- [x] Startup Roadmap
- [x] Enterprise Roadmap
- [x] Implementation Checklist
