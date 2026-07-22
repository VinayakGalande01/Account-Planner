'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronRight, CheckCircle2, Circle } from 'lucide-react'
import { getFriendlyStageLabel } from '@/utils/stageLabels'

interface ReasoningTrailProps {
  steps: string[]
}

export function ReasoningTrail({ steps }: ReasoningTrailProps) {
  const [isOpen, setIsOpen] = useState(false)

  if (!steps || steps.length === 0) return null

  // Deduplicate and filter steps to keep clean stage updates
  const cleanSteps = Array.from(new Set(steps))
    .map((step) => getFriendlyStageLabel(step))
    .filter((step) => step.trim().length > 0)

  if (cleanSteps.length === 0) return null

  return (
    <div className="mb-3 border-l-2 border-primary/20 pl-4 select-none">
      {/* Toggle Bar */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        className="flex items-center gap-1.5 text-[11px] font-bold text-muted-foreground hover:text-foreground transition-colors"
      >
        {isOpen ? (
          <ChevronDown className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-primary" aria-hidden="true" />
        )}
        <span>Thought process ({cleanSteps.length} stages)</span>
      </button>

      {/* Collapsible Timeline List */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <ol className="mt-2.5 space-y-2 border-l border-border/80 pl-3.5 relative ml-1">
              {cleanSteps.map((step, idx) => {
                const isLast = idx === cleanSteps.length - 1
                return (
                  <li key={idx} className="relative pb-0.5">
                    {/* Circle Dot Check icon */}
                    <span className="absolute -left-[20px] top-0.5 w-3 h-3 rounded-full bg-card flex items-center justify-center">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary shrink-0" aria-hidden="true" />
                    </span>
                    <p className={`text-[11px] leading-relaxed ${isLast ? 'text-foreground font-semibold' : 'text-muted-foreground'}`}>
                      {step}
                    </p>
                  </li>
                )
              })}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
