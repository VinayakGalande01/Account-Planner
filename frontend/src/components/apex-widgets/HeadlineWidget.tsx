'use client';

// HeadlineWidget — APEX pipeline Level 1 widget.
// Renders the dominant headline sentence, the primary attention
// anchor at the top of a structured APEX response.
// Sections in this file:
//   - Props/types
//   - Render (accent bar + headline text)

import React from 'react';

// --- SECTION: Props ---
interface HeadlineWidgetProps {
  content: string;
}

/**
 * Level 1: Primary attention anchor.
 * Renders the dominant headline with modern sans-serif typography
 * and a cobalt gradient accent bar.
 */
export function HeadlineWidget({ content }: HeadlineWidgetProps) {
  if (!content) return null;

  // --- SECTION: Render ---
  return (
    <div className="apex-widget-headline">
      <div className="apex-headline-accent" aria-hidden="true" />
      <h2 className="text-[16px] font-bold tracking-normal text-foreground leading-snug font-[family-name:var(--font-inter)]">
        {content}
      </h2>
    </div>
  );
}
