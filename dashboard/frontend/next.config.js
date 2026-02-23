/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Use this directory as project root when multiple lockfiles exist (e.g. monorepo / CI)
  // Next.js 16+ Turbopack: explicit root and path alias so @/ resolves to src/
  turbopack: {
    root: __dirname,
    resolveAlias: {
      '@': require('path').resolve(__dirname, 'src'),
    },
  },
  // Ensure webpack build also resolves @/ (e.g. if Turbopack is disabled)
  webpack: (config, { isServer }) => {
    config.resolve.alias = config.resolve.alias || {};
    config.resolve.alias['@'] = require('path').resolve(__dirname, 'src');
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;

