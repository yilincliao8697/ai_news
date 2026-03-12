import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI News",
  description: "Curated AI, tech, and science articles — summarized.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
