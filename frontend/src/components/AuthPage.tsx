'use client';

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Lock, Mail, User, Cpu, Sparkles, ArrowRight, ShieldAlert, Eye, EyeOff, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';



interface AuthPageProps {
  onBack?: () => void;
}

export default function AuthPage({ onBack }: AuthPageProps) {
  const { login, signup, error, loading } = useAuth();
  const { theme, toggleTheme } = useTheme();
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
    <div className="relative min-h-screen bg-background text-foreground overflow-hidden flex flex-col justify-center items-center px-4 transition-colors duration-200">
      {/* Theme Toggle Button */}
      <div className="absolute top-4 right-4 z-30">
        <button
          type="button"
          onClick={toggleTheme}
          className="p-2 text-zinc-500 hover:text-primary hover:bg-muted dark:hover:bg-white/[0.03] rounded-md transition-all duration-150 flex items-center justify-center border border-border bg-card shadow-sm"
          title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      {/* Topographic scan line details */}
      <div className="absolute inset-0 scanlines opacity-[0.8] pointer-events-none z-10" />
      
      {/* Ambient backgrounds */}
      <div className="fixed top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-primary/[0.04] rounded-full blur-[100px] pointer-events-none z-0" />
      <div className="fixed bottom-10 right-10 w-[400px] h-[200px] bg-secondary/[0.03] rounded-full blur-[80px] pointer-events-none z-0" />

      {/* Main card wrapper */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="glass-card relative z-20 w-full max-w-[420px] p-8 shadow-2xl shadow-primary/5 group"
      >
        {/* Glow corners */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-primary/45 rounded-tl-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-primary/45 rounded-tr-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-primary/45 rounded-bl-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-primary/45 rounded-br-xl transition-all duration-300 group-hover:w-6 group-hover:h-6" />

        {/* Logo and Header */}
        <div className="flex flex-col items-center mb-8">
          <img src="/apex-logo.png" alt="APEX Logo" className="w-16 h-16 object-contain mb-2 drop-shadow-[0_0_15px_rgba(37,99,235,0.5)]" />
          <h2 className="text-[15px] font-black tracking-[0.15em] text-primary uppercase font-[family-name:var(--font-mono)]">
            {isLogin ? 'Sign In' : 'Create Your Account'}
          </h2>
          <p className="text-[11px] text-zinc-500 font-medium mt-1">
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
              className="mb-5 p-3 rounded-md bg-red-500/10 border border-red-500/20 flex items-start gap-2.5"
            >
              <ShieldAlert className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
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
                <label className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your full name"
                    className="w-full pl-10 pr-4 py-2.5 bg-white/[0.02] border border-white/[0.06] rounded-md text-[12px] placeholder:text-zinc-500 focus:outline-none focus:border-primary/50 focus:bg-white/[0.04] transition-all font-[family-name:var(--font-mono)]"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="space-y-1">
            <label className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email address"
                className="w-full pl-10 pr-4 py-2.5 bg-white/[0.02] border border-white/[0.06] rounded-md text-[12px] placeholder:text-zinc-500 focus:outline-none focus:border-primary/50 focus:bg-white/[0.04] transition-all font-[family-name:var(--font-mono)]"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.15em] font-[family-name:var(--font-mono)]">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full pl-10 pr-10 py-2.5 bg-white/[0.02] border border-white/[0.06] rounded-md text-[12px] placeholder:text-zinc-500 focus:outline-none focus:border-primary/50 focus:bg-white/[0.04] transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-primary transition-colors focus:outline-none"
              >
                {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full group/btn relative mt-6 py-3 bg-primary text-white text-[11px] font-black uppercase tracking-[0.25em] rounded-md overflow-hidden transition-all duration-300 hover:shadow-[0_0_25px_rgba(37,99,235,0.3)] disabled:opacity-50 disabled:cursor-not-allowed font-[family-name:var(--font-mono)]"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
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
            className="text-[11px] text-zinc-500 hover:text-primary uppercase tracking-[0.05em] font-[family-name:var(--font-mono)] transition-colors"
          >
            {isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Sign In'}
          </button>
        </div>

        {onBack && (
          <div className="mt-4 text-center border-t border-white/[0.04] pt-4">
            <button
              type="button"
              onClick={onBack}
              className="text-[10px] text-zinc-600 hover:text-primary uppercase tracking-widest font-[family-name:var(--font-mono)] transition-colors cursor-pointer"
            >
              ← Back to Home
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
