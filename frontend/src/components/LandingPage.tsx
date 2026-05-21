'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Cpu, BarChart3, Shield, Database, Zap, Globe } from 'lucide-react';
import WebGLGrid from './WebGLGrid';

const PILLARS = [
  {
    icon: Cpu,
    title: 'Synthetic Intelligence',
    subtitle: 'OLLAMA ENGINE',
    description: 'Deep-link analysis with local LLM inference. Real-time account health scoring across 5 weighted dimensions.',
    metric: 'llama3.2:latest',
    metricLabel: 'Active Model',
  },
  {
    icon: BarChart3,
    title: 'Pipeline Velocity',
    subtitle: 'REVENUE CORE',
    description: 'Step-line stage analytics with cool-to-hot gradient mapping. Quartile-based forecasting against actuals.',
    metric: '9 Stages',
    metricLabel: 'Tracked',
  },
  {
    icon: Shield,
    title: 'Command & Control',
    subtitle: 'DATA MATRIX',
    description: 'Dense-data ledgers at 36px row density. Zero-friction strategic health checks triggered by selection.',
    metric: '5 Tables',
    metricLabel: 'Synced',
  },
];

const INTEGRATIONS = [
  'PostgreSQL', 'MySQL', 'Salesforce', 'HubSpot',
  'Milvus', 'Qdrant', 'Snowflake', 'Redis',
  'MongoDB', 'Elasticsearch', 'Kafka', 'dbt',
];

function ScanButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group relative px-10 py-4 bg-primary text-white text-[11px] font-black uppercase tracking-[0.25em] rounded-md overflow-hidden transition-all duration-300 hover:shadow-[0_0_40px_rgba(37,99,235,0.4)] font-[family-name:var(--font-mono)]"
    >
      {/* Scan line overlay */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="absolute top-0 left-0 w-full h-full">
          <div
            className="absolute top-0 h-[2px] w-[30%] bg-gradient-to-r from-transparent via-white/60 to-transparent"
            style={{
              animation: 'system-scan 1.5s ease-in-out infinite',
            }}
          />
        </div>
      </div>
      {/* Corner accents */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-white/30" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-white/30" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-white/30" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-white/30" />

      <span className="relative z-10 flex items-center gap-3">
        INITIALIZE APEX CONSOLE
        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
      </span>
    </button>
  );
}

