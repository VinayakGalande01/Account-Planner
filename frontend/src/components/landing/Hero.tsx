// --------------------------------------------------------------------
// Hero.tsx
// Landing page hero section: status pill, headline/subhead copy with
// primary/secondary CTAs, a mini stats strip, and an embedded compact
// DashboardPreview HUD on the right column.
// --- SECTION: Component ---
// --------------------------------------------------------------------

'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUpRight, Activity, Radio, ShieldCheck } from 'lucide-react';
import { DashboardPreview } from './DashboardPreview';

interface HeroProps {
  onCta: () => void;
}

// --- SECTION: Component ---
export const Hero: React.FC<HeroProps> = ({ onCta }) => {
  return (
    <section
      id="top"
      data-testid="hero-section"
      className="relative pt-32 pb-24 lg:pt-40 lg:pb-32 overflow-hidden scanlines"
    >
      {/* layered background */}
      <div className="absolute inset-0 grid-bg opacity-70 pointer-events-none" />
      <div className="absolute inset-0 radial-glow pointer-events-none" />
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent, hsl(var(--primary)/0.6), transparent)',
        }}
      />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8 z-10">
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-8 items-start">
          {/* Left column - copy */}
          <div className="lg:col-span-7 text-left">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 mb-8 border border-primary/30 bg-primary/5"
              data-testid="hero-status-pill"
              style={{
                clipPath:
                  'polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)',
              }}
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75 animate-ping" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
              </span>
              <span className="font-mono text-[10px] tracking-[0.3em] text-primary uppercase">
                System Online · Ready to Scan
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.05 }}
              className="font-display font-bold uppercase text-5xl sm:text-6xl lg:text-7xl leading-[0.95] tracking-tighter"
              data-testid="hero-headline"
            >
              The easy way
              <br />
              to keep &amp; grow <span className="text-primary neon-text">your</span>
              <br />
              <span className="text-primary neon-text">key</span> accounts.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="mt-8 max-w-xl text-base lg:text-lg text-muted-foreground leading-relaxed"
              data-testid="hero-subhead"
            >
              APEX connects to your CRM to track client happiness, send warning alerts,
              and help you predict sales targets in one simple dashboard.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.25 }}
              className="mt-10 flex flex-wrap items-center gap-4"
            >
              <button
                onClick={onCta}
                data-testid="hero-primary-cta"
                className="btn-primary inline-flex items-center gap-2 cursor-pointer"
              >
                Open Dashboard
                <ArrowUpRight className="w-4 h-4" />
              </button>
              <a
                href="#preview"
                data-testid="hero-secondary-cta"
                className="btn-ghost inline-flex items-center gap-2 cursor-pointer"
              >
                See Live Preview
              </a>
            </motion.div>

            {/* Mini stats strip */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="mt-14 grid grid-cols-3 gap-px bg-primary/15 border border-primary/15"
              data-testid="hero-stats-strip"
            >
              {[
                { icon: Activity, value: '5-factor', label: 'Account Health Score' },
                { icon: Radio, value: '4 signals', label: 'Automatic Risk Detection' },
                { icon: ShieldCheck, value: 'Grounded', label: 'Every Number From CRM' },
              ].map((s) => (
                <div
                  key={s.label}
                  className="bg-background/80 px-4 py-5 flex flex-col gap-1 text-left"
                >
                  <s.icon
                    className="w-4 h-4 text-primary"
                    strokeWidth={1.5}
                  />
                  <div className="font-display text-3xl font-bold tracking-tight">
                    {s.value}
                  </div>
                  <div className="text-[10px] font-mono tracking-[0.2em] uppercase text-muted-foreground">
                    {s.label}
                  </div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right column - mini HUD */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="lg:col-span-5 lg:sticky lg:top-28"
            data-testid="hero-hud"
          >
            <DashboardPreview compact />
          </motion.div>
        </div>
      </div>
    </section>
  );
};
