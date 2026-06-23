'use client';

import React from 'react';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';

interface SummaryWidgetProps {
  content: string;
}

/**
 * Level 2: Context framing.
 * Renders a warm, readable summary with sans-serif typography
 * and subtle left-border accent. Supports inline markdown (bold/italic).
 */
export function SummaryWidget({ content }: SummaryWidgetProps) {
  if (!content) return null;

  return (
    <div className="apex-widget-summary">
      <p className="text-[13.5px] text-zinc-600 dark:text-zinc-400 leading-[1.7] font-[family-name:var(--font-inter)]">
        {renderInlineMarkdown(content)}
      </p>
    </div>
  );
}
