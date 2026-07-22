'use client'

import { motion } from 'framer-motion'
import { Star } from 'lucide-react'

interface TestimonialCardProps {
  quote: string
  author: string
  title: string
  company: string
  delay?: number
}

export function TestimonialCard({ quote, author, title, company, delay = 0 }: TestimonialCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
      className="rounded-lg border border-border bg-card p-6"
    >
      <div className="mb-4 flex gap-1">
        {[...Array(5)].map((_, i) => (
          <Star key={i} className="size-4 fill-amber-400 text-amber-400" aria-hidden="true" />
        ))}
      </div>
      <p className="mb-6 text-foreground/90">&quot;{quote}&quot;</p>
      <div>
        <p className="font-semibold text-foreground">{author}</p>
        <p className="text-sm text-muted-foreground">{title} at {company}</p>
      </div>
    </motion.div>
  )
}
