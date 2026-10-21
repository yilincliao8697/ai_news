import type { MetadataRoute } from "next";

// PWA manifest — served by Next.js at /manifest.webmanifest.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI News",
    short_name: "AI News",
    description: "Curated AI, tech, and science articles — summarized.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#111827",
    theme_color: "#111827",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
