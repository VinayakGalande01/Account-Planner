'use client';

// LEGACY/BACKUP FILE — not part of the active build (frontend/src is the live app).
// Original Canvas2D background effect: a fixed full-viewport dot grid whose points
// are repelled by the mouse and spring back to their base position, with brightness
// and radius scaling by displacement for a subtle glow effect.
//
// --- SECTION: Point Type & Physics Constants ---
// --- SECTION: initPoints — builds the dot grid on resize ---
// --- SECTION: animate — per-frame physics update + canvas draw ---
// --- SECTION: Effect Setup (resize/mouse listeners, RAF loop) & Render ---

import React, { useRef, useEffect, useCallback } from 'react';

interface Point {
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  vx: number;
  vy: number;
}

export default function InteractiveGrid() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const pointsRef = useRef<Point[]>([]);
  const rafRef = useRef<number>(0);

  const DOT_SPACING = 32;
  const DOT_RADIUS = 1;
  const INFLUENCE_RADIUS = 120;
  const SPRING = 0.03;
  const DAMPING = 0.9;

  const initPoints = useCallback((w: number, h: number) => {
    const pts: Point[] = [];
    const cols = Math.ceil(w / DOT_SPACING) + 2;
    const rows = Math.ceil(h / DOT_SPACING) + 2;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = c * DOT_SPACING;
        const y = r * DOT_SPACING;
        pts.push({ x, y, baseX: x, baseY: y, vx: 0, vy: 0 });
      }
    }
    pointsRef.current = pts;
  }, []);

  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    const mouse = mouseRef.current;
    const points = pointsRef.current;

    for (const p of points) {
      // Mouse influence
      const dx = p.baseX - mouse.x;
      const dy = p.baseY - mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < INFLUENCE_RADIUS) {
        const force = (1 - dist / INFLUENCE_RADIUS) * 8;
        const angle = Math.atan2(dy, dx);
        p.vx += Math.cos(angle) * force;
        p.vy += Math.sin(angle) * force;
      }

      // Spring back
      p.vx += (p.baseX - p.x) * SPRING;
      p.vy += (p.baseY - p.y) * SPRING;

      // Damping
      p.vx *= DAMPING;
      p.vy *= DAMPING;

      // Apply
      p.x += p.vx;
      p.y += p.vy;

      // Displacement for brightness
      const displacement = Math.sqrt(
        (p.x - p.baseX) ** 2 + (p.y - p.baseY) ** 2
      );
      const brightness = Math.min(0.35, 0.06 + displacement * 0.02);
      const blueFactor = Math.min(1, displacement * 0.05);

      // Draw dot
      ctx.beginPath();
      ctx.arc(p.x, p.y, DOT_RADIUS + displacement * 0.04, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${37 + blueFactor * 40}, ${99 + blueFactor * 30}, ${235}, ${brightness})`;
      ctx.fill();
    }

    rafRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.scale(dpr, dpr);
      initPoints(window.innerWidth, window.innerHeight);
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseLeave = () => {
      mouseRef.current = { x: -1000, y: -1000 };
    };

    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(rafRef.current);
    };
  }, [initPoints, animate]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.7 }}
    />
  );
}
