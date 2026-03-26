"use client";

import { useEffect, useState } from "react";
import FeedTable, { FeedEntry, formatDate, SOURCE_TYPE_LABELS } from "@/components/FeedTable";
import ThemeToggle from "@/components/ThemeToggle";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function AdminPage() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [keyError, setKeyError] = useState(false);
  const [feeds, setFeeds] = useState<FeedEntry[]>([]);
  const [feedsLoading, setFeedsLoading] = useState(false);
  const [feedsError, setFeedsError] = useState(false);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [newFeed, setNewFeed] = useState({ name: "", url: "", category: "industry", source_type: "" });
  const [addFeedStatus, setAddFeedStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [addFeedError, setAddFeedError] = useState("");

  // Load key from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("adminKey");
    if (stored) setApiKey(stored);
  }, []);

  // Load feeds when key is set
  useEffect(() => {
    if (apiKey) loadFeeds();
  }, [apiKey]);

  function handleUnlock(e: React.FormEvent) {
    e.preventDefault();
    if (!keyInput.trim()) return;
    localStorage.setItem("adminKey", keyInput.trim());
    setApiKey(keyInput.trim());
    setKeyError(false);
  }

  function forgetKey() {
    localStorage.removeItem("adminKey");
    setApiKey(null);
    setKeyInput("");
    setKeyError(false);
  }

  async function loadFeeds() {
    setFeedsLoading(true);
    setFeedsError(false);
    try {
      const res = await fetch(`${API_BASE}/admin/feeds`);
      if (!res.ok) throw new Error();
      setFeeds(await res.json());
    } catch {
      setFeedsError(true);
    } finally {
      setFeedsLoading(false);
    }
  }

  async function runPipeline() {
    if (!apiKey) return;
    setPipelineRunning(true);
    try {
      const res = await fetch(`${API_BASE}/admin/run-pipeline`, {
        method: "POST",
        headers: { "X-Admin-Key": apiKey },
      });
      if (res.status === 401) { forgetKey(); return; }
    } catch {
      // fail silently
    } finally {
      setPipelineRunning(false);
    }
  }

  async function addFeed(e: React.FormEvent) {
    e.preventDefault();
    if (!apiKey) return;
    setAddFeedStatus("loading");
    setAddFeedError("");
    try {
      const res = await fetch(`${API_BASE}/admin/feeds`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Key": apiKey },
        body: JSON.stringify(newFeed),
      });
      if (res.status === 401) { forgetKey(); return; }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setAddFeedError(data.detail ?? "Failed to add feed.");
        setAddFeedStatus("error");
        return;
      }
      setAddFeedStatus("success");
      setNewFeed({ name: "", url: "", category: "industry", source_type: "" });
      await loadFeeds();
    } catch {
      setAddFeedError("Network error.");
      setAddFeedStatus("error");
    }
  }

  async function resetErrors(feedId: number) {
    if (!apiKey) return;
    const res = await fetch(`${API_BASE}/admin/feeds/${feedId}/reset-errors`, {
      method: "POST",
      headers: { "X-Admin-Key": apiKey },
    });
    if (res.status === 401) { forgetKey(); return; }
    if (res.ok) setFeeds((prev) => prev.map((f) => f.id === feedId ? { ...f, error_count: 0 } : f));
  }

  const enabledCount = feeds.filter((f) => f.enabled).length;
  const errorFeeds = feeds.filter((f) => f.error_count > 0);

  // Key gate
  if (!apiKey) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <form onSubmit={handleUnlock} className="flex flex-col gap-3 w-full max-w-xs">
          <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Admin</h1>
          {keyError && (
            <p className="text-sm text-red-500">Invalid key — try again.</p>
          )}
          <input
            type="password"
            placeholder="Enter admin key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
          />
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 hover:opacity-90 transition-opacity"
          >
            Unlock
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Admin</h1>
            <span className="text-sm text-gray-400 dark:text-gray-500">
              {enabledCount} / 30 feeds enabled
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={runPipeline}
              disabled={pipelineRunning}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-opacity ${
                pipelineRunning
                  ? "bg-gray-400 dark:bg-gray-600 text-white cursor-not-allowed animate-pulse"
                  : "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 hover:opacity-90"
              }`}
            >
              {pipelineRunning ? "Running…" : "Rerun all enabled feeds"}
            </button>
            <button
              onClick={forgetKey}
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
            >
              Forget key
            </button>
            <ThemeToggle />
          </div>
        </div>

        <form
          onSubmit={addFeed}
          className="mb-6 p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
        >
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Add Feed</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <input
              type="text"
              placeholder="Name"
              value={newFeed.name}
              onChange={(e) => setNewFeed((f) => ({ ...f, name: e.target.value }))}
              required
              className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
            />
            <input
              type="url"
              placeholder="URL"
              value={newFeed.url}
              onChange={(e) => setNewFeed((f) => ({ ...f, url: e.target.value }))}
              required
              className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
            />
            <select
              value={newFeed.category}
              onChange={(e) => setNewFeed((f) => ({ ...f, category: e.target.value }))}
              className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
            >
              <option value="industry">industry</option>
              <option value="research">research</option>
              <option value="science">science</option>
            </select>
            <input
              type="text"
              placeholder="Group (e.g. major_media)"
              value={newFeed.source_type}
              onChange={(e) => setNewFeed((f) => ({ ...f, source_type: e.target.value }))}
              required
              className="px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm">
              {addFeedStatus === "success" && (
                <span className="text-green-600 dark:text-green-400">Feed added.</span>
              )}
              {addFeedStatus === "error" && (
                <span className="text-red-500">{addFeedError}</span>
              )}
            </div>
            <button
              type="submit"
              disabled={addFeedStatus === "loading"}
              className="px-4 py-2 text-sm font-medium rounded-md bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {addFeedStatus === "loading" ? "Adding…" : "Add Feed"}
            </button>
          </div>
        </form>

        {feedsLoading ? (
          <div className="flex flex-col items-center gap-1 mt-8 animate-pulse">
            <p className="text-gray-400 dark:text-gray-500 text-sm">Loading feeds…</p>
            <p className="text-gray-400 dark:text-gray-500 text-xs">This may take a few minutes…</p>
          </div>
        ) : feedsError ? (
          <div className="flex flex-col items-center mt-16 gap-3">
            <p className="text-gray-500 dark:text-gray-400 text-sm">Failed to load feeds.</p>
            <button
              onClick={loadFeeds}
              className="px-4 py-2 text-sm font-medium rounded-md bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900 hover:opacity-90"
            >
              Retry
            </button>
          </div>
        ) : (
          <FeedTable feeds={feeds} apiKey={apiKey} />
        )}

        {errorFeeds.length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Feeds with errors</h2>
            <ul className="space-y-2">
              {errorFeeds.map((feed) => (
                <li key={feed.id} className="flex items-center justify-between px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-sm">
                  <span className="text-gray-800 dark:text-gray-200">{feed.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-red-500 font-medium">{feed.error_count} error{feed.error_count !== 1 ? "s" : ""}</span>
                    <button
                      onClick={() => resetErrors(feed.id)}
                      className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 px-2 py-0.5 rounded"
                    >
                      Reset
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
