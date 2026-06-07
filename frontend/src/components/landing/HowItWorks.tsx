'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Database, Cpu, Crosshair, LucideIcon } from 'lucide-react';

interface StepItem {
  n: string;
  icon: LucideIcon;
  title: string;
  body: string;
}

const STEPS: StepItem[] = [
  {
    n: '01',
    icon: Database,
    title: 'Connect Your Data',
    body:
      'Securely link your CRM to sync your client information, sales deals, and support tickets in seconds.',
  },
  {
    n: '02',
    icon: Cpu,
    title: 'Automatic Analysis',
    body:
      'The system automatically calculates a simple client health score and flags accounts that need your attention.',
  },
  {
    n: '03',
    icon: Crosshair,
    title: 'Keep Clients Happy',
    body:
      'Use warning alerts, AI chat, and predictions to solve issues and support your clients before problems happen.',
  },
];

export const HowItWorks: React.FC = () => {
  return (
    <section
      id="protocol"
      data-testid="howitworks-section"
      className="relative py-24 lg:py-32"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="mb-16 max-w-2xl text-left">
          <div className="label-tag mb-4">// How it works</div>
          <h2 className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl uppercase tracking-tighter leading-[0.95]">
            Keep your clients happy in <span className="text-primary">three</span> simple steps.
          </h2>
        </div>

        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-px bg-primary/15 border border-primary/15">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="bg-background relative p-8 lg:p-10 group hover:bg-primary/5 transition-colors text-left"
              data-testid={`protocol-step-${s.n}`}
            >
              <div className="flex items-center justify-between mb-8">
                <span className="font-display text-5xl font-bold text-primary/30 group-hover:text-primary/60 transition-colors">
                  {s.n}
                </span>
                <div className="w-12 h-12 grid place-items-center border border-primary/40 group-hover:border-primary group-hover:bg-primary/10 transition-all">
                  <s.icon className="w-5 h-5 text-primary" strokeWidth={1.5} />
                </div>
              </div>
              <h3 className="font-display text-2xl font-bold uppercase tracking-tight mb-3">
                {s.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {s.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
