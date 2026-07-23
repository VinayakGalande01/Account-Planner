'use client';

// ActionsWidget — APEX pipeline Level 5 widget.
// Renders the backend-ranked list of next-best-actions as a numbered
// list with gradient priority badges and inline markdown support.
// Sections in this file:
//   - Props/types
//   - Render (ordered list of action items)
// Design Rule: action order is decided by the backend; this component
// only renders, it never re-ranks or filters actions client-side.

import React from 'react';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';

// --- SECTION: Props ---
interface ActionsWidgetProps {
  actions: string[];
}

/**
 * Level 5: Operational directives.
 * Renders backend-ranked next-best-actions with gradient badges and hover effects.
 * Uses sans-serif for natural readability. Supports inline markdown.
 *
 * Design Rule: Action order/priority is determined by the backend.
 *              Frontend only handles rendering — no client-side re-ranking.
 */
export function ActionsWidget({ actions }: ActionsWidgetProps) {
  if (!actions || actions.length === 0) return null;

  // --- SECTION: Render ---
  return (
    <div className="apex-widget-actions">
      <div className="apex-section-label">RECOMMENDED ACTIONS</div>
      <ol className="space-y-2.5">
        {actions.map((action, i) => (
          <li
            key={i}
            className="apex-action-item flex items-start gap-3 text-[13px] p-2.5 rounded-lg transition-all duration-200 hover:bg-white/[0.02]"
          >
            <span className="apex-action-badge-gradient" aria-label={`Priority ${i + 1}`}>
              {i + 1}
            </span>
            <span className="text-zinc-700 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-inter)]">
              {renderInlineMarkdown(action)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
