'use client'

// AnimatedCounter: count-up number span that animates from `from` to `to`
// once scrolled into view, with optional delay/suffix.
// Major sections:
// - Props
// - State/hooks: intersection observer + counting interval
// - Render: counter span

import { motion } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'

interface AnimatedCounterProps {
  from: number
  to: number
  duration?: number
  suffix?: string
  delay?: number
}

export function AnimatedCounter({ from, to, duration = 2, suffix = '', delay = 0 }: AnimatedCounterProps) {
  // --- SECTION: State/Hooks ---
  const [count, setCount] = useState(from)
  const ref = useRef(null)
  const [isInView, setIsInView] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsInView(true)
      }
    })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isInView) return

    const timer = setTimeout(() => {
      const increment = (to - from) / (duration * 60)
      const interval = setInterval(() => {
        setCount((prev) => {
          const next = prev + increment
          if (next >= to) {
            clearInterval(interval)
            return to
          }
          return next
        })
      }, 16)
      return () => clearInterval(interval)
    }, delay * 1000)

    return () => clearTimeout(timer)
  }, [isInView, from, to, duration, delay])

  // --- SECTION: Render ---
  return (
    <span ref={ref}>
      {Math.floor(count)}
      {suffix}
    </span>
  )
}
