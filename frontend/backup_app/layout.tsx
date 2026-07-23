// LEGACY/BACKUP FILE — not part of the active build (frontend/src is the live app).
// Original Next.js root layout for the "Account Planner / Tactical Command Center" UI.
// Loaded fonts, injected the pre-hydration dark/light theme script, and wrapped the
// app in ThemeProvider / AuthProvider / DataProvider + MainLayout shell.
//
// --- SECTION: Font Setup (Inter, JetBrains Mono, Rajdhani, Chivo) ---
// --- SECTION: Metadata Export ---
// --- SECTION: RootLayout Component ---
//   - <head> inline script: applies stored/system theme before paint
//   - <body>: Theme/Auth/Data providers wrapping MainLayout

import React from 'react';
import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Rajdhani, Chivo } from 'next/font/google';
import './globals.css';
import MainLayout from '../components/MainLayout';
import { DataProvider } from '../context/DataContext';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthProvider } from '../context/AuthContext';



const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

const rajdhani = Rajdhani({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-rajdhani',
  display: 'swap',
});

const chivo = Chivo({
  subsets: ['latin'],
  weight: ['300', '400', '500', '700'],
  variable: '--font-chivo',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Account Planner | Tactical Command Center',
  description: 'ERP-Grade Enterprise Account Intelligence & Strategic Control System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} ${rajdhani.variable} ${chivo.variable}`} suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const storedTheme = localStorage.getItem('theme');
                if (storedTheme === 'dark' || (!storedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                  document.documentElement.style.colorScheme = 'dark';
                } else if (storedTheme === 'light') {
                  document.documentElement.classList.remove('dark');
                  document.documentElement.style.colorScheme = 'light';
                } else {
                  // Default fallback is dark
                  document.documentElement.classList.add('dark');
                  document.documentElement.style.colorScheme = 'dark';
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body className="bg-background text-foreground antialiased selection:bg-primary/30 min-h-screen font-[family-name:var(--font-inter)]">
        <ThemeProvider>
          <AuthProvider>
            <DataProvider>
              <MainLayout>
                {children}
              </MainLayout>
            </DataProvider>
          </AuthProvider>
        </ThemeProvider>

      </body>
    </html>
  );
}
