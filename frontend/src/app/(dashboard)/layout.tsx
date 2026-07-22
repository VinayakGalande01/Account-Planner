import { AuthWrapper } from '@/components/auth-wrapper'
import { DashboardShell } from '@/components/dashboard-shell'

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
