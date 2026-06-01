'use client';

import React, { useState } from 'react';
import type { ConfidenceData } from '../../types/responseContract';

interface ConfidenceWidgetProps {
  data: ConfidenceData;
}

/**
 * Level 6: Secondary governance (collapsible).
 * Grounding metadata is operational trust verification, NOT primary intelligence.
 * Collapsed by default to reduce cognitive load.
 */
export function ConfidenceWidget({ data }: ConfidenceWidgetProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!data) return null;

  return (
    <div className="apex-widget-governance apex-governance-default" id="apex-confidence">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="apex-governance-toggle"
        aria-expanded={isExpanded}
        aria-controls="apex-confidence-content"
      >
        <span className="flex items-center gap-2">
          <span className="text-[10px]">📊</span>
          <span className="text-[11px] font-bold tracking-widest uppercase text-zinc-500 font-[family-name:var(--font-mono)]">
            Grounding: {data.score}
          </span>
        </span>
        <span className={`apex-chevron ${isExpanded ? 'apex-chevron-open' : ''}`}>▾</span>
      </button>
      {isExpanded && (
        <div id="apex-confidence-content" className="apex-governance-content">
          <div className="space-y-1.5 text-[12px] text-zinc-500 font-[family-name:var(--font-mono)]">
            <div className="flex items-start gap-2">
              <span className="text-zinc-600 flex-shrink-0">Status:</span>
              <span>{data.status}</span>
            </div>
            {data.sources.length > 0 && (
              <div className="flex items-start gap-2">
                <span className="text-zinc-600 flex-shrink-0">Sources:</span>
                <span>{data.sources.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
