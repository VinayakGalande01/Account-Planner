import React from 'react';
import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import MainLayout from '../components/MainLayout';

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
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`} style={{ colorScheme: 'dark' }}>
      <body className="bg-background text-foreground antialiased selection:bg-primary/30 min-h-screen font-[family-name:var(--font-inter)]">
        <MainLayout>
          {children}
        </MainLayout>
      </body>
    </html>
  );
}
