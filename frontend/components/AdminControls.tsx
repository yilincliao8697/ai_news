"use client";

import { useState } from "react";
import { FeedEntry, SOURCE_TYPE_LABELS, formatDate } from "@/components/FeedTable";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Props = {
  initialFeeds: FeedEntry[];
};

export default function AdminControls({ initialFeeds }: Props) {
  const [feeds, setFeeds] = useState<FeedEntry[]>(initialFeeds);
  const [pipelineStatus, setPipelineStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const [pipelineResult, setPipelineResult] = useState<string | null>(null);

  async function runPipeline() {
    setPipelineStatus("running");
    try {
      const res = await fetch(`${API_BASE}/admin/run-pipeline`, { method: "POST" });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setPipelineResult(`Pipeline complete — ${data.saved} new articles saved.`);
      setPipelineStatus("success");
    } catch {
      setPipelineResult("Pipeline failed. Check logs.");
      setPipelineStatus("error");
    } finally {
      setTimeout(() => {
        setPipelineStatus("idle");
        setPipelineResult(null);
      }, 5000);
    }
  }

  async function resetErrors(feedId: number) {
    try {
      const res = await fetch(`${API_BASE}/admin/feeds/${feedId}/reset-errors`, { method: "POST" });
      if (!res.ok) throw new Error();
      setFeeds((prev) =>
        prev.map((f) => (f.id === feedId ? { ...f, error_count: 0 } : f))
      );
    } catch (e) {
      console.error(e);
    }
  }

  const erroredFeeds = feeds.filter((f) => f.error_count > 0);

  return (
    <>
      {/* Pipeline trigger */}
      <div className="flex items-center gap-3 mb-1">
        <button
          onClick={runPipeline}
          disabled={pipelineStatus === "running"}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            pipelineStatus === "running"
              ? "bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed"
              : "bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 hover:bg-gray-700 dark:hover:bg-gray-300"
          }`}
        >
          {pipelineStatus === "running" ? "Running…" : "Run Pipeline Now"}
        </button>
        {pipelineResult && (
          <span className={`text-sm ${
            pipelineStatus === "error"
              ? "text-red-600 dark:text-red-400"
              : "text-green-600 dark:text-green-400"
          }`}>
            {pipelineResult}
          </span>
        )}
      </div>

      {/* Error monitoring */}
      {erroredFeeds.length > 0 && (
        <section className="mt-6 mb-6 rounded-lg border border-red-200 dark:border-red-800 overflow-hidden">
          <div className="px-4 py-3 bg-red-50 dark:bg-red-950">
            <h2 className="text-sm font-semibold text-red-700 dark:text-red-400">
              {erroredFeeds.length} feed{erroredFeeds.length > 1 ? "s" : ""} with errors
            </h2>
          </div>
          <table className="min-w-full text-sm divide-y divide-red-100 dark:divide-red-900">
            <thead className="bg-white dark:bg-gray-900">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Feed</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Group</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Errors</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Last Fetched</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-red-50 dark:divide-red-900 bg-white dark:bg-gray-900">
              {erroredFeeds.map((feed) => (
                <tr key={feed.id}>
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{feed.name}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                    {SOURCE_TYPE_LABELS[feed.source_type] ?? feed.source_type}
                  </td>
                  <td className="px-4 py-3 text-red-500 font-medium">{feed.error_count}</td>
                  <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{formatDate(feed.last_fetched)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => resetErrors(feed.id)}
                      className="text-xs text-gray-500 dark:text-gray-400 border border-gray-300 dark:border-gray-600 px-2 py-0.5 rounded hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                    >
                      Reset errors
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
