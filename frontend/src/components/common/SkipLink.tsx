'use client'

// SkipLink: accessibility skip-navigation link, visually hidden until
// focused, jumps keyboard users straight to #main-content.
// Major sections:
// - Render: single anchor element

import React from 'react'

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only"
    >
      Skip to main content
    </a>
  )
}
