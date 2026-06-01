'use client';

import React from 'react';

interface SignalsWidgetProps {
  signals: string[];
}

/**
 * Signal type → visual style mapping.
 * Backend sends optional [TYPE] prefix (e.g., "[REVENUE] 3 deals close within 30 days").
 * Frontend parses the prefix for subtle color coding. Falls back to default if no prefix found.
 */
const SIGNAL_STYLES: Record<string, { color: string; icon: string }> = {
  REVENUE:    { color: 'text-emerald-400', icon: '◆' },
  PIPELINE:   { color: 'text-blue-400',    icon: '◆' },
  STRATEGIC:  { color: 'text-violet-400',  icon: '◆' },
  RISK:       { color: 'text-amber-400',   icon: '◆' },
  ENGAGEMENT: { color: 'text-cyan-400',    icon: '◆' },
  TEMPORAL:   { color: 'text-orange-400',  icon: '◆' },
  CRM:        { color: 'text-zinc-500',    icon: '◆' },
};

const DEFAULT_STYLE = { color: 'text-primary', icon: '◆' };

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
 * Renders backend-ranked, typed trend signals with color-coded type indicators.
 *
 * Design Rule: Signal order/priority is determined by the backend.
 *              Frontend only handles rendering — no client-side re-ranking.
 */
export function SignalsWidget({ signals }: SignalsWidgetProps) {
  if (!signals || signals.length === 0) return null;

  return (
    <div className="apex-widget-signals">
      <div className="apex-section-label">KEY SIGNALS</div>
      <ul className="space-y-1.5">
        {signals.map((signal, i) => {
          const { type, text } = parseSignalType(signal);
          const style = type && SIGNAL_STYLES[type] ? SIGNAL_STYLES[type] : DEFAULT_STYLE;

          return (
            <li key={i} className="flex items-start gap-2.5 text-[13px] text-zinc-300 font-[family-name:var(--font-mono)]">
              <span className={`${style.color} mt-[3px] text-[8px] flex-shrink-0`}>{style.icon}</span>
              <span className="leading-relaxed">
                {type && (
                  <span className={`${style.color} text-[10px] font-black tracking-wider mr-1.5 uppercase`}>
                    {type}
                  </span>
                )}
                {text}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
