'use client'

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
