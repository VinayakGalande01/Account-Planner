'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  Lock,
  Activity,
  GitBranch,
  Terminal,
  Siren,
  LucideIcon,
} from 'lucide-react';

interface FeatureItem {
  code: string;
  icon: LucideIcon;
  title: string;
  body: string;
  bullets: string[];
  accent: 'primary' | 'secondary' | 'destructive';
}

const FEATURES: FeatureItem[] = [
  {
    code: '01 / SECURITY',
    icon: Lock,
    title: 'Secure Account Access',
    body:
      'Keep your data safe with advanced login protections, automatic safety checks, and strong password validation built into your portal.',
    bullets: ['Safe Login Sessions', 'Bcrypt Security', 'Strong Password Checks'],
    accent: 'primary',
  },
  {
    code: '02 / HEALTH',
    icon: Activity,
    title: 'Client Directory & Health Score',
    body:
      'View all your clients in one clean list. See a simple account health score computed from support histories, deal velocity, and customer action rates in real-time.',
    bullets: ['Importance Grouping', 'Combined Health Score', 'Live Status Tracking'],
    accent: 'primary',
  },
  {
    code: '03 / PREDICT',
    icon: GitBranch,
    title: 'Sales Target Predictor',
    body:
      'Adjust deal sizes and win rates to simulate your sales pipeline. Stress-test your goals without affecting your actual CRM records.',
    bullets: ['Pipeline Simulation', 'Target Predictions', 'No-Risk Planning'],
    accent: 'secondary',
  },
  {
    code: '04 / ASSIST',
    icon: Terminal,
    title: 'Smart AI Assistant',
    body:
      'Ask questions in a simple chat tool and get accurate answers based directly on your client records, contacts, and active tickets.',
    bullets: ['CRM Grounded AI', 'Citations & Source Links', 'Fast Answers'],
    accent: 'primary',
  },
  {
    code: '05 / ALERTS',
    icon: Siren,
    title: 'Smart Warning Alerts',
    body:
      'Get notified immediately when a client has unresolved issues or a deal is at risk, with quick suggestions on how to reach out to them.',
    bullets: ['Risk Identification', 'AI Email Drafts', 'Urgent Warnings'],
    accent: 'destructive',
  },
];

export const Features: React.FC = () => {
  return (
    <section
      id="capabilities"
      data-testid="features-section"
      className="relative py-24 lg:py-32"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 mb-16">
          <div className="text-left">
            <div className="label-tag mb-4">// Features</div>
            <h2 className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl uppercase tracking-tighter max-w-3xl leading-[0.95]">
              Five tools. One <span className="text-primary">simple</span> dashboard.
            </h2>
          </div>
          <p className="max-w-md text-muted-foreground text-left">
            Everything you need to manage relationships and protect your revenue, built to make your day-to-day simpler.
          </p>
        </div>

        {/* Bento grid */}
        <div className="grid grid-cols-12 gap-4 lg:gap-5">
          {FEATURES.map((f, i) => {
            const span =
              i === 0
                ? 'col-span-12 lg:col-span-7'
                : i === 1
                ? 'col-span-12 lg:col-span-5'
                : i === 2
                ? 'col-span-12 lg:col-span-5'
                : i === 3
                ? 'col-span-12 lg:col-span-7'
                : 'col-span-12';
            return (
              <motion.div
                key={f.code}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ duration: 0.55, delay: i * 0.05 }}
                className={`relative glass p-6 lg:p-8 rounded-md border border-primary/20 ${span}`}
                data-testid={`feature-card-${i + 1}`}
              >
                {/* corner spans to create brackets on features manually */}
                <span className="absolute top-[-1px] left-[-1px] w-3.5 h-3.5 border-t-2 border-l-2 border-primary pointer-events-none" style={{ filter: 'drop-shadow(0 0 6px hsl(var(--primary) / 0.7))' }} />
                <span className="absolute bottom-[-1px] right-[-1px] w-3.5 h-3.5 border-b-2 border-r-2 border-primary pointer-events-none" style={{ filter: 'drop-shadow(0 0 6px hsl(var(--primary) / 0.7))' }} />
                <span className="absolute top-[-1px] right-[-1px] w-3.5 h-3.5 border-t-2 border-r-2 border-primary pointer-events-none" style={{ filter: 'drop-shadow(0 0 6px hsl(var(--primary) / 0.7))' }} />
                <span className="absolute bottom-[-1px] left-[-1px] w-3.5 h-3.5 border-b-2 border-l-2 border-primary pointer-events-none" style={{ filter: 'drop-shadow(0 0 6px hsl(var(--primary) / 0.7))' }} />

                <div className="flex items-center justify-between mb-6">
                  <span className="label-tag">{f.code}</span>
                  <f.icon
                    className={`w-5 h-5 ${
                      f.accent === 'destructive'
                        ? 'text-red-500'
                        : 'text-primary'
                    }`}
                    strokeWidth={1.5}
                  />
                </div>
                <h3 className="font-display text-2xl lg:text-3xl font-bold uppercase tracking-tight mb-3 leading-tight text-left">
                  {f.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed text-sm max-w-lg text-left">
                  {f.body}
                </p>
                <ul className="mt-6 flex flex-wrap gap-2">
                  {f.bullets.map((b) => (
                    <li
                      key={b}
                      className="font-mono text-[10px] tracking-widest uppercase px-2.5 py-1 border border-primary/25 text-primary/90 bg-primary/5"
                    >
                      {b}
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
