import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/auth/:path*',
        destination: 'http://127.0.0.1:8001/auth/:path*',
      },
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8002/api/:path*',
      },
    ];
  },
};

export default nextConfig;
