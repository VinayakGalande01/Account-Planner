'use client'

// ThinkingIndicator: animated "AI is working" status pill that crossfades
// status labels and rotates idle reassurance phrases when silent.
// Major sections:
// - State/hooks: status sync + idle rotation timers
// - Render: pulsing brain icon, crossfading status text

import { useState, useEffect } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Brain } from 'lucide-react'
import { getFriendlyStageLabel, idleReassurancePhrases } from '@/utils/stageLabels'

interface ThinkingIndicatorProps {
  status: string
}

export function ThinkingIndicator({ status }: ThinkingIndicatorProps) {
  // --- SECTION: State/Hooks ---
  const shouldReduceMotion = useReducedMotion()
  const [displayStatus, setDisplayStatus] = useState('')
  const [idleIndex, setIdleIndex] = useState(0)

  // Sync displayStatus with status
  useEffect(() => {
    if (status) {
      setDisplayStatus(getFriendlyStageLabel(status))
      setIdleIndex(0)
    }
  }, [status])

  // Idle timeout loop: rotate reassurance phrases if status is silent for > 1.8 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setIdleIndex((prev) => (prev + 1) % idleReassurancePhrases.length)
      setDisplayStatus(idleReassurancePhrases[idleIndex])
    }, 1800)

    return () => clearTimeout(timer)
  }, [displayStatus, idleIndex])

  // --- SECTION: Render ---
  return (
    <div className="flex items-center gap-3 py-3 px-4 bg-secondary/30 border border-border rounded-lg max-w-md h-12 select-none">
      {/* Pulse/Glow Brain Icon */}
      <motion.div
        animate={
          shouldReduceMotion
            ? {}
            : {
                scale: [1, 1.12, 1],
                opacity: [0.75, 1, 0.75],
              }
        }
        transition={{
          duration: 1.8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="w-5 h-5 text-primary flex items-center justify-center shrink-0"
      >
        <Brain className="w-5 h-5 text-primary drop-shadow-[0_0_8px_rgba(37,99,235,0.4)]" aria-hidden="true" />
      </motion.div>

      {/* Crossfading status labels */}
      <div className="flex-1 overflow-hidden relative h-4 flex items-center">
        <AnimatePresence mode="wait">
          <motion.p
            key={displayStatus}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.18 }}
            className="text-xs font-semibold text-muted-foreground truncate"
          >
            {displayStatus || 'Thinking...'}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  )
}
