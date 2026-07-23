"""
INTELLIGENCE PATTERN MODELS (patterns/models.py)
Dataclass definitions for domain intelligence detection rules:
Pattern definitions, compiled Findings, and overall IntelligenceBrief summaries.
"""

# --- SECTION 1: Base Imports & Pattern Rule Definition ---
# Defines declarative Pattern dataclasses for matching CRM anomalies and opportunities.
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Pattern:
    id: str                        # "SILENT_CHURN_RISK"
    version: str                   # "1.0.0"
    name: str                      
    category: str                  # PIPELINE | RELATIONSHIP | SUPPORT | ACTIVITY | REVENUE | COMPOSITE
    description: str               
    trigger_conditions: List[str]  # List of observation IDs that must fire
    min_conditions_required: int   # 1 = OR logic, len(trigger_conditions) = AND logic
    insight_template: str          # Parameterized "why it matters" string
    business_impact_template: str  # Parameterized "consequence if ignored" string
    severity: str                  # HIGH | MEDIUM | LOW | POSITIVE
    confidence_weight: float       # 0.0–1.0. How reliable is this detection rule.
    tags: List[str]

# --- SECTION 2: Finding & Intelligence Brief Dataclasses ---
# Models detected finding instances and composite account intelligence briefs.
@dataclass
class Finding:
    id: str                        # "{pattern_id}_{account_id}"
    pattern_id: str
    pattern_version: str
    category: str
    observation: str               # Plain English fact.
    insight: str                   # Why it matters (rendered insight_template)
    business_impact: str           # Consequence if ignored (rendered business_impact_template)
    severity: str
    evidence: List[str]            # Raw data references that triggered this finding
    priority_score: float          # Final computed priority 0.0–1.0
    confidence: float              # Hierarchical confidence — NOT from LLM

@dataclass
class IntelligenceBrief:
    account_name: str
    account_risk_score: float      # Composite 0.0–1.0
    top_finding: str               # Plain text. Top-ranked finding observation.
    ranked_findings: List[Finding] # Sorted descending by priority_score
    expansion_signals: List[str]   # POSITIVE-severity finding observations
    critical_count: int            # Count of HIGH severity findings
    confidence: float              # Level 5 — mean of top 3 finding confidences
    account_maturity: str          # ACQUISITION | GROWTH | AT_RISK | STRATEGIC | CHURNING
    data_quality_score: float      # From Layer 2 (pass-through for confidence chain)
    is_empty: bool = False         # True when no data available — safe fallback state
