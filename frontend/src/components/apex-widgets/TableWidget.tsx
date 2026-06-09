'use client';

import React from 'react';
import type { TableData } from '../../types/responseContract';

// ── TableWidget (Structured JSON → Premium Data Grid) ───────

interface TableWidgetProps {
  data: TableData;
}

/**
 * Level 3: Tactical data grid.
 * Renders from structured data models (not markdown strings).
 * Supports future: sorting, filtering, pagination, export, virtualization.
 *
 * Design Rule: Backend owns ranking/priority/truncation.
 *              Frontend only handles rendering and layout.
 */
export function TableWidget({ data }: TableWidgetProps) {
  if (!data?.rows || data.rows.length === 0) return null;

  return (
    <div className="apex-widget-table">
      <div className="overflow-x-auto">
        <table className="apex-data-grid" id="apex-table-primary">
          <thead>
            <tr>
              {data.columns.map((col) => (
                <th key={col}>{formatColumnHeader(col)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, idx) => (
              <tr
                key={idx}
                className="animate-fade-row"
                style={{ animationDelay: `${idx * 25}ms` }}
              >
                {data.columns.map((col) => (
                  <td
                    key={col}
                    className={isNumericColumn(col) ? 'tabular-nums text-right' : ''}
                  >
                    {formatCell(row[col], col)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="apex-table-footer">
        <span className="text-[10px] text-zinc-600 font-[family-name:var(--font-mono)] tracking-wider uppercase">
          {data.rows.length} record{data.rows.length !== 1 ? 's' : ''} · Backend-ranked
        </span>
      </div>
    </div>
  );
}

// ── TableSkeleton (Atomic Hydration Placeholder) ────────────

/**
 * Skeleton placeholder shown during streaming choreography.
 * Displayed until headline + summary are complete, then replaced
 * by atomic table hydration.
 *
 * Tables NEVER stream row-by-row.
 */
export function TableSkeleton() {
  return (
    <div className="apex-widget-table apex-table-skeleton">
      <div className="space-y-0">
        {/* Header skeleton */}
        <div className="flex gap-4 px-3 py-2.5 border-b border-white/[0.06]">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="ghost-cell flex-1 h-3" style={{ animationDelay: `${i * 100}ms` }} />
          ))}
        </div>
        {/* Row skeletons */}
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex gap-4 px-3 py-2 ghost-row"
            style={{ animationDelay: `${i * 150}ms` }}
          >
            {Array.from({ length: 6 }).map((_, j) => (
              <div key={j} className="ghost-cell flex-1 h-2.5" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── TableMarkdownWidget (LLM Fallback) ──────────────────────

interface TableMarkdownWidgetProps {
  content: string;
}

/**
 * Fallback renderer for LLM-generated markdown tables.
 * Parses markdown table syntax into structured grid rendering.
 * Used when backend sends TABLE (markdown) instead of TABLE_DATA (JSON).
 */
export function TableMarkdownWidget({ content }: TableMarkdownWidgetProps) {
  const lines = content.split('\n').filter((l) => l.trim());
  if (lines.length < 2) {
    return (
      <div className="text-[13px] text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap font-[family-name:var(--font-mono)]">
        {content}
      </div>
    );
  }

  const headerLine = lines[0];
  const separatorLine = lines[1];

  // Verify this is actually a markdown table
  if (!separatorLine.includes('---')) {
    return (
      <div className="text-[13px] text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap font-[family-name:var(--font-mono)]">
        {content}
      </div>
    );
  }

  const headers = headerLine
    .split('|')
    .map((h) => h.trim())
    .filter(Boolean);
  const rows = lines.slice(2).map((line) =>
    line
      .split('|')
      .map((cell) => cell.trim())
      .filter(Boolean)
  );

  return (
    <div className="apex-widget-table">
      <div className="overflow-x-auto">
        <table className="apex-data-grid">
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="animate-fade-row" style={{ animationDelay: `${i * 25}ms` }}>
                {row.map((cell, j) => (
                  <td key={j}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Formatting Helpers ──────────────────────────────────────

function formatColumnHeader(col: string): string {
  return col
    .replace(/_/g, ' ')
    .replace(/USD/g, '(USD)')
    .replace(/Pct/g, '%');
}

function isNumericColumn(col: string): boolean {
  return /Amount|USD|Score|Pct|Rank|Revenue|Value|Forecast/i.test(col);
}

function formatCell(value: string | number | boolean | null | undefined, column: string): string {
  if (value === null || value === undefined || value === '') return '—';

  if (/Amount|USD|Revenue|Value|Forecast/i.test(column)) {
    const num = Number(value);
    if (!isNaN(num)) {
      return `$${num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    }
  }

  if (/Score/i.test(column)) {
    const num = Number(value);
    if (!isNaN(num)) return num.toFixed(1);
  }

  if (/Pct/i.test(column)) {
    const num = Number(value);
    if (!isNaN(num)) return `${num}%`;
  }

  return String(value);
}
