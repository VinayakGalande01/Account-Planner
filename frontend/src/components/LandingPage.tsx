'use client';

import React from 'react';
import { Navbar } from './landing/Navbar';
import { Hero } from './landing/Hero';
import { Features } from './landing/Features';
import { PreviewSection } from './landing/PreviewSection';
import { HowItWorks } from './landing/HowItWorks';

interface LandingPageProps {
  onInitialize: () => void;
}

export default function LandingPage({ onInitialize }: LandingPageProps) {
  return (
    <div className="relative min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/30">
      {/* Animated Scanlines and Grid Background */}
      <div className="absolute inset-0 scanlines pointer-events-none z-50" />
      
      {/* Component Sections */}
      <Navbar onRequestAccess={onInitialize} />
      
      <main className="relative">
        <Hero onCta={onInitialize} />
        <PreviewSection />
        <Features />
        <HowItWorks />
      </main>

      {/* Footer info line */}
      <footer className="py-8 border-t border-primary/10 text-center font-mono text-[10px] text-muted-foreground bg-black/10">
        <div className="max-w-7xl mx-auto px-6">
          <p>© {new Date().getFullYear()} APEX.PLANNER // PROTOCOL SECURED // HS256 AUTH ACTIVE</p>
        </div>
      </footer>
    </div>
  );
}
