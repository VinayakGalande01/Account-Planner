/**
 * DASHBOARD GROUP LAYOUT (src/app/(dashboard)/layout.tsx)
 * Enforces user authentication checks via AuthWrapper and wraps authenticated
 * dashboard routes with the collapsible sidebar and navigation DashboardShell.
 */

// --- SECTION 1: Dependencies & Shell Wrappers ---
// Imports authentication boundary guard and dashboard layout shell wrappers.
import { AuthWrapper } from '@/components/layout/auth-wrapper'
import { DashboardShell } from '@/components/layout/dashboard-shell'

// --- SECTION 2: Dashboard Group Component ---
// Wraps child dashboard routes (Accounts, Intelligence, Pipeline, Datasets, Settings) with layout shells.
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthWrapper>
      <DashboardShell>{children}</DashboardShell>
    </AuthWrapper>
  )
}

