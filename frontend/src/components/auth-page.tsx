'use client';

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, Mail, User, ShieldAlert, Eye, EyeOff, ArrowRight } from 'lucide-react';
import Image from 'next/image';

export default function AuthPage() {
  const { login, signup, error, loading, isTransitioning, transitionType } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  
  // Fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!email || !password) {
      setValidationError('Please enter your email and password.');
      return;
    }

    if (password.length < 8) {
      setValidationError('Password must be at least 8 characters.');
      return;
    }

    if (!isLogin && !name) {
      setValidationError('Please enter your name.');
      return;
    }

    if (isLogin) {
      await login(email, password);
    } else {
      await signup(name, email, password);
    }
  };

  return (
    <div className="relative min-h-screen bg-black text-foreground overflow-hidden flex flex-col justify-center items-center px-4">
      {/* Topographic scan line details */}
      <div className="absolute inset-0 opacity-[0.8] pointer-events-none z-10" />
      
      {/* Ambient backgrounds */}
      <div className="fixed top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-primary/[0.04] rounded-full blur-[100px] pointer-events-none z-0" />
      <div className="fixed bottom-10 right-10 w-[400px] h-[200px] bg-secondary/[0.03] rounded-full blur-[80px] pointer-events-none z-0" />

      {/* Main card wrapper or Splash screen */}
      <AnimatePresence mode="wait">
        {!isTransitioning ? (
          <motion.div 
            key="login-form"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, filter: "blur(10px)" }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="bg-zinc-950/80 backdrop-blur-xl border border-white/10 relative z-20 w-full max-w-[420px] p-8 rounded-xl shadow-2xl group"
          >
        {/* Glow corners */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-white/20 rounded-tl-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-white/20 rounded-tr-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-white/20 rounded-bl-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-white/20 rounded-br-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />

        {/* Logo and Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 mb-4">
             <Image src="/logo.png" alt="APEX Logo" width={80} height={80} className="object-contain drop-shadow-[0_0_20px_rgba(255,255,255,0.2)] brightness-125" priority />
          </div>
          <h2 className="text-[15px] font-black tracking-[0.15em] text-white uppercase font-[family-name:var(--font-mono)]">
            {isLogin ? 'Sign In' : 'Create Your Account'}
          </h2>
          <p className="text-[11px] text-zinc-400 font-medium mt-1">
            {isLogin ? 'Sign in to your account to continue' : 'Sign up to get started'}
          </p>
        </div>

        {/* Error States */}
        <AnimatePresence mode="wait">
          {(error || validationError) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              role="alert"
              aria-live="polite"
              className="mb-5 p-3 rounded-md bg-red-500/10 border border-red-500/20 flex items-start gap-2.5"
            >
              <ShieldAlert className="w-4 h-4 text-red-500 shrink-0 mt-0.5" aria-hidden="true" />
              <span className="text-[11px] text-red-400 font-bold uppercase tracking-[0.05em] leading-normal font-[family-name:var(--font-mono)]">
                {validationError || error}
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input Forms */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="popLayout">
            {!isLogin && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-1"
              >
                <label htmlFor="auth-name" className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" aria-hidden="true" />
                  <input
                    id="auth-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your full name"
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-md text-[12px] placeholder:text-zinc-400 focus:outline-none focus:border-white/30 focus:bg-white/10 text-white transition-all font-[family-name:var(--font-mono)]"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="space-y-1">
            <label htmlFor="auth-email" className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" aria-hidden="true" />
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email address"
                className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-md text-[12px] placeholder:text-zinc-400 focus:outline-none focus:border-white/30 focus:bg-white/10 text-white transition-all font-[family-name:var(--font-mono)]"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="auth-password" className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" aria-hidden="true" />
              <input
                id="auth-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full pl-10 pr-10 py-2.5 bg-white/5 border border-white/10 rounded-md text-[12px] placeholder:text-zinc-400 focus:outline-none focus:border-white/30 focus:bg-white/10 text-white transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-white transition-colors focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" aria-hidden="true" /> : <Eye className="w-3.5 h-3.5" aria-hidden="true" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full group/btn relative mt-6 py-3 bg-primary text-black text-[11px] font-black uppercase tracking-[0.25em] rounded-md overflow-hidden transition-all duration-300 hover:bg-zinc-200 hover:shadow-[0_0_25px_rgba(255,255,255,0.15)] disabled:opacity-50 disabled:cursor-not-allowed font-[family-name:var(--font-mono)]"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3 h-3 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                Please wait...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                {isLogin ? 'Sign In' : 'Sign Up'}
                <ArrowRight className="w-3.5 h-3.5 group-hover/btn:translate-x-0.5 transition-transform" />
              </span>
            )}
          </button>
        </form>

        {/* Toggle Mode */}
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setValidationError(null);
            }}
            className="text-[11px] text-zinc-400 hover:text-white uppercase tracking-[0.05em] font-[family-name:var(--font-mono)] transition-colors"
          >
            {isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Sign In'}
          </button>
        </div>
      </motion.div>
        ) : (
          <motion.div
            key="success-splash"
            initial={{ opacity: 0, scale: 0.9, filter: "blur(10px)" }}
            animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="relative z-20 flex flex-col items-center justify-center"
          >
            <div className="mb-8 w-24 h-24">
              <Image src="/logo.png" alt="APEX Logo" width={96} height={96} className="object-contain drop-shadow-[0_0_30px_rgba(255,255,255,0.3)] brightness-125" priority />
            </div>
            
            <motion.div 
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", bounce: 0.5, delay: 0.2 }}
              className={`w-16 h-16 rounded-full mb-8 flex items-center justify-center ${transitionType === 'login' ? 'bg-emerald-500/20' : 'bg-blue-500/20'}`}
            >
               <div className={`w-8 h-8 rounded-full animate-pulse ${transitionType === 'login' ? 'bg-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.8)]' : 'bg-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.8)]'}`} />
            </motion.div>
            
            <motion.h2 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-2xl sm:text-3xl font-black tracking-[0.1em] text-white uppercase font-[family-name:var(--font-mono)] mb-3 text-center"
            >
              {transitionType === 'login' ? "Welcome Back" : "Account Created"}
            </motion.h2>
            
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-zinc-400 font-medium text-center uppercase tracking-[0.2em] text-[11px] sm:text-[13px]"
            >
              {transitionType === 'login' ? "Initializing Intelligence Engine..." : "Preparing your workspace for launch..."}
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
