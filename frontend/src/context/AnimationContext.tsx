'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { MotionConfig } from 'framer-motion'

interface AnimationContextType {
  isFirstVisit: boolean
}

const AnimationContext = createContext<AnimationContextType>({ isFirstVisit: true })

export function AnimationProvider({ children }: { children: React.ReactNode }) {
  const [isFirstVisit, setIsFirstVisit] = useState(true)

  useEffect(() => {
    // We only want the entrance animations to play on the very first mount.
    // After that, navigation should feel instant.
    // Give it 1 second to play initial animations, then set to false.
    const timer = setTimeout(() => {
      setIsFirstVisit(false)
    }, 1000)
    
    return () => clearTimeout(timer)
  }, [])

  return (
    <AnimationContext.Provider value={{ isFirstVisit }}>
      <MotionConfig reducedMotion="user">
        {children}
      </MotionConfig>
    </AnimationContext.Provider>
  )
}

export function useAnimation() {
  return useContext(AnimationContext)
}
