'use client';

import React from 'react';

interface ActionsWidgetProps {
  actions: string[];
}

/**
 * Level 5: Operational directives.
 * Renders backend-ranked next-best-actions with priority badges.
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
          <li key={i} className="flex items-start gap-3 text-[13px]">
            <span className="apex-action-badge" aria-label={`Priority ${i + 1}`}>
              {i + 1}
            </span>
            <span className="text-zinc-800 dark:text-zinc-200 leading-relaxed font-[family-name:var(--font-mono)]">
              {action}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
