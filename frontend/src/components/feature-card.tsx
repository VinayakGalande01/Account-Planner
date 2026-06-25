'use client'

import { motion } from 'framer-motion'
import { ReactNode } from 'react'

interface FeatureCardProps {
  icon: ReactNode
  title: string
  description: string
  delay?: number
}

export function FeatureCard({ icon, title, description, delay = 0 }: FeatureCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
      className="group rounded-lg border border-white/10 bg-black/50 p-6 transition-all hover:border-blue-500/50 hover:bg-black/80 hover:shadow-lg hover:shadow-blue-500/10"
    >
      <div className="mb-4 inline-flex rounded-lg bg-white/5 p-3 text-zinc-100 transition-transform group-hover:scale-110">
        {icon}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-white">{title}</h3>
      <p className="text-zinc-400">{description}</p>
    </motion.div>
  )
}
