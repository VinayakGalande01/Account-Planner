/**
 * APEX Response Contract Types
 *
 * These types define the normalized internal state for structured APEX responses.
 * The __SECTION_*__ tag system is strictly a STREAMING TRANSPORT FORMAT.
 * After stream completion, all responses are normalized into these types.
 *
 * Design Rule: Backend owns ranking, severity, priority, truncation, importance ordering.
 *              Frontend owns rendering, layout, interaction, hydration, progressive disclosure.
 */

// ── Structured Data Models ──────────────────────────────────

export interface TableData {
  /** Column names in display order */
  columns: string[];
  /** Rows as key-value objects (column name → cell value) */
  rows: Record<string, string | number | boolean | null>[];
}

export interface ConfidenceData {
  /** Grounding score (e.g., "100%") */
  score: string;
  /** Human-readable grounding status */
  status: string;
  /** Data sources used for this response */
  sources: string[];
}

/** A single recommended next-step action for the copilot UI */
export interface RecommendedAction {
  /** Display label for the action chip */
  title: string;
  /** Machine-readable action key (for future workflow routing) */
  action: string;
  /** Optional tooltip description */
  description?: string;
  /** Priority level — affects chip styling */
  priority?: 'high' | 'medium' | 'low';
}

// ── Response Contract (Normalized Application State) ────────

export interface ResponseContract {
  /** Classified query intent (e.g., GLOBAL_LIST_QUERY) */
  queryType: string;
  /** Primary operational headline */
  headline: string;
  /** Max 3-bullet executive summary (optional) */
  executiveSummary?: string;
  /** 2-4 line context summary */
  summary: string;
  /** Structured table data for deterministic rendering (supports sort/filter/export) */
  tableData: TableData | null;
  /** Fallback markdown table (from LLM responses when structured data unavailable) */
  tableMarkdown: string | null;
  /** Key trend signals (backend-ranked) */
  signals: string[];
  /** Prioritized next-best-actions (backend-ranked) */
  actions: string[];
  /** CRM hygiene warnings (secondary governance, collapsed by default) */
  crmWarnings: string[];
  /** Grounding & integrity metadata (secondary governance, collapsed by default) */
  confidence: ConfidenceData | null;
  /** Executive Why This Matters summary */
  whyThisMatters?: string;
  /** Direct answer to the user's question (rendered first, before headline) */
  directAnswer?: string;
  /** Contextual recommended next-step actions (copilot chips) */
  recommendedActions: RecommendedAction[];
  /** Raw text content for fallback rendering */
  rawContent: string;
  /** Pipeline breakdown details */
  breakdown: { total_usd: number; breakdown: string[] } | null;
  /** Whether the response contains structured __SECTION_*__ tags */
  isStructured: boolean;
}

// ── Section Transport Protocol ──────────────────────────────

/** Section names as they appear in the streaming transport format */
export type SectionName =
  | 'INTENT'
  | 'DIRECT_ANSWER'
  | 'HEADLINE'
  | 'EXECUTIVE_SUMMARY'
  | 'SUMMARY'
  | 'TABLE_DATA'
  | 'TABLE'
  | 'SIGNALS'
  | 'BREAKDOWN'
  | 'WHY_THIS_MATTERS'
  | 'ACTIONS'
  | 'CRM_HYGIENE'
  | 'CONFIDENCE'
  | 'RECOMMENDED_ACTIONS'
  | 'END';

/**
 * Priority ordering for section rendering (Level 1 = highest).
 * Frontend renders sections in this order regardless of stream arrival order.
 */
export const SECTION_RENDER_ORDER: SectionName[] = [
  'DIRECT_ANSWER', // Level 0: Immediate factual answer (Question-First Policy)
  'HEADLINE',     // Level 1: Primary attention anchor
  'EXECUTIVE_SUMMARY', // Level 1.5: High-level overview
  'SUMMARY',      // Level 2: Context framing
  'TABLE_DATA',   // Level 3: Tactical data (structured JSON — preferred)
  'TABLE',        // Level 3: Tactical data (markdown fallback)
  'SIGNALS',      // Level 4: Key intelligence
  'WHY_THIS_MATTERS', // Level 4.5: Executive importance bridge
  'ACTIONS',      // Level 5: Operational directives
  'CRM_HYGIENE',  // Level 6: Secondary governance (collapsible)
  'CONFIDENCE',   // Level 6: Secondary governance (collapsible)
  'RECOMMENDED_ACTIONS', // Level 7: Copilot next-step suggestions (interactive)
];

/** Sections that render as collapsible secondary governance (not primary intelligence) */
export const SECONDARY_SECTIONS: SectionName[] = [
  'CRM_HYGIENE',
  'CONFIDENCE',
];
