'use client';

/**
 * LIGHTWEIGHT INLINE MARKDOWN RENDERER (src/utils/inlineMarkdown.tsx)
 * Renders bold, italic, and inline code formatting inside APEX widget cards without external dependencies.
 */

// --- SECTION 1: Dependencies & Import Setup ---
// Imports React primitives for creating inline styled DOM node arrays.
import React from 'react';

// --- SECTION 2: Inline Markdown Tokenizer & Renderer ---
// Parses text strings using regex matchers to return styled ReactNode JSX elements.
export function renderInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Regex matches: **bold**, *italic*, `code`
  const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[1]) {
      // **bold**
      parts.push(
        <strong key={match.index} className="font-semibold text-foreground">
          {match[2]}
        </strong>
      );
    } else if (match[3]) {
      // *italic*
      parts.push(
        <em key={match.index} className="italic text-foreground/80">
          {match[4]}
        </em>
      );
    } else if (match[5]) {
      // `code`
      parts.push(
        <code
          key={match.index}
          className="px-1.5 py-0.5 rounded bg-zinc-800/50 text-[12px] font-[family-name:var(--font-mono)] text-zinc-300"
        >
          {match[6]}
        </code>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}
