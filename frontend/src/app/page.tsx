'use client'

import { motion } from 'framer-motion'
import { ArrowRight, BarChart3, Brain, CheckCircle2, Lock, Zap, TrendingUp, Users, Lightbulb, Target, Clock, Star, Menu, X } from 'lucide-react'
import Image from 'next/image'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { FeatureCard } from '@/components/feature-card'
import { TestimonialCard } from '@/components/testimonial-card'
import { AnimatedCounter } from '@/components/animated-counter'

export default function Home() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const router = useRouter()

  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-black to-zinc-950">
      {/* Floating background shapes */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <motion.div
          animate={{ y: [0, 40, 0] }}
          transition={{ duration: 6, repeat: Infinity }}
          className="absolute right-10 top-20 size-96 rounded-full bg-white/5 blur-3xl"
        />
        <motion.div
          animate={{ y: [0, -30, 0] }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute left-10 bottom-20 size-72 rounded-full bg-zinc-500/10 blur-3xl"
        />
      </div>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2 text-2xl font-bold text-zinc-100"
            >
              <Image src="/logo.png" alt="APEX Logo" width={40} height={40} className="object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] brightness-125" priority />
              APEX
            </motion.div>

            {/* Desktop Menu */}
            <div className="hidden gap-8 md:flex">
              {['Features', 'Solution', 'Pricing', 'Company'].map((item, i) => (
                <motion.a
                  key={item}
                  href={`#${item.toLowerCase()}`}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="text-zinc-400 transition-colors hover:text-white"
                >
                  {item}
                </motion.a>
              ))}
            </div>

            <motion.button
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              onClick={() => router.push('/dashboard')}
              className="hidden rounded-lg bg-white px-6 py-2 font-medium text-black transition-all hover:bg-zinc-200 hover:shadow-lg hover:shadow-white/10 md:block"
            >
              Get Started
            </motion.button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden text-zinc-400 hover:text-white"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="border-t border-white/10 py-4 md:hidden"
            >
              <div className="flex flex-col gap-4">
                {['Features', 'Solution', 'Pricing', 'Company'].map((item) => (
                  <a
                    key={item}
                    href={`#${item.toLowerCase()}`}
                    className="text-zinc-400 transition-colors hover:text-white"
                  >
                    {item}
                  </a>
                ))}
                <button onClick={() => router.push('/dashboard')} className="rounded-lg bg-white px-6 py-2 font-medium text-black transition-all hover:bg-zinc-200 w-full">
                  Get Started
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-20">
        {/* Hero Section */}
        <section className="py-12 sm:py-20">
          <div className="grid gap-8 lg:grid-cols-2 lg:gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
            >
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-zinc-300"
              >
                <Zap className="size-4" />
                <span>Powered by Advanced AI</span>
              </motion.div>
              <h1 className="mb-6 text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight">
                <span className="bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
                  Account Planning
                </span>
                {' '}
                <span className="text-white">Reimagined</span>
              </h1>
              <p className="mb-8 text-lg text-zinc-400 leading-relaxed">
                APEX uses AI-powered intelligence to help you streamline account planning and execution. Make smarter decisions, faster.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => router.push('/dashboard')}
                  className="flex items-center justify-center gap-2 rounded-lg bg-white px-8 py-3 font-semibold text-black transition-all hover:bg-zinc-200 hover:shadow-lg hover:shadow-white/10"
                >
                  Start Free Trial
                  <ArrowRight className="size-5" />
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="rounded-lg border border-white/10 px-8 py-3 font-semibold text-zinc-200 transition-all hover:border-white/20 hover:bg-zinc-950"
                >
                  Watch Demo
                </motion.button>
              </div>
            </motion.div>

            {/* Hero Image - Browser Mockup */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative"
            >
              <div className="rounded-xl border border-white/10 bg-zinc-900 p-4 shadow-2xl">
                <div className="flex gap-2 mb-4">
                  <div className="size-3 rounded-full bg-red-500" />
                  <div className="size-3 rounded-full bg-yellow-500" />
                  <div className="size-3 rounded-full bg-green-500" />
                </div>
                <div className="aspect-video rounded-lg bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center">
                  <div className="text-center">
                    <BarChart3 className="size-12 text-zinc-100 mx-auto mb-4" />
                    <p className="text-zinc-400">Interactive Dashboard Preview</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Features Grid */}
        <section id="features" className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-16 text-center"
          >
            <h2 className="mb-4 text-3xl sm:text-4xl font-bold text-white">
              Powerful Features for Smart Planning
            </h2>
            <p className="mx-auto max-w-2xl text-lg text-zinc-400">
              Everything you need to manage accounts with intelligence and precision
            </p>
          </motion.div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Brain className="size-6" />}
              title="AI-Powered Insights"
              description="Get intelligent recommendations and predictive analytics powered by machine learning."
              delay={0}
            />
            <FeatureCard
              icon={<TrendingUp className="size-6" />}
              title="Revenue Intelligence"
              description="Track and optimize revenue outcomes with real-time forecasting and pipeline visibility."
              delay={0.1}
            />
            <FeatureCard
              icon={<Users className="size-6" />}
              title="Team Collaboration"
              description="Enable seamless collaboration across sales, marketing, and customer success teams."
              delay={0.2}
            />
            <FeatureCard
              icon={<Target className="size-6" />}
              title="Strategic Planning"
              description="Create and execute comprehensive account strategies with guided workflows."
              delay={0.3}
            />
            <FeatureCard
              icon={<Lock className="size-6" />}
              title="Enterprise Security"
              description="Industry-leading security with SOC 2 compliance and encryption at rest."
              delay={0.4}
            />
            <FeatureCard
              icon={<Zap className="size-6" />}
              title="Real-Time Sync"
              description="Stay synchronized with real-time data integration and instant updates."
              delay={0.5}
            />
          </div>
        </section>

        {/* Solution Workflow */}
        <section id="solution" className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-16 text-center"
          >
            <h2 className="mb-4 text-3xl sm:text-4xl font-bold text-white">
              How APEX Works
            </h2>
            <p className="mx-auto max-w-2xl text-lg text-zinc-400">
              A simple yet powerful workflow to transform your account planning
            </p>
          </motion.div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { step: 1, title: 'Connect', description: 'Integrate your CRM and data sources' },
              { step: 2, title: 'Analyze', description: 'AI analyzes your accounts and opportunities' },
              { step: 3, title: 'Plan', description: 'Create intelligent account strategies' },
              { step: 4, title: 'Execute', description: 'Execute with real-time monitoring' },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                viewport={{ once: true }}
                className="relative text-center"
              >
                <div className="mb-4 inline-flex size-16 items-center justify-center rounded-full bg-blue-500/20 text-2xl font-bold text-zinc-100">
                  {item.step}
                </div>
                <h3 className="mb-2 text-lg font-semibold text-white">{item.title}</h3>
                <p className="text-zinc-400">{item.description}</p>
                {i < 3 && (
                  <motion.div
                    animate={{ x: [0, 8, 0] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute -right-4 top-1/3 hidden lg:block text-white"
                  >
                    <ArrowRight className="size-6" />
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="rounded-xl border border-white/10 bg-slate-800/30 p-8 sm:p-12"
          >
            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4 text-center">
              <div>
                <p className="mb-2 text-4xl sm:text-5xl font-bold text-zinc-100">
                  <AnimatedCounter from={0} to={5} suffix="k+" />
                </p>
                <p className="text-zinc-400">Active Users</p>
              </div>
              <div>
                <p className="mb-2 text-4xl sm:text-5xl font-bold text-cyan-400">
                  <AnimatedCounter from={0} to={99} suffix="%" delay={0.2} />
                </p>
                <p className="text-zinc-400">Uptime SLA</p>
              </div>
              <div>
                <p className="mb-2 text-4xl sm:text-5xl font-bold text-emerald-400">
                  <AnimatedCounter from={0} to={3} suffix="x" delay={0.4} />
                </p>
                <p className="text-zinc-400">Revenue Growth</p>
              </div>
              <div>
                <p className="mb-2 text-4xl sm:text-5xl font-bold text-amber-400">
                  <AnimatedCounter from={0} to={180} suffix="+" delay={0.6} />
                </p>
                <p className="text-zinc-400">Enterprise Clients</p>
              </div>
            </div>
          </motion.div>
        </section>

        {/* Comparison Table */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-12 text-center"
          >
            <h2 className="mb-4 text-3xl sm:text-4xl font-bold text-white">
              Why Choose APEX?
            </h2>
            <p className="mx-auto max-w-2xl text-lg text-zinc-400">
              Compare APEX with traditional approaches
            </p>
          </motion.div>

          <div className="overflow-x-auto rounded-lg border border-white/10 bg-black/50">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-6 py-4 font-semibold text-white">Feature</th>
                  <th className="px-6 py-4 font-semibold text-white">APEX</th>
                  <th className="px-6 py-4 font-semibold text-white">Traditional Tools</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { feature: 'AI-Powered Planning', apex: true, traditional: false },
                  { feature: 'Real-Time Forecasting', apex: true, traditional: false },
                  { feature: 'Predictive Analytics', apex: true, traditional: false },
                  { feature: 'Team Collaboration', apex: true, traditional: true },
                  { feature: 'CRM Integration', apex: true, traditional: true },
                  { feature: 'Enterprise Security', apex: true, traditional: true },
                ].map((row, i) => (
                  <tr key={i} className="border-b border-white/10 hover:bg-slate-800/30">
                    <td className="px-6 py-4 text-white">{row.feature}</td>
                    <td className="px-6 py-4">
                      {row.apex ? (
                        <CheckCircle2 className="size-5 text-emerald-500" />
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {row.traditional ? (
                        <CheckCircle2 className="size-5 text-zinc-500" />
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Testimonials */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="mb-12 text-center"
          >
            <h2 className="mb-4 text-3xl sm:text-4xl font-bold text-white">
              Loved by Enterprise Leaders
            </h2>
            <p className="mx-auto max-w-2xl text-lg text-zinc-400">
              See what our customers say about APEX
            </p>
          </motion.div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <TestimonialCard
              quote="APEX transformed how we approach account planning. We&apos;ve seen a 3x improvement in deal closure rates."
              author="Sarah Chen"
              title="VP Sales"
              company="TechCorp"
              delay={0}
            />
            <TestimonialCard
              quote="The AI insights are incredible. It&apos;s like having a team of data scientists working for us 24/7."
              author="Michael Rodriguez"
              title="Sales Director"
              company="Enterprise Solutions"
              delay={0.1}
            />
            <TestimonialCard
              quote="Implementation was smooth, and the ROI was evident within the first month. Highly recommended."
              author="Jessica Liu"
              title="Chief Revenue Officer"
              company="Growth Analytics"
              delay={0.2}
            />
          </div>
        </section>

        {/* Security Section */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="rounded-xl border border-white/10 bg-slate-800/30 p-8 sm:p-12 text-center"
          >
            <Lock className="size-12 text-zinc-100 mx-auto mb-6" />
            <h2 className="mb-4 text-3xl font-bold text-white">
              Enterprise-Grade Security
            </h2>
            <p className="mx-auto mb-8 max-w-2xl text-zinc-400">
              We comply with SOC 2 Type II, GDPR, and HIPAA standards. Your data is encrypted, backed up, and protected.
            </p>
            <div className="flex flex-wrap justify-center gap-6">
              {['SOC 2 Type II', 'GDPR Compliant', 'HIPAA Ready', '99.99% Uptime'].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-black/50 px-4 py-2 text-zinc-300"
                >
                  <CheckCircle2 className="size-4 text-emerald-500" />
                  {item}
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Final CTA */}
        <section className="py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="rounded-xl border border-white/10 bg-white/5 p-8 sm:p-16 text-center"
          >
            <h2 className="mb-4 text-3xl sm:text-4xl font-bold text-white">
              Ready to Transform Your Account Planning?
            </h2>
            <p className="mb-8 text-lg text-zinc-400">
              Join thousands of enterprise teams using APEX to drive smarter revenue growth.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => router.push('/dashboard')}
                className="flex items-center justify-center gap-2 rounded-lg bg-white px-8 py-3 font-semibold text-black transition-all hover:bg-zinc-200"
              >
                Start Free Trial Today
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="rounded-lg border border-white/10 px-8 py-3 font-semibold text-zinc-200 transition-all hover:border-white/20 hover:bg-zinc-950"
              >
                Schedule a Demo
              </motion.button>
            </div>
          </motion.div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-black/50 py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <div>
              <h3 className="mb-4 font-bold text-white">Product</h3>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="#" className="transition-colors hover:text-white">Features</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Pricing</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Security</a></li>
              </ul>
            </div>
            <div>
              <h3 className="mb-4 font-bold text-white">Company</h3>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="#" className="transition-colors hover:text-white">About</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Blog</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Careers</a></li>
              </ul>
            </div>
            <div>
              <h3 className="mb-4 font-bold text-white">Resources</h3>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="#" className="transition-colors hover:text-white">Docs</a></li>
                <li><a href="#" className="transition-colors hover:text-white">API</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Support</a></li>
              </ul>
            </div>
            <div>
              <h3 className="mb-4 font-bold text-white">Legal</h3>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><a href="#" className="transition-colors hover:text-white">Privacy</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Terms</a></li>
                <li><a href="#" className="transition-colors hover:text-white">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-white/10 pt-8 text-center text-sm text-zinc-400">
            <p>&copy; 2026 APEX. All rights reserved. Crafted with intelligence for enterprise sales teams.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
