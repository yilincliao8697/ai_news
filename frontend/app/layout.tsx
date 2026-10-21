import type { Metadata, Viewport } from "next";
import { Analytics } from "@vercel/analytics/next";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI News",
  description: "Curated AI, tech, and science articles — summarized.",
  icons: { apple: "/icons/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: "#111827",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        {children}
        <Analytics />
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
