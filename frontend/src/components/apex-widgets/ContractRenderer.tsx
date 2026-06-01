'use client';

import React, { useMemo } from 'react';
import type { ResponseContract, SectionName } from '../../types/responseContract';
import { SECTION_RENDER_ORDER } from '../../types/responseContract';
import { parseStreamingSections, parseResponseContract } from '../../utils/contractParser';
import { HeadlineWidget } from './HeadlineWidget';
import { SummaryWidget } from './SummaryWidget';
import { TableWidget, TableSkeleton, TableMarkdownWidget } from './TableWidget';
import { SignalsWidget } from './SignalsWidget';
import { ActionsWidget } from './ActionsWidget';
import { CrmHygieneWidget } from './CrmHygieneWidget';
import { ConfidenceWidget } from './ConfidenceWidget';

// ── Widget Registry ─────────────────────────────────────────
// Registry-driven component mapping. Extensible: add new sections
// by registering a renderer here. No conditional rendering in the
// orchestrator loop.

type WidgetRenderer = (content: string) => React.ReactNode;

const WIDGET_REGISTRY: Record<string, WidgetRenderer> = {
  HEADLINE: (content) => <HeadlineWidget content={content} />,

  SUMMARY: (content) => <SummaryWidget content={content} />,

  TABLE_DATA: (content) => {
    try {
      const data = JSON.parse(content);
      return <TableWidget data={data} />;
    } catch {
      return <div className="text-[13px] text-zinc-400 font-[family-name:var(--font-mono)]">{content}</div>;
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
};

// ── Streaming Contract Renderer ─────────────────────────────

interface ContractRendererProps {
  /** Raw content string (possibly still streaming) */
  content: string;
  /** Whether the stream is still active */
  isStreaming: boolean;
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
export function ContractRenderer({ content, isStreaming }: ContractRendererProps) {
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

  const renderedSections: React.ReactNode[] = [];

  // Phase 1: Meta logs
  if (metaLogs.length > 0) {
    renderedSections.push(
      <div key="apex-meta-logs" className="space-y-1 mb-2">
        {metaLogs.map((log, i) => (
          <div key={i} className="text-[12px] text-zinc-600 font-bold tracking-widest my-1 uppercase font-[family-name:var(--font-mono)]">
            {log}
          </div>
        ))}
      </div>
    );
  }

  // Phase 2: Sections in visual priority order
  for (const section of SECTION_RENDER_ORDER) {
    // INTENT is metadata, never rendered
    if (section === 'INTENT') continue;

    // ── Table sections (special choreography) ──────────────
    if (section === 'TABLE_DATA' || section === 'TABLE') {
      // Skip TABLE if TABLE_DATA was already processed
      if (section === 'TABLE' && completedSections.has('TABLE_DATA')) continue;

      if (tableReady) {
        // Atomic table hydration
        const tableContent = completedSections.get('TABLE_DATA') || completedSections.get('TABLE')!;
        const sectionType = completedSections.has('TABLE_DATA') ? 'TABLE_DATA' : 'TABLE';
        const renderer = WIDGET_REGISTRY[sectionType];
        if (renderer && tableContent) {
          renderedSections.push(
            <div key="apex-table" className="apex-section-block animate-slide-up">
              {renderer(tableContent)}
            </div>
          );
        }
      } else if (showTableSkeleton && section === 'TABLE_DATA') {
        // Show skeleton placeholder (tables NEVER stream row-by-row)
        renderedSections.push(
          <div key="apex-table-skeleton" className="apex-section-block">
            <TableSkeleton />
          </div>
        );
      } else if (activeSection === 'TABLE_DATA' || activeSection === 'TABLE') {
        // Table data is the active section (still arriving)
        renderedSections.push(
          <div key="apex-table-skeleton" className="apex-section-block">
            <TableSkeleton />
          </div>
        );
      }
      continue;
    }

    // ── Completed sections ─────────────────────────────────
    if (completedSections.has(section)) {
      const sectionContent = completedSections.get(section)!;
      const renderer = WIDGET_REGISTRY[section];
      if (renderer && sectionContent) {
        renderedSections.push(
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
        renderedSections.push(
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

  return <div className="apex-contract-response space-y-3">{renderedSections}</div>;
}

// ── Finalized Contract Renderer ─────────────────────────────

interface FinalizedRendererProps {
  /** Normalized ResponseContract (post-stream application state) */
  contract: ResponseContract;
}

/**
 * Renders a finalized (non-streaming) structured response from
 * a normalized ResponseContract state object.
 *
 * Used for messages in conversation history. Renders from structured
 * data models, not raw text — enabling future sort/filter/export.
 */
export function FinalizedContractRenderer({ contract }: FinalizedRendererProps) {
  if (!contract.isStructured) return null;

  return (
    <div className="apex-contract-response space-y-3">
      {contract.headline && (
        <div className="apex-section-block">
          <HeadlineWidget content={contract.headline} />
        </div>
      )}
      {contract.summary && (
        <div className="apex-section-block">
          <SummaryWidget content={contract.summary} />
        </div>
      )}
      {contract.tableData && (
        <div className="apex-section-block">
          <TableWidget data={contract.tableData} />
        </div>
      )}
      {contract.tableMarkdown && !contract.tableData && (
        <div className="apex-section-block">
          <TableMarkdownWidget content={contract.tableMarkdown} />
        </div>
      )}
      {contract.signals.length > 0 && (
        <div className="apex-section-block">
          <SignalsWidget signals={contract.signals} />
        </div>
      )}
      {contract.actions.length > 0 && (
        <div className="apex-section-block">
          <ActionsWidget actions={contract.actions} />
        </div>
      )}
      {contract.crmWarnings.length > 0 && (
        <div className="apex-section-block">
          <CrmHygieneWidget warnings={contract.crmWarnings} />
        </div>
      )}
      {contract.confidence && (
        <div className="apex-section-block">
          <ConfidenceWidget data={contract.confidence} />
        </div>
      )}
    </div>
  );
}
