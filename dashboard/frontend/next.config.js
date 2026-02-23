/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Use this directory as project root when multiple lockfiles exist (e.g. monorepo / CI)
  turbopack: {
    root: __dirname,
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

