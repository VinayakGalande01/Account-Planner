'use client';

// SignalsWidget — APEX pipeline Level 4 widget.
// Renders backend-ranked trend signals as typed, icon-coded cards
// (revenue, pipeline, risk, etc.), parsed from an optional [TYPE] prefix.
// Sections in this file:
//   - Types/props (signal style map, parser)
//   - Render (signal card list)

import React from 'react';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';

// --- SECTION: Types/props ---
interface SignalsWidgetProps {
  signals: string[];
}

/**
 * Signal type → visual style mapping with emoji icons.
 * Backend sends optional [TYPE] prefix (e.g., "[REVENUE] 3 deals close within 30 days").
 * Frontend parses the prefix for visual styling. Falls back to default if no prefix found.
 */
const SIGNAL_STYLES: Record<string, { color: string; bgColor: string; icon: string }> = {
  REVENUE:    { color: 'text-emerald-400', bgColor: 'bg-emerald-500/8', icon: '💰' },
  PIPELINE:   { color: 'text-blue-400',    bgColor: 'bg-blue-500/8',    icon: '📊' },
  STRATEGIC:  { color: 'text-violet-400',  bgColor: 'bg-violet-500/8',  icon: '🎯' },
  RISK:       { color: 'text-amber-400',   bgColor: 'bg-amber-500/8',   icon: '⚠️' },
  ENGAGEMENT: { color: 'text-cyan-400',    bgColor: 'bg-cyan-500/8',    icon: '🤝' },
  TEMPORAL:   { color: 'text-orange-400',  bgColor: 'bg-orange-500/8',  icon: '⏱️' },
  CRM:        { color: 'text-zinc-400',    bgColor: 'bg-zinc-500/8',    icon: '📋' },
  MARKET:     { color: 'text-rose-400',    bgColor: 'bg-rose-500/8',    icon: '📈' },
  QUANTIFIED: { color: 'text-blue-400',    bgColor: 'bg-blue-500/8',    icon: '📊' },
  STATUS:     { color: 'text-emerald-400', bgColor: 'bg-emerald-500/8', icon: '✅' },
};

const DEFAULT_STYLE = { color: 'text-primary', bgColor: 'bg-primary/8', icon: '◆' };

/**
 * Parse an optional [TYPE] prefix from a signal string.
 * Returns { type, text } where type is the parsed signal type and text is the clean signal.
 */
function parseSignalType(signal: string): { type: string | null; text: string } {
  const match = signal.match(/^\[([A-Z_]+)\]\s*(.*)/);
  if (match) {
    return { type: match[1], text: match[2] };
  }
  return { type: null, text: signal };
}

/**
 * Level 4: Key intelligence signals.
 * Renders backend-ranked, typed trend signals with emoji icons and card backgrounds.
 * Uses sans-serif for natural readability.
 *
 * Design Rule: Signal order/priority is determined by the backend.
 *              Frontend only handles rendering — no client-side re-ranking.
 */
export function SignalsWidget({ signals }: SignalsWidgetProps) {
  if (!signals || signals.length === 0) return null;

  // --- SECTION: Render ---
  return (
    <div className="apex-widget-signals">
      <div className="apex-section-label">KEY SIGNALS</div>
      <div className="space-y-2">
        {signals.map((signal, i) => {
          const { type, text } = parseSignalType(signal);
          const style = type && SIGNAL_STYLES[type] ? SIGNAL_STYLES[type] : DEFAULT_STYLE;

          return (
            <div
              key={i}
              className={`apex-signal-card ${style.bgColor} border border-white/[0.04] rounded-lg px-3.5 py-2.5 flex items-start gap-3 transition-colors duration-200 hover:border-white/[0.08]`}
            >
              <span className="text-[14px] mt-[1px] flex-shrink-0">{style.icon}</span>
              <span className="text-[13px] text-zinc-700 dark:text-zinc-300 leading-relaxed font-[family-name:var(--font-inter)]">
                {type && (
                  <span className={`${style.color} text-[10px] font-bold tracking-wider mr-1.5 uppercase font-[family-name:var(--font-mono)]`}>
                    {type}
                  </span>
                )}
                {renderInlineMarkdown(text)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
