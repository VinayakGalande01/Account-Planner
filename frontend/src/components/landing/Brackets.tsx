// --------------------------------------------------------------------
// Brackets.tsx
// Small decorative wrapper that adds tactical-HUD style corner accents
// (top-right / bottom-left bracket marks) around any child content.
// Used across landing sections (e.g. DashboardPreview) for the
// sci-fi/terminal visual theme.
// --- SECTION: Types ---
// --- SECTION: Component ---
// --------------------------------------------------------------------

'use client';

import React from 'react';

// --- SECTION: Types ---
interface BracketsProps {
  className?: string;
  children?: React.ReactNode;
}

// --- SECTION: Component ---
export const Brackets: React.FC<BracketsProps> = ({ className = '', children }) => (
  <div className={`brackets ${className}`}>
    <span className="br-tr" />
    <span className="br-bl" />
    {children}
  </div>
);
