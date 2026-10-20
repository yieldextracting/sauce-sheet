import type { NextConfig } from "next";

// Classic static generation: every page is prerendered from the JSON in data/ at build time.
// Each pipeline commit triggers a Vercel rebuild, which is how the site updates.
const nextConfig: NextConfig = {
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
