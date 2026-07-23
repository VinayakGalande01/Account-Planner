/**
 * ROOT APPLICATION LAYOUT (src/app/layout.tsx)
 * Global layout wrapper providing Google Fonts (Geist, Space Grotesk), dark mode themes,
 * SEO metadata, toast notifications, and context providers (Auth, Sidebar, Data, Animation).
 */

// --- SECTION 1: Dependencies & Context Providers ---
// Imports Next.js font loaders, metadata definitions, global CSS, and React Context providers.
import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono, Space_Grotesk } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'
import { SidebarProvider } from '@/context/SidebarContext'
import { DataProvider } from '@/context/DataContext'
import { AnimationProvider } from '@/context/AnimationContext'
import { Toaster } from 'sonner'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})
const spaceGrotesk = Space_Grotesk({
  variable: '--font-display',
  subsets: ['latin'],
})

// --- SECTION 2: SEO Metadata & Viewport Configurations ---
// Defines page titles, descriptions, theme colors, and browser icon favicon manifests.
export const metadata: Metadata = {
  title: 'APEX - Account Planning & Execution Intelligence',
  description: 'AI-powered sales and account management platform',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: [{ media: '(prefers-color-scheme: dark)', color: '#09090b' }],
}

import { ThemeProvider } from '@/context/ThemeContext'
import { SkipLink } from '@/components/SkipLink'

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${spaceGrotesk.variable} dark`}
    >
      <body className="font-sans antialiased bg-background">
        <SkipLink />
        <ThemeProvider>
          <AnimationProvider>
            <AuthProvider>
              <SidebarProvider>
                <DataProvider>
                  {children}
                </DataProvider>
              </SidebarProvider>
            </AuthProvider>
          </AnimationProvider>
        </ThemeProvider>
        <Toaster theme="dark" position="top-center" />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
