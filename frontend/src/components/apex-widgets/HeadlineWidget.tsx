'use client';

import React from 'react';

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

  return (
    <div className="apex-widget-headline">
      <div className="apex-headline-accent" aria-hidden="true" />
      <h2 className="text-[16px] font-bold tracking-normal text-foreground leading-snug font-[family-name:var(--font-inter)]">
        {content}
      </h2>
    </div>
  );
}
