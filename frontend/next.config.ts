/**
 * NEXT.JS FRAMEWORK CONFIGURATION (next.config.ts)
 * Configures environment URL cleaners, response compression, and API proxy rewrites
 * routing `/auth/*` traffic to Port 8001 and `/api/*` traffic to Port 8002.
 */

// --- SECTION 1: Dependencies & Environment Resolution ---
// Imports NextConfig types and cleans backend/auth microservice destination URLs.
import type { NextConfig } from "next";

const cleanUrl = (url: string) => url.replace(/\/+$/, "");
const BACKEND_URL = cleanUrl(process.env.BACKEND_URL || 'http://127.0.0.1:8002');
const AUTH_URL = cleanUrl(process.env.AUTH_URL || (process.env.BACKEND_URL ? process.env.BACKEND_URL : 'http://127.0.0.1:8001'));

// --- SECTION 2: Next.js Configuration & Proxy Rewrites ---
// Configures Next.js build parameters and dynamic reverse-proxy rewrite rules.
const nextConfig: NextConfig = {
  compress: false,
  async rewrites() {
    return [
      {
        source: '/auth/:path*',
        destination: `${AUTH_URL}/auth/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

