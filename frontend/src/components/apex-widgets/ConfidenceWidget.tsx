'use client';

// ConfidenceWidget — APEX pipeline Level 6 widget.
// Renders an always-visible grounding/confidence pill with a mini
// progress bar and source list, replacing an older collapsible toggle.
// Sections in this file:
//   - Props/types
//   - Data shaping (score parsing, color thresholds)
//   - Render (pill + progress bar + sources)

import React from 'react';
import type { ConfidenceData } from '../../types/responseContract';

// --- SECTION: Props ---
interface ConfidenceWidgetProps {
  data: ConfidenceData;
}

/**
 * Level 6: Confidence / Grounding indicator.
 * Redesigned as an always-visible inline pill with a mini progress bar,
 * instead of a collapsible toggle. This builds visual trust at a glance
 * without requiring user interaction.
 */
export function ConfidenceWidget({ data }: ConfidenceWidgetProps) {
  if (!data) return null;

  // --- SECTION: Data shaping ---
  // Parse percentage from score string (e.g., "85%" → 85)
  const scoreNum = parseFloat(data.score) || 0;
  const isHigh = scoreNum >= 80;
  const isMedium = scoreNum >= 50 && scoreNum < 80;

  const barColor = isHigh
    ? 'bg-emerald-500'
    : isMedium
    ? 'bg-amber-500'
    : 'bg-red-500';

  const textColor = isHigh
    ? 'text-emerald-500'
    : isMedium
    ? 'text-amber-500'
    : 'text-red-500';

  const bgColor = isHigh
    ? 'bg-emerald-500/8'
    : isMedium
    ? 'bg-amber-500/8'
    : 'bg-red-500/8';

  // --- SECTION: Render ---
  return (
    <div
      className={`apex-confidence-pill ${bgColor} border border-white/[0.04] rounded-lg px-4 py-2.5 flex items-center gap-3`}
      id="apex-confidence"
    >
      <span className="text-[13px]">📊</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[11px] font-semibold tracking-wider uppercase text-zinc-500 font-[family-name:var(--font-mono)]">
            Grounding
          </span>
          <span className={`text-[12px] font-bold ${textColor} font-[family-name:var(--font-mono)]`}>
            {data.score}
          </span>
        </div>
        {/* Mini progress bar */}
        <div className="w-full h-1.5 rounded-full bg-zinc-800/50 overflow-hidden">
          <div
            className={`h-full rounded-full ${barColor} transition-all duration-700 ease-out`}
            style={{ width: `${Math.min(scoreNum, 100)}%` }}
          />
        </div>
        {data.sources.length > 0 && (
          <div className="mt-1.5 text-[10px] text-zinc-600 font-[family-name:var(--font-mono)]">
            Sources: {data.sources.join(' · ')}
          </div>
        )}
      </div>
    </div>
  );
}
