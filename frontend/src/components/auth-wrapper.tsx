'use client'

/**
 * AUTHENTICATION LAYOUT WRAPPER (auth-wrapper.tsx)
 * Security wrapper guarding downstream pages, displaying a sleek loading spinner
 * on initialization, and redirecting non-authenticated users to AuthPage login screens.
 */

// --- SECTION 1: Dependencies & Hook Integrations ---
// Imports user session validation hooks and full-screen auth page component views.
import { useAuth } from '@/context/AuthContext'
import AuthPage from './auth-page'

// --- SECTION 2: Auth Wrapper Shield Component ---
// Validates session state tokens, shows progress indicators, and serves nested page trees.
export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const { user, loading, isTransitioning } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center mb-2 animate-pulse">
            <span className="text-xl font-bold text-primary">A</span>
          </div>
          <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
        </div>
      </div>
    )
  }

  if (!user || isTransitioning) {
    return <AuthPage />
  }

  return <>{children}</>
}
