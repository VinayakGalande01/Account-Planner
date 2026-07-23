'use client';

// SummaryWidget — APEX pipeline Level 2 widget.
// Renders the context-framing summary paragraph below the headline,
// with inline markdown (bold/italic) support.
// Sections in this file:
//   - Props/types
//   - Render (summary paragraph)

import React from 'react';
import { renderInlineMarkdown } from '../../utils/inlineMarkdown';

// --- SECTION: Props ---
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

  // --- SECTION: Render ---
  return (
    <div className="apex-widget-summary">
      <p className="text-[13.5px] text-zinc-600 dark:text-zinc-400 leading-[1.7] font-[family-name:var(--font-inter)]">
        {renderInlineMarkdown(content)}
      </p>
    </div>
  );
}
