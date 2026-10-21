"use client";

import { useEffect } from "react";

// Registers the PWA service worker (public/sw.js). Production only, so dev
// reloads never serve stale cached pages.
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.error("Service worker registration failed:", err);
    });
  }, []);

  return null;
}
