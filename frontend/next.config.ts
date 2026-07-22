import type { NextConfig } from "next";

const cleanUrl = (url: string) => url.replace(/\/+$/, "");
const BACKEND_URL = cleanUrl(process.env.BACKEND_URL || 'http://127.0.0.1:8002');
const AUTH_URL = cleanUrl(process.env.AUTH_URL || (process.env.BACKEND_URL ? process.env.BACKEND_URL : 'http://127.0.0.1:8001'));

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
