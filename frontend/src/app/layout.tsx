import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'
import { SidebarProvider } from '@/context/SidebarContext'
import { DataProvider } from '@/context/DataContext'
import { Toaster } from 'sonner'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark`}
    >
      <body className="font-sans antialiased bg-background">
        <AuthProvider>
          <SidebarProvider>
            <DataProvider>
              {children}
            </DataProvider>
          </SidebarProvider>
        </AuthProvider>
        <Toaster theme="dark" position="top-center" />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
