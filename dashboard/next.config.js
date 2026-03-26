/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/gold/:path*',
        destination: `${process.env.GOLD_API_URL || 'http://127.0.0.1:8000'}/api/:path*`,
      },
      {
        source: '/api/forex/:path*',
        destination: `${process.env.FOREX_API_URL || 'http://127.0.0.1:8001'}/api/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
