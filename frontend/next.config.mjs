/** @type {import('next').NextConfig} */
const django = process.env.DJANGO_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  output: "standalone",
  // Existing invite links look like /join/CODE/ — keep the trailing slash.
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  poweredByHeader: false,
  // In production the gateway sends /api, /admin, /s/ … to Django before Next sees them.
  // These rewrites only matter for `next dev` without the gateway.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${django}/api/:path*` },
      { source: "/admin/:path*", destination: `${django}/admin/:path*` },
      { source: "/static/:path*", destination: `${django}/static/:path*` },
    ];
  },
};

export default nextConfig;
