'use client';

import React from 'react';

interface SummaryWidgetProps {
  content: string;
}

/**
 * Level 2: Context framing.
 * Renders a concise operational summary with subtle left-border accent.
 */
export function SummaryWidget({ content }: SummaryWidgetProps) {
  if (!content) return null;

  return (
    <div className="apex-widget-summary">
      <p className="text-[13px] text-zinc-400 leading-relaxed font-[family-name:var(--font-mono)]">
        {content}
      </p>
    </div>
  );
}
