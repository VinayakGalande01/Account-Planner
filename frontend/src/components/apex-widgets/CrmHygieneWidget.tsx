'use client';

import React, { useState } from 'react';

interface CrmHygieneWidgetProps {
  warnings: string[];
}

/**
 * Level 6: Secondary governance (collapsible).
 * CRM hygiene is secondary data governance, NOT primary intelligence.
 * Collapsed by default to reduce cognitive load.
 *
 * Amber color scheme indicates operational governance, not critical alerts.
 */
export function CrmHygieneWidget({ warnings }: CrmHygieneWidgetProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="apex-widget-governance apex-governance-amber" id="apex-crm-hygiene">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="apex-governance-toggle"
        aria-expanded={isExpanded}
        aria-controls="apex-crm-hygiene-content"
      >
        <span className="flex items-center gap-2">
          <span className="text-amber-500 text-[10px]">⚠</span>
          <span className="text-[11px] font-bold tracking-widest uppercase text-amber-500/80 font-[family-name:var(--font-mono)]">
            CRM Hygiene ({warnings.length})
          </span>
        </span>
        <span className={`apex-chevron ${isExpanded ? 'apex-chevron-open' : ''}`}>▾</span>
      </button>
      {isExpanded && (
        <div id="apex-crm-hygiene-content" className="apex-governance-content">
          <ul className="space-y-1.5">
            {warnings.map((warning, i) => (
              <li
                key={i}
                className="text-[12px] text-amber-400/70 flex items-start gap-2 font-[family-name:var(--font-mono)]"
              >
                <span className="mt-0.5 flex-shrink-0">•</span>
                <span className="leading-relaxed">{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
