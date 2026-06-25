'use client'

import { useAuth } from '@/context/AuthContext'
import AuthPage from './auth-page'

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

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

  if (!user) {
    return <AuthPage />
  }

  return <>{children}</>
}
