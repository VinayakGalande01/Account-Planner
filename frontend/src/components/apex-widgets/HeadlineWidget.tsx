'use client';

import React from 'react';

interface HeadlineWidgetProps {
  content: string;
}

/**
 * Level 1: Primary attention anchor.
 * Renders the dominant operational headline with a cobalt gradient accent bar.
 */
export function HeadlineWidget({ content }: HeadlineWidgetProps) {
  if (!content) return null;

  return (
    <div className="apex-widget-headline">
      <div className="apex-headline-accent" aria-hidden="true" />
      <h2 className="text-[15px] font-black tracking-wide text-foreground leading-snug font-[family-name:var(--font-mono)]">
        {content}
      </h2>
    </div>
  );
}
