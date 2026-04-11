import React from 'react';
import type { Metadata } from 'next';
import './globals.css';
import MainLayout from '../components/MainLayout';

export const metadata: Metadata = {
  title: 'Account Planner Agent | Enterprise Strategic Control',
  description: 'ERP-Grade B2B Account Planning and Analysis Engine',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: 'dark' }}>
      <body className="bg-background text-foreground antialiased selection:bg-primary/30 min-h-screen font-sans">
        <MainLayout>
          {children}
        </MainLayout>
      </body>
    </html>
  );
}
