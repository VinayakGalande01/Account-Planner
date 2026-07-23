// --------------------------------------------------------------------
// Navbar.tsx
// Fixed landing page navigation header: logo/brand, desktop nav links,
// theme toggle, login CTA, and a collapsible mobile menu.
// --- SECTION: Nav data ---
// --- SECTION: State & theme hook ---
// --- SECTION: Render (desktop nav + mobile menu) ---
// --------------------------------------------------------------------

'use client';

import React, { useState } from 'react';
import { Sun, Moon, Hexagon, Menu, X } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { motion } from 'framer-motion';

// --- SECTION: Nav data ---
const NAV = [
  { label: 'CAPABILITIES', href: '#capabilities' },
  { label: 'PREVIEW', href: '#preview' },
  { label: 'PROTOCOL', href: '#protocol' },
];

interface NavbarProps {
  onRequestAccess: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onRequestAccess }) => {
  // --- SECTION: State & theme hook ---
  const { theme, toggleTheme } = useTheme();
  const [open, setOpen] = useState(false);

  // --- SECTION: Render (desktop nav + mobile menu) ---
  return (
    <motion.header
      data-testid="landing-navbar"
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="fixed top-0 inset-x-0 z-50 backdrop-blur-md"
      style={{
        background: 'hsl(var(--background) / 0.65)',
        borderBottom: '1px solid hsl(var(--primary) / 0.15)',
      }}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        <a
          href="#top"
          data-testid="nav-logo"
          className="flex items-center gap-2.5 group"
        >
          <div className="relative w-8 h-8 grid place-items-center">
            <Hexagon
              className="w-8 h-8 text-primary group-hover:rotate-180 transition-transform duration-700"
              strokeWidth={1.5}
            />
            <span className="absolute inset-0 grid place-items-center text-[10px] font-mono font-bold text-primary">
              AX
            </span>
          </div>
          <div className="leading-none text-left">
            <div className="font-display font-bold text-lg tracking-tight uppercase">
              Apex<span className="text-primary">.</span>Planner
            </div>
            <div className="text-[9px] font-mono tracking-[0.3em] text-muted-foreground uppercase">
              Tactical Command Center
            </div>
          </div>
        </a>

        <nav className="hidden md:flex items-center gap-8">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              data-testid={`nav-link-${n.label.toLowerCase()}`}
              className="text-xs font-mono tracking-[0.22em] text-muted-foreground hover:text-primary transition-colors"
            >
              {n.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <button
            data-testid="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            className="w-9 h-9 grid place-items-center border border-primary/30 hover:border-primary hover:bg-primary/10 transition-all cursor-pointer"
            style={{
              clipPath:
                'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)',
            }}
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-primary" strokeWidth={1.8} aria-hidden="true" />
            ) : (
              <Moon className="w-4 h-4 text-primary" strokeWidth={1.8} aria-hidden="true" />
            )}
          </button>
          <button
            data-testid="nav-cta-access"
            onClick={onRequestAccess}
            className="hidden sm:inline-flex btn-primary cursor-pointer"
          >
            Log In
          </button>
          <button
            data-testid="nav-mobile-toggle"
            onClick={() => setOpen(!open)}
            className="md:hidden w-9 h-9 grid place-items-center border border-primary/30 cursor-pointer"
            aria-label={open ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={open}
          >
            {open ? (
              <X className="w-4 h-4 text-primary" aria-hidden="true" />
            ) : (
              <Menu className="w-4 h-4 text-primary" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-primary/15 px-6 py-4 flex flex-col gap-3 bg-background/95">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              onClick={() => setOpen(false)}
              className="text-sm font-mono tracking-widest text-muted-foreground hover:text-primary"
              data-testid={`mobile-nav-link-${n.label.toLowerCase()}`}
            >
              {n.label}
            </a>
          ))}
          <button
            onClick={() => {
              setOpen(false);
              onRequestAccess();
            }}
            className="btn-primary w-full text-center mt-2 cursor-pointer"
          >
            Log In
          </button>
        </div>
      )}
    </motion.header>
  );
};
