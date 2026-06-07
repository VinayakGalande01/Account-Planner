'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { DashboardPreview } from './DashboardPreview';

export const PreviewSection: React.FC = () => {
  return (
    <section
      id="preview"
      data-testid="preview-section"
      className="relative py-24 lg:py-32 overflow-hidden"
    >
      <div className="absolute inset-0 grid-bg opacity-40 pointer-events-none" />
      <div className="absolute inset-0 radial-glow opacity-60 pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex flex-col items-start gap-4 mb-12 max-w-3xl text-left">
          <div className="label-tag">// Live Preview</div>
          <h2 className="font-display font-bold text-4xl sm:text-5xl lg:text-6xl uppercase tracking-tighter leading-[0.95]">
            A workspace that <span className="text-primary">simplifies</span> your client management.
          </h2>
          <p className="text-muted-foreground max-w-xl">
            See your sales progress, client health scores, warning alerts, and chat with your AI assistant in one clean dashboard.
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 32 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.7 }}
        >
          <DashboardPreview />
        </motion.div>
      </div>
    </section>
  );
};
