'use client'

// ModelLimitNotice: animated progress line shown while a slow AI answer is running.
// APEX uses free OpenRouter models (rate-limited, ~15s per call, 50 requests/day), so a
// full AI plan can take minutes. Appears only after a short delay so instant data
// answers never show it.

import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'

const SHOW_AFTER_MS = 6000

export function ModelLimitNotice() {
  const shouldReduceMotion = useReducedMotion()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), SHOW_AFTER_MS)
    return () => clearTimeout(timer)
  }, [])

  if (!visible) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      role="status"
      className="max-w-md mt-2 px-4 py-2.5 bg-secondary/20 border border-border rounded-lg"
    >
      <div className="relative h-[3px] w-full overflow-hidden rounded-full bg-primary/15">
        <motion.div
          className="absolute inset-y-0 w-1/3 rounded-full bg-primary"
          animate={shouldReduceMotion ? { left: '33%' } : { left: ['-33%', '100%'] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
        Free AI model in use: detailed plans can take 1–3 minutes. Data questions (revenue, contacts,
        at-risk lists) answer instantly.
      </p>
    </motion.div>
  )
}
