'use client'

import React, { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { useAnimation } from '@/context/AnimationContext'

interface PageHeaderProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  action?: ReactNode
}

export function PageHeader({ title, subtitle, icon, action }: PageHeaderProps) {
  const { isFirstVisit } = useAnimation()

  return (
    <motion.div
      initial={isFirstVisit ? { opacity: 0, y: -12 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="mb-6 flex items-center justify-between gap-4"
    >
      <div>
        <div className="flex items-center gap-2.5">
          {icon && <span className="text-primary flex-shrink-0">{icon}</span>}
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground font-sans">
            {title}
          </h1>
        </div>
        {subtitle && (
          <p className="text-sm text-muted-foreground mt-1 font-normal">
            {subtitle}
          </p>
        )}
      </div>

      {action && <div className="flex items-center gap-3 shrink-0">{action}</div>}
    </motion.div>
  )
}
