'use client';

import React, { useMemo } from 'react';
import type { ResponseContract, SectionName, RecommendedAction, FormattedJsonResponse } from '../../types/responseContract';
import { SECTION_RENDER_ORDER } from '../../types/responseContract';
import { parseStreamingSections, parseResponseContract } from '../../utils/contractParser';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';
import { HeadlineWidget } from './HeadlineWidget';
import { SummaryWidget } from './SummaryWidget';
import { TableWidget, TableSkeleton, TableMarkdownWidget } from './TableWidget';
import { SignalsWidget } from './SignalsWidget';
import { ActionsWidget } from './ActionsWidget';
import { CrmHygieneWidget } from './CrmHygieneWidget';
import { ConfidenceWidget } from './ConfidenceWidget';
import { RecommendedActionsWidget } from './RecommendedActionsWidget';

// ── Formatted Response Renderer ─────────────────────────────

interface FormattedResponseRendererProps {
  data: FormattedJsonResponse;
  onActionClick?: (action: RecommendedAction) => void;
}

export function FormattedResponseRenderer({ data, onActionClick }: FormattedResponseRendererProps) {
  const urgencyColors = {
    P1: 'bg-red-600 text-white font-semibold px-2 py-0.5 rounded text-xs flex items-center gap-1.5 w-fit',
    P2: 'bg-amber-500 text-zinc-950 font-semibold px-2 py-0.5 rounded text-xs flex items-center gap-1.5 w-fit',
    P3: 'bg-emerald-500 text-zinc-950 font-semibold px-2 py-0.5 rounded text-xs flex items-center gap-1.5 w-fit'
  };

  const getUrgencyText = (urgency: string) => {
    if (urgency === 'P1') return '🔴 P1 — Urgent';
    if (urgency === 'P2') return '🟡 P2 — Watch';
    if (urgency === 'P3') return '🟢 P3 — On Track';
    return urgency;
  };

  const badgeClass = urgencyColors[data.urgency as keyof typeof urgencyColors] || urgencyColors.P2;

  const tableData = useMemo(() => {
    if (!data.opportunities || data.opportunities.length === 0) return null;
    return {
      columns: ['Opp ID', 'Name', 'Stage', 'Amount', 'Probability', 'Insight'],
      rows: data.opportunities.map((opp: { id: string; name: string; stage: string; amount: string; probability: string; insight: string; }) => ({
        'Opp ID': opp.id,
        'Name': opp.name,
        'Stage': opp.stage,
        'Amount': opp.amount,
        'Probability': opp.probability,
        'Insight': opp.insight
      }))
    };
  }, [data.opportunities]);

  const suggestions = useMemo(() => {
    if (!data.next_steps_suggestions || data.next_steps_suggestions.length === 0) return [];
    return data.next_steps_suggestions.map((s: string) => ({
      title: s,
      action: s
    }));
  }, [data.next_steps_suggestions]);

  const getRoleBadge = (role: string) => {
    if (role === 'Account Manager') {
      return (
        <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] px-1.5 py-0.2 rounded-full font-semibold">
          AM
        </span>
      );
    }
    if (role === 'VP Sales') {
      return (
        <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[10px] px-1.5 py-0.2 rounded-full font-semibold">
          VP
        </span>
      );
    }
    if (role === 'Executive') {
      return (
        <span className="bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 text-[10px] px-1.5 py-0.2 rounded-full font-semibold">
          Exec
        </span>
      );
    }
    return (
      <span className="bg-zinc-500/10 text-zinc-400 border border-zinc-500/20 text-[10px] px-1.5 py-0.2 rounded-full font-semibold">
        {role}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Urgency Badge */}
      <div className="flex items-center">
        <span className={badgeClass}>
          {getUrgencyText(data.urgency)}
        </span>
      </div>

      {/* Headline */}
      <h2 className="text-[1.25rem] font-bold text-zinc-900 dark:text-zinc-50 leading-snug">
        {data.headline}
      </h2>

      {/* Summary */}
      <p className="text-[0.95rem] text-zinc-600 dark:text-zinc-300 leading-relaxed">
        {data.summary}
      </p>

      {/* Two Column Layout on Desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Table & Suggestions */}
        <div className="lg:col-span-8 space-y-4">
          {/* Opportunities Table */}
          {tableData && (
            <div>
              <TableWidget data={tableData} />
            </div>
          )}
          
          {/* Next steps suggestions */}
          {suggestions.length > 0 && (
            <div className="pt-2">
              <RecommendedActionsWidget actions={suggestions} onActionClick={onActionClick} />
            </div>
          )}
        </div>

        {/* Right Column: Flags, Risks & Recommended Actions */}
        <div className="lg:col-span-4 space-y-4">
          {/* Flag Section */}
          {data.flag && (
            <div className="space-y-1.5">
              <div className="text-[11px] font-bold text-amber-500 uppercase tracking-widest font-[family-name:var(--font-mono)]">
                ONE THING I'D FLAG
              </div>
              <div className="border-l-4 border-l-amber-500 bg-zinc-900/40 p-4 rounded-r-xl flex items-start gap-3">
                <span className="text-lg flex-shrink-0">💡</span>
                <p className="text-sm text-zinc-300">
                  {data.flag}
                </p>
              </div>
            </div>
          )}

          {/* Risks Section */}
          {data.risks && data.risks.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-bold text-red-500 uppercase tracking-widest font-[family-name:var(--font-mono)]">
                RISKS TO WATCH
              </div>
              <div className="space-y-3">
                {data.risks.map((risk: { type: string; account: string; action: string; }, index: number) => (
                  <div 
                    key={index}
                    className="border-l-[3px] border-l-red-600 bg-zinc-900/40 p-4 rounded-r-xl flex flex-col"
                  >
                    <div className="text-sm font-bold text-zinc-100">
                      {risk.type}
                    </div>
                    <div className="text-xs text-zinc-400 mt-0.5">
                      Account: {risk.account}
                    </div>
                    <div className="text-sm text-white mt-2 font-medium">
                      → {risk.action}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          {data.recommended_actions && data.recommended_actions.length > 0 && (
            <div className="space-y-2">
              <div className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest font-[family-name:var(--font-mono)]">
                RECOMMENDED ACTIONS
              </div>
              <ol className="space-y-3">
                {data.recommended_actions.map((act: { priority: number; role: 'Account Manager' | 'VP Sales' | 'Executive'; action: string; }, index: number) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-zinc-800 text-zinc-300 flex items-center justify-center font-bold text-xs mt-0.5">
                      {index + 1}
                    </span>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {getRoleBadge(act.role)}
                        <span className="text-[10px] text-zinc-400 font-semibold uppercase">
                          Priority {act.priority}
                        </span>
                      </div>
                      <p className="text-sm text-zinc-700 dark:text-zinc-300">
                        {act.action}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </div>

      {/* Closing Question */}
      {data.closing_question && (
        <p className="text-sm italic text-zinc-500 dark:text-zinc-400 mt-4 leading-relaxed">
          {data.closing_question}
        </p>
      )}

      {/* Next steps suggestions */}
      {suggestions.length > 0 && (
        <div className="mt-4 pt-2">
          <RecommendedActionsWidget actions={suggestions} onActionClick={onActionClick} />
        </div>
      )}
    </div>
  );
}

// ── Widget Registry ─────────────────────────────────────────
// Registry-driven component mapping. Extensible: add new sections
// by registering a renderer here. No conditional rendering in the
// orchestrator loop.

type WidgetRenderer = (content: string) => React.ReactNode;

const WIDGET_REGISTRY: Record<string, WidgetRenderer> = {
  DIRECT_ANSWER: (content) => (
    <div className="apex-direct-answer bg-primary/[0.04] border border-primary/10 p-4 rounded-xl mb-1">
      <p className="text-[14px] text-zinc-800 dark:text-zinc-200 leading-[1.7] font-[family-name:var(--font-inter)]">
        {renderInlineMarkdown(content)}
      </p>
    </div>
  ),

  HEADLINE: (content) => <HeadlineWidget content={content} />,

  EXECUTIVE_SUMMARY: (content) => {
    const points = content
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => l.replace(/^[•\-*\d.)+\s]+/, '').trim())
      .filter(Boolean);
    return (
      <div className="apex-executive-summary border-l-2 border-indigo-500/60 bg-indigo-950/8 pl-4 pr-3 py-3.5 rounded-r my-2">
        <div className="text-[11px] font-semibold text-indigo-400 uppercase tracking-widest mb-2.5 font-[family-name:var(--font-mono)]">
          Executive Summary
        </div>
        <ul className="space-y-2">
          {points.map((point, i) => (
            <li key={i} className="text-[13px] text-zinc-700 dark:text-zinc-300 flex items-start leading-relaxed font-[family-name:var(--font-inter)]">
              <span className="text-indigo-400 mr-2.5 mt-0.5 text-[8px]">●</span>
              <span>{renderInlineMarkdown(point)}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  },

  SUMMARY: (content) => <SummaryWidget content={content} />,

  TABLE_DATA: (content) => {
    try {
      const data = JSON.parse(content);
      return <TableWidget data={data} />;
    } catch {
      return <div className="text-[13px] text-zinc-600 dark:text-zinc-400 font-[family-name:var(--font-mono)]">{content}</div>;
    }
  },

  TABLE: (content) => <TableMarkdownWidget content={content} />,

  SIGNALS: (content) => {
    const signals = content
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => l.replace(/^[◆•\-*]\s*/, '').trim())
      .filter(Boolean);
    return <SignalsWidget signals={signals} />;
  },

  WHY_THIS_MATTERS: (content) => (
    <div className="apex-why-this-matters border border-violet-500/10 bg-violet-950/8 p-4 rounded-xl my-2">
      <div className="text-[11px] font-semibold text-violet-400 uppercase tracking-widest mb-2 font-[family-name:var(--font-mono)] flex items-center gap-1.5">
        <span className="text-[12px]">💡</span> Why This Matters
      </div>
      <p className="text-[13px] text-zinc-600 dark:text-zinc-300 leading-[1.7] font-[family-name:var(--font-inter)]">
        {renderInlineMarkdown(content)}
      </p>
    </div>
  ),

  BREAKDOWN: (content) => {
    try {
      const data = JSON.parse(content);
      if (!data || !data.breakdown || data.breakdown.length === 0) return null;
      return (
        <div className="apex-breakdown bg-zinc-900/40 border border-white/5 rounded-xl p-4 my-3">
          <div className="text-[11px] text-zinc-400 uppercase font-semibold tracking-wider mb-3 font-[family-name:var(--font-mono)] flex items-center justify-between">
            <span>Pipeline Breakdown</span>
            <span className="text-emerald-400 font-bold">${(data.total_usd || 0).toLocaleString()}</span>
          </div>
          <ul className="space-y-1.5">
            {data.breakdown.map((item: string, i: number) => (
              <li key={i} className="text-[13px] text-zinc-300 flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-zinc-600"></span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      );
    } catch {
      return null;
    }
  },

  ACTIONS: (content) => {
    const actions = content
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => l.replace(/^[•\-*\d.)+\s]+/, '').trim())
      .filter(Boolean);
    return <ActionsWidget actions={actions} />;
  },

  CRM_HYGIENE: (content) => {
    const warnings = content
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => l.replace(/^[⚠️\s]+/, '').trim())
      .filter(Boolean);
    return <CrmHygieneWidget warnings={warnings} />;
  },

  CONFIDENCE: (content) => {
    try {
      const data = JSON.parse(content);
      return <ConfidenceWidget data={data} />;
    } catch {
      return <ConfidenceWidget data={{ score: content, status: content, sources: [] }} />;
    }
  },

  RECOMMENDED_ACTIONS: (content) => {
    try {
      const actions = JSON.parse(content);
      // During streaming, render without click handler (will be wired in finalized view)
      return <RecommendedActionsWidget actions={actions} />;
    } catch {
      return null;
    }
  },
};

// ── Streaming Contract Renderer ─────────────────────────────

interface ContractRendererProps {
  /** Raw content string (possibly still streaming) */
  content: string;
  /** Whether the stream is still active */
  isStreaming: boolean;
  /** Callback when a recommended action chip is clicked */
  onActionClick?: (action: RecommendedAction) => void;
}

/**
 * ContractRenderer — Orchestrates structured APEX response rendering.
 *
 * Streaming Choreography:
 * 1. Meta logs render first (before any widgets)
 * 2. Headline → renders immediately via HeadlineWidget
 * 3. Summary → renders via SummaryWidget
 * 4. Table → skeleton placeholder until headline+summary are complete, then atomic hydration
 * 5. Signals → renders via SignalsWidget
 * 6. Actions → renders via ActionsWidget
 * 7. CRM Hygiene / Confidence → collapsible secondary governance (collapsed by default)
 *
 * Falls back to plain text rendering if no __SECTION_*__ tags found.
 *
 * Design Rule: Frontend NEVER infers business meaning or priority.
 *              Backend owns all ranking/severity/truncation decisions.
 *              Frontend only handles rendering, layout, and interaction.
 */
export function ContractRenderer({ content, isStreaming, onActionClick }: ContractRendererProps) {
  const streamState = useMemo(() => parseStreamingSections(content), [content]);

  // No structured content found → return null (caller handles fallback)
  if (!streamState.hasStructuredContent) {
    return null;
  }

  const { completedSections, activeSection, activeSectionContent, metaLogs } = streamState;

  // Choreography gates: table hydrates only after headline + summary are complete
  const headlineDone = completedSections.has('HEADLINE');
  const summaryDone = completedSections.has('SUMMARY');
  const hasTableData = completedSections.has('TABLE_DATA') || completedSections.has('TABLE');
  const tableReady = hasTableData && (!isStreaming || (headlineDone && summaryDone));
  const showTableSkeleton = isStreaming && !tableReady && (headlineDone || summaryDone || hasTableData);

  const narrativeSections: React.ReactNode[] = [];
  const dataSections: React.ReactNode[] = [];
  const actionSections: React.ReactNode[] = [];

  const getTargetGroup = (sectionName: string) => {
    if (['HEADLINE', 'SUMMARY', 'DIRECT_ANSWER', 'EXECUTIVE_SUMMARY'].includes(sectionName)) {
      return narrativeSections;
    }
    if (['ACTIONS', 'CRM_HYGIENE', 'CONFIDENCE', 'RECOMMENDED_ACTIONS'].includes(sectionName)) {
      return actionSections;
    }
    return dataSections;
  };

  // Phase 2: Sections in visual priority order
  for (const section of SECTION_RENDER_ORDER) {
    // INTENT is metadata, never rendered
    if (section === 'INTENT') continue;

    const targetGroup = getTargetGroup(section);

    // ── Table sections (special choreography) ──────────────
    if (section === 'TABLE_DATA' || section === 'TABLE') {
      // Process both TABLE_DATA and TABLE in a single pass under the TABLE_DATA slot, skip TABLE iteration entirely.
      if (section === 'TABLE') continue;

      if (tableReady) {
        // Atomic table hydration
        const tableContent = completedSections.get('TABLE_DATA') || completedSections.get('TABLE')!;
        const sectionType = completedSections.has('TABLE_DATA') ? 'TABLE_DATA' : 'TABLE';
        const renderer = WIDGET_REGISTRY[sectionType];
        if (renderer && tableContent) {
          targetGroup.push(
            <div key="apex-table" className="apex-section-block animate-slide-up">
              {renderer(tableContent)}
            </div>
          );
        }
      } else if (showTableSkeleton && section === 'TABLE_DATA') {
        // Show skeleton placeholder (tables NEVER stream row-by-row)
        targetGroup.push(
          <div key="apex-table-skeleton" className="apex-section-block">
            <TableSkeleton />
          </div>
        );
      } else if (activeSection === 'TABLE_DATA' || activeSection === 'TABLE') {
        // Table data is the active section (still arriving)
        targetGroup.push(
          <div key="apex-table-skeleton" className="apex-section-block">
            <TableSkeleton />
          </div>
        );
      }
      continue;
    }

    // ── Recommended Actions (special: needs onActionClick callback) ──
    if (section === 'RECOMMENDED_ACTIONS') {
      if (completedSections.has('RECOMMENDED_ACTIONS')) {
        const raContent = completedSections.get('RECOMMENDED_ACTIONS')!;
        try {
          const actions = JSON.parse(raContent);
          targetGroup.push(
            <div key="apex-RECOMMENDED_ACTIONS" className="apex-section-block animate-slide-up">
              <RecommendedActionsWidget actions={actions} onActionClick={onActionClick} />
            </div>
          );
        } catch {
          // Silently skip if JSON invalid
        }
      }
      continue;
    }

    // ── Completed sections ─────────────────────────────────
    if (completedSections.has(section)) {
      const sectionContent = completedSections.get(section)!;
      const renderer = WIDGET_REGISTRY[section];
      if (renderer && sectionContent) {
        targetGroup.push(
          <div key={`apex-${section}`} className="apex-section-block animate-slide-up">
            {renderer(sectionContent)}
          </div>
        );
      }
      continue;
    }

    // ── Active streaming section (partial content with cursor) ──
    if (section === activeSection && activeSectionContent.trim()) {
      const renderer = WIDGET_REGISTRY[section];
      if (renderer) {
        targetGroup.push(
          <div key={`apex-${section}`} className="apex-section-block">
            {renderer(activeSectionContent.trim())}
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-primary ml-1 animate-blink-cursor align-middle" />
            )}
          </div>
        );
      }
    }
  }

  return (
    <div className="apex-contract-response">
      {metaLogs.length > 0 && (
        <div className="space-y-1 mb-2">
          {metaLogs.map((log, i) => (
            <div key={i} className="text-[12px] text-zinc-600 font-bold tracking-widest my-1 uppercase font-[family-name:var(--font-mono)]">
              {log}
            </div>
          ))}
        </div>
      )}
      {narrativeSections.length > 0 && (
        <div className="space-y-2">{narrativeSections}</div>
      )}
      {dataSections.length > 0 && (
        <div className="mt-3 space-y-3">{dataSections}</div>
      )}
      {actionSections.length > 0 && (
        <div className="mt-4 space-y-2">{actionSections}</div>
      )}
    </div>
  );
}

// ── Finalized Contract Renderer ─────────────────────────────

interface FinalizedRendererProps {
  /** Normalized ResponseContract (post-stream application state) */
  contract: ResponseContract;
  /** Callback when a recommended action chip is clicked */
  onActionClick?: (action: RecommendedAction) => void;
}

/**
 * Renders a finalized (non-streaming) structured response from
 * a normalized ResponseContract state object.
 *
 * Used for messages in conversation history. Renders from structured
 * data models, not raw text — enabling future sort/filter/export.
 */
export function FinalizedContractRenderer({ contract, onActionClick }: FinalizedRendererProps) {
  if (!contract.isStructured) return null;

  if (contract.type === 'conversational' || contract.type === 'clarification') {
    return (
      <div className="space-y-4">
        <div className="bg-primary/[0.04] border border-primary/10 p-4 rounded-xl mb-1">
          <p className="text-[14px] text-zinc-800 dark:text-zinc-200 leading-[1.7] font-[family-name:var(--font-inter)]">
            {contract.conversationalData?.message}
          </p>
        </div>
        {contract.conversationalData?.suggestions && contract.conversationalData.suggestions.length > 0 && (
          <div className="pt-2">
            <RecommendedActionsWidget 
              actions={contract.conversationalData.suggestions.map(s => ({ title: s, action: s }))} 
              onActionClick={onActionClick} 
            />
          </div>
        )}
      </div>
    );
  }

  if (contract.formattedJson) {
    return <FormattedResponseRenderer data={contract.formattedJson} onActionClick={onActionClick} />;
  }

  const narrativeSections: React.ReactNode[] = [];
  const dataSections: React.ReactNode[] = [];
  const actionSections: React.ReactNode[] = [];

  if (contract.directAnswer) {
    narrativeSections.push(
      <div key="directAnswer" className="apex-section-block">
        <div className="apex-direct-answer bg-primary/[0.04] border border-primary/10 p-4 rounded-xl mb-1">
          <p className="text-[14px] text-zinc-800 dark:text-zinc-200 leading-[1.7] font-[family-name:var(--font-inter)]">
            {renderInlineMarkdown(contract.directAnswer)}
          </p>
        </div>
      </div>
    );
  }
  if (contract.headline) {
    narrativeSections.push(
      <div key="headline" className="apex-section-block">
        <HeadlineWidget content={contract.headline} />
      </div>
    );
  }
  if (contract.executiveSummary) {
    narrativeSections.push(
      <div key="executiveSummary" className="apex-section-block">
        {WIDGET_REGISTRY['EXECUTIVE_SUMMARY'](contract.executiveSummary)}
      </div>
    );
  }
  if (contract.summary) {
    narrativeSections.push(
      <div key="summary" className="apex-section-block">
        <SummaryWidget content={contract.summary} />
      </div>
    );
  }
  if (contract.tableData) {
    dataSections.push(
      <div key="tableData" className="apex-section-block">
        <TableWidget data={contract.tableData} />
      </div>
    );
  }
  if (contract.tableMarkdown && !contract.tableData) {
    dataSections.push(
      <div key="tableMarkdown" className="apex-section-block">
        <TableMarkdownWidget content={contract.tableMarkdown} />
      </div>
    );
  }
  if (contract.signals.length > 0) {
    dataSections.push(
      <div key="signals" className="apex-section-block">
        <SignalsWidget signals={contract.signals} />
      </div>
    );
  }
  if (contract.whyThisMatters) {
    dataSections.push(
      <div key="whyThisMatters" className="apex-section-block">
        <div className="apex-why-this-matters border border-violet-500/10 bg-violet-950/8 p-4 rounded-xl my-2">
          <div className="text-[11px] font-semibold text-violet-400 uppercase tracking-widest mb-2 font-[family-name:var(--font-mono)] flex items-center gap-1.5">
            <span className="text-[12px]">💡</span> Why This Matters
          </div>
          <p className="text-[13px] text-zinc-600 dark:text-zinc-300 leading-[1.7] font-[family-name:var(--font-inter)]">
            {renderInlineMarkdown(contract.whyThisMatters)}
          </p>
        </div>
      </div>
    );
  }
  if (contract.actions.length > 0) {
    actionSections.push(
      <div key="actions" className="apex-section-block">
        <ActionsWidget actions={contract.actions} />
      </div>
    );
  }
  if (contract.crmWarnings.length > 0) {
    actionSections.push(
      <div key="crmWarnings" className="apex-section-block">
        <CrmHygieneWidget warnings={contract.crmWarnings} />
      </div>
    );
  }
  if (contract.confidence) {
    actionSections.push(
      <div key="confidence" className="apex-section-block">
        <ConfidenceWidget data={contract.confidence} />
      </div>
    );
  }
  if (contract.recommendedActions && contract.recommendedActions.length > 0) {
    actionSections.push(
      <div key="recommendedActions" className="apex-section-block">
        <RecommendedActionsWidget actions={contract.recommendedActions} onActionClick={onActionClick} />
      </div>
    );
  }

  return (
    <div className="apex-contract-response">
      {narrativeSections.length > 0 && (
        <div className="space-y-2">{narrativeSections}</div>
      )}
      {dataSections.length > 0 && (
        <div className="mt-3 space-y-3">{dataSections}</div>
      )}
      {actionSections.length > 0 && (
        <div className="mt-4 space-y-2">{actionSections}</div>
      )}
    </div>
  );
}
