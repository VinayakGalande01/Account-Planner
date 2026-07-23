'use client';

// TableWidget — APEX pipeline Level 3 widget (and file exports two
// sibling widgets: TableSkeleton, TableMarkdownWidget).
// Renders structured tabular data (TABLE_DATA) as a premium data grid,
// with a loading skeleton and a markdown-table fallback (TABLE).
// Sections in this file:
//   - TableWidget (props + render)
//   - TableSkeleton (streaming placeholder)
//   - TableMarkdownWidget (LLM markdown-table fallback)
//   - Formatting helpers (headers, cell values, badges)

import React from 'react';
import type { TableData } from '../../types/responseContract';

// ── TableWidget (Structured JSON → Premium Data Grid) ───────

// --- SECTION: TableWidget ---
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
        <table className="apex-data-grid" id="apex-table-primary" aria-label="Structured data grid">
          <thead>
            <tr>
              {data.columns.map((col) => (
                <th key={col} scope="col">{formatColumnHeader(col)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, idx) => (
              <tr
                key={idx}
                className="animate-fade-row"
                style={{ animationDelay: `${idx * 40}ms` }}
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
        <span className="text-[10px] text-zinc-500 font-[family-name:var(--font-inter)] tracking-wide">
          {data.rows.length} record{data.rows.length !== 1 ? 's' : ''} · Ranked by priority
        </span>
      </div>
    </div>
  );
}

// ── TableSkeleton (Atomic Hydration Placeholder) ────────────
// --- SECTION: TableSkeleton ---

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
// --- SECTION: TableMarkdownWidget ---

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
// --- SECTION: Formatting helpers ---

function formatColumnHeader(col: string): string {
  return col
    .replace(/_/g, ' ')
    .replace(/USD/g, '(USD)')
    .replace(/Pct/g, '%');
}

function isNumericColumn(col: string): boolean {
  return /Amount|USD|Score|Pct|Rank|Revenue|Value|Forecast/i.test(col);
}

function formatCell(value: string | number | boolean | null | undefined, column: string): React.ReactNode {
  if (value === null || value === undefined || value === '') return '—';

  if (/insight/i.test(column)) {
    return <span className="italic text-zinc-500 dark:text-zinc-400">{String(value)}</span>;
  }

  // 1. Classification & Risk Badge Pill Spans
  if (/classification|risk_level|risk level/i.test(column)) {
    const val = String(value).toLowerCase();
    const isCritical = val.includes('critical');
    const isHigh = val.includes('high');
    const isMedium = val.includes('medium');
    const isLow = val.includes('low');

    let badgeStyle = {
      color: 'rgba(161, 161, 170, 0.9)',
      backgroundColor: 'rgba(161, 161, 170, 0.08)',
      border: '1px solid rgba(161, 161, 170, 0.15)'
    };

    if (isCritical) {
      badgeStyle = {
        color: '#f97316',
        backgroundColor: 'rgba(249, 115, 22, 0.1)',
        border: '1px solid rgba(249, 115, 22, 0.25)'
      };
    } else if (isHigh) {
      badgeStyle = {
        color: '#ef4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.25)'
      };
    } else if (isMedium) {
      badgeStyle = {
        color: '#eab308',
        backgroundColor: 'rgba(234, 179, 8, 0.1)',
        border: '1px solid rgba(234, 179, 8, 0.25)'
      };
    } else if (isLow) {
      badgeStyle = {
        color: '#22c55e',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.25)'
      };
    }

    return (
      <span
        style={{
          ...badgeStyle,
          borderRadius: '9999px',
          padding: '2px 8px',
          fontSize: '10.5px',
          fontWeight: 600,
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          display: 'inline-block',
          whiteSpace: 'nowrap'
        }}
      >
        {String(value)}
      </span>
    );
  }

  // 2. Risk Score Color Tags
  if (/^risk.*score$/i.test(column)) {
    const num = Number(value);
    if (!isNaN(num)) {
      const color = num >= 10 ? '#ef4444' : num >= 7 ? '#f97316' : num >= 4 ? '#eab308' : '#22c55e';
      return (
        <span style={{ color, fontWeight: 700, fontFamily: 'var(--font-mono), monospace' }}>
          {num.toFixed(1)}
        </span>
      );
    }
  }

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
