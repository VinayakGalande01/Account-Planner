'use client'

/**
 * ANIMATION CONTEXT PROVIDER (AnimationContext.tsx)
 * Manages global entrance animation states and reduced-motion user accessibility preferences.
 */

// --- SECTION 1: Dependencies & Context Type Schema ---
// Imports React Context hooks and Framer Motion accessibility configuration wrappers.
import { createContext, useContext, useEffect, useState } from 'react'
import { MotionConfig } from 'framer-motion'

interface AnimationContextType {
  isFirstVisit: boolean
}

// --- SECTION 2: Provider Implementation & Custom Hook ---
// Manages first-visit entrance animation timers and exports the useAnimation hook.
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
