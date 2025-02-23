import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Warning: This allows production builds to succeed even if there are ESLint errors.
    ignoreDuringBuilds: true,
  },
  /* other config options here */
};

export default nextConfig;
