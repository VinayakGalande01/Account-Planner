'use client';

import React from 'react';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';

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
