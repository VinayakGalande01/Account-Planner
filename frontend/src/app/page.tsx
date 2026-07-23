'use client'

/**
 * LANDING PAGE COMPONENT (src/app/page.tsx)
 * Public marketing landing page displaying APEX Hero section, Features matrix,
 * How-It-Works workflow, live UI preview sections, and Call-To-Action (CTA) triggers.
 */

// --- SECTION 1: Dependencies & Landing Components ---
// Imports React router hooks, landing navbar, hero banner, feature matrices, and icons.
import React from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/landing/Navbar'
import { Hero } from '@/components/landing/Hero'
import { Features } from '@/components/landing/Features'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { PreviewSection } from '@/components/landing/PreviewSection'
import { Terminal, ArrowRight } from 'lucide-react'

// --- SECTION 2: Landing Page View & CTA Handlers ---
// Handles dashboard navigation routing and renders responsive landing page sections.
export default function Home() {
  const router = useRouter()

  const handleCta = () => {
    router.push('/dashboard')
  }

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/30 selection:text-primary-foreground overflow-x-hidden font-sans transition-colors duration-300">
      <Navbar onRequestAccess={handleCta} />
      
      <main>
        <Hero onCta={handleCta} />
        <Features />
        <HowItWorks />
        <PreviewSection />

        {/* Custom Closing CTA Section (HUD Monospace Aesthetic) */}
        <section id="cta" className="relative py-24 border-t border-border/85 bg-background scanlines">
          <div className="absolute inset-0 grid-bg opacity-30 pointer-events-none" />
          <div className="absolute inset-0 radial-glow pointer-events-none" />
          
          <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
            <span className="label-tag block mb-4">// DEPLOYMENT INITIATIVE</span>
            
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight font-display text-foreground uppercase mb-6">
              Establish Account Authority
            </h2>
            
            <p className="text-muted-foreground max-w-lg mx-auto text-sm sm:text-base mb-8 leading-relaxed">
              Connect your CRM, ingest account parameters, and let the APEX planning engine formulate your path to execution.
            </p>

            <div className="flex justify-center">
              <button
                onClick={handleCta}
                className="btn-primary flex items-center gap-2.5 px-8 py-3.5 text-sm uppercase tracking-wider cursor-pointer shadow-lg shadow-primary/10 font-bold"
              >
                <span>Initialize Platform</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Custom Footer (HUD Monospace Aesthetic) */}
      <footer className="relative border-t border-border bg-background/50 py-12 text-xs text-muted-foreground">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-blue-500/10 border border-blue-500/30 flex items-center justify-center">
                <Terminal className="w-3 h-3 text-blue-400" />
              </div>
              <span className="font-mono tracking-wider font-semibold text-muted-foreground">APEX CORE v1.0.4</span>
            </div>
            
            <div className="flex items-center gap-6 font-mono text-[10px]">
              <span className="hover:text-foreground transition-colors cursor-pointer">// PROTOCOL</span>
              <span className="hover:text-foreground transition-colors cursor-pointer">// TERMS</span>
              <span className="hover:text-foreground transition-colors cursor-pointer">// SECURITY</span>
            </div>
            
            <p className="font-mono text-[10px] text-muted-foreground/60">
              © {new Date().getFullYear()} APEX INTELLIGENCE. ALL RIGHTS SECURED.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