export default function LandingPage({ onInitialize }: { onInitialize: () => void }) {
  const [mounted, setMounted] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [cipherText, setCipherText] = useState('');

  const FINAL_TEXT = '> SYSTEM READY. AWAITING OPERATOR AUTHENTICATION...';

  useEffect(() => {
    setMounted(true);
    let iter = 0;
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()';
    const interval = setInterval(() => {
      iter += 1;
      setCipherText(
        FINAL_TEXT.split('')
          .map((char, index) => {
            if (index < iter / 2) return char;
            if (char === ' ') return ' ';
            return chars[Math.floor(Math.random() * chars.length)];
          })
          .join('')
      );
      if (iter / 2 >= FINAL_TEXT.length) clearInterval(interval);
    }, 30);
    return () => clearInterval(interval);
  }, []);

  const handleStartTransition = () => {
    setTransitioning(true);
    setTimeout(() => {
      onInitialize();
    }, 1200);
  };

  return (
    <div className="relative min-h-screen bg-[#020202] text-foreground overflow-x-hidden">
      {/* Interactive Background Grid */}
      <WebGLGrid transitionActive={transitioning} />

      {/* Cobalt light leak — top */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/[0.04] rounded-full blur-[120px] pointer-events-none z-0" />
      {/* Cobalt light leak — bottom */}
      <div className="fixed bottom-0 right-0 w-[600px] h-[300px] bg-primary/[0.03] rounded-full blur-[100px] pointer-events-none z-0" />

      {/* ═══ NAV BAR ═══ */}
      <motion.nav
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center justify-between px-8 bg-[#020202]/60 backdrop-blur-xl border-b border-white/[0.03]"
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center font-black text-white text-[10px] shadow-[0_0_20px_rgba(37,99,235,0.3)]">
            AP
          </div>
          <span className="font-black text-[10px] tracking-[0.2em] text-primary uppercase font-[family-name:var(--font-mono)]">
            APEX PLANNER
          </span>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-[9px] font-bold text-zinc-600 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)] hidden sm:block">
            v2.1 // TACTICAL SUITE
          </span>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[9px] font-bold text-emerald-500 uppercase tracking-[0.1em] font-[family-name:var(--font-mono)]">
              Ready
            </span>
          </div>
        </div>
      </motion.nav>

      {/* ═══ HERO SECTION ═══ */}
      <section className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6 pt-14">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={mounted ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-5xl mx-auto space-y-8"
        >
          {/* Status Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 border border-primary/20 rounded-full bg-primary/[0.05]"
          >
            <Zap className="w-3 h-3 text-primary" />
            <span className="text-[9px] font-black text-primary uppercase tracking-[0.2em] font-[family-name:var(--font-mono)]">
              Enterprise Intelligence Platform
            </span>
          </motion.div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-foreground uppercase tracking-[0.25em] leading-[1.1] font-[family-name:var(--font-mono)]">
            Revenue{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-blue-400 to-primary">
              Orchestration
            </span>
            <br />
            At Scale
          </h1>

          {/* Sub-headline */}
          <p className="text-sm sm:text-base text-zinc-500 max-w-2xl mx-auto leading-relaxed font-medium">
            The elite intelligence console for enterprise account mastery.{' '}
            <span className="text-zinc-400">Synthesize.</span>{' '}
            <span className="text-zinc-400">Forecast.</span>{' '}
            <span className="text-zinc-400">Execute.</span>
          </p>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.5 }}
            className="pt-4"
          >
            <ScanButton onClick={handleStartTransition} />
          </motion.div>

          {/* Terminal hint */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
            className="text-[10px] text-zinc-700 font-[family-name:var(--font-mono)] uppercase tracking-[0.15em] min-h-[20px]"
          >
            {cipherText}
          </motion.p>
        </motion.div>

        {/* ═══ DASHBOARD PREVIEW ═══ */}
        <motion.div
          initial={{ opacity: 0, y: 60, rotateX: 8, scale: 0.95 }}
          animate={mounted ? { opacity: 1, y: 0, rotateX: 4, scale: 1 } : {}}
          transition={{ duration: 1, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="relative mt-16 max-w-5xl w-full mx-auto"
          style={{ perspective: '1200px' }}
        >
          <div className="relative rounded-lg overflow-hidden border border-white/[0.06] shadow-2xl shadow-primary/10" style={{ transform: 'rotateX(2deg)' }}>
            {/* Glare overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] via-transparent to-transparent z-10 pointer-events-none" />
            {/* System Active pulse */}
            <div className="absolute top-4 right-4 z-20 flex items-center gap-2 px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[8px] font-black text-emerald-500 uppercase font-[family-name:var(--font-mono)]">Live</span>
            </div>
            {/* Screenshot */}
            <img
              src="/dashboard-hero.png"
              alt="APEX Console Preview"
              className="w-full h-auto"
              style={{ filter: 'brightness(0.85) contrast(1.1)' }}
            />
          </div>
          {/* Reflection */}
          <div className="absolute -bottom-20 left-4 right-4 h-20 bg-gradient-to-b from-primary/[0.02] to-transparent blur-xl" />
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="mt-16 mb-8 flex flex-col items-center gap-2"
        >
          <div className="w-px h-8 bg-gradient-to-b from-primary/30 to-transparent" />
          <span className="text-[8px] text-zinc-700 uppercase tracking-[0.3em] font-[family-name:var(--font-mono)]">Scroll</span>
        </motion.div>
      </section>

      {/* ═══ THREE PILLARS ═══ */}
      <section className="relative z-10 py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-100px' }}
            transition={{ duration: 0.6 }}
            className="text-center mb-20"
          >
            <span className="text-[9px] font-black text-primary uppercase tracking-[0.3em] font-[family-name:var(--font-mono)]">
              System Architecture
            </span>
            <h2 className="text-3xl sm:text-4xl font-black text-foreground uppercase tracking-[0.2em] mt-4 font-[family-name:var(--font-mono)]">
              Three Pillars
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {PILLARS.map((pillar, idx) => {
              const Icon = pillar.icon;
              return (
                <motion.div
                  key={pillar.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.5, delay: idx * 0.12 }}
                  className="corner-brackets group relative p-8 bg-transparent hover:bg-white/[0.02] transition-all duration-300 cursor-default"
                >
                  <div className="space-y-5">
                    <div className="flex items-center justify-between">
                      <Icon className="w-5 h-5 text-primary/60 group-hover:text-primary transition-colors" />
                      <span className="text-[8px] font-black text-zinc-700 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                        {pillar.subtitle}
                      </span>
                    </div>

                    <h3 className="text-sm font-black text-foreground uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                      {pillar.title}
                    </h3>

                    <p className="text-[11px] text-zinc-500 leading-relaxed font-medium">
                      {pillar.description}
                    </p>

                    <div className="pt-4 border-t border-white/[0.04] flex items-center justify-between">
                      <span className="text-xs font-black text-primary font-[family-name:var(--font-mono)]">{pillar.metric}</span>
                      <span className="text-[8px] text-zinc-600 uppercase tracking-[0.12em] font-[family-name:var(--font-mono)]">{pillar.metricLabel}</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ═══ INTEGRATION MATRIX ═══ */}
      <section className="relative z-10 py-20 border-t border-white/[0.03]">
        <div className="text-center mb-12">
          <span className="text-[9px] font-black text-zinc-600 uppercase tracking-[0.3em] font-[family-name:var(--font-mono)]">
            Connected Cores
          </span>
        </div>

        {/* Scrolling ticker */}
        <div className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-[#020202] to-transparent z-10" />
          <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-[#020202] to-transparent z-10" />
          <div className="flex animate-marquee">
            {[...INTEGRATIONS, ...INTEGRATIONS].map((name, idx) => (
              <div
                key={`${name}-${idx}`}
                className="flex items-center justify-center px-10 py-4 shrink-0 group cursor-default"
              >
                <div className="flex items-center gap-2 text-zinc-700 group-hover:text-primary transition-colors duration-300">
                  <Database className="w-4 h-4" />
                  <span className="text-[10px] font-black uppercase tracking-[0.15em] font-[family-name:var(--font-mono)] whitespace-nowrap">
                    {name}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ FOOTER CTA ═══ */}
      <section className="relative z-10 py-32 px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-3xl mx-auto space-y-8"
        >
          <h3 className="text-2xl sm:text-3xl font-black text-foreground uppercase tracking-[0.2em] font-[family-name:var(--font-mono)]">
            Ready for Deployment
          </h3>
          <p className="text-sm text-zinc-500 max-w-lg mx-auto">
            Your intelligence engine is standing by. Initialize the console to begin strategic operations.
          </p>
          <ScanButton onClick={handleStartTransition} />
        </motion.div>
      </section>

      {/* ═══ BOTTOM BORDER ═══ */}
      <div className="h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
      <div className="py-8 text-center">
        <span className="text-[8px] text-zinc-800 uppercase tracking-[0.3em] font-[family-name:var(--font-mono)]">
          APEX Account Planner v2.1 // Tactical Suite // {new Date().getFullYear()}
        </span>
      </div>
    </div>
  );
}
