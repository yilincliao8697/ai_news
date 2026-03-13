"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type RecentArticle = {
  title: string;
  link: string;
  created_at: string;
};

export type FeedEntry = {
  id: number;
  name: string;
  url: string;
  category: string;
  enabled: boolean;
  last_fetched: string | null;
  error_count: number;
  recent_articles: RecentArticle[];
};

const CATEGORY_COLORS: Record<string, string> = {
  research: "bg-purple-100 text-purple-700",
  industry: "bg-blue-100 text-blue-700",
  science:  "bg-green-100 text-green-700",
};

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

type Props = { feeds: FeedEntry[] };

export default function FeedTable({ feeds: initialFeeds }: Props) {
  const [feeds, setFeeds] = useState<FeedEntry[]>(initialFeeds);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState<number | null>(null);

  async function toggleFeed(id: number, currentEnabled: boolean) {
    setLoading(id);
    try {
      const res = await fetch(`${API_BASE}/admin/feeds/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (!res.ok) throw new Error("Toggle failed");
      setFeeds((prev) =>
        prev.map((f) => (f.id === id ? { ...f, enabled: !currentEnabled } : f))
      );
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Feed</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Category</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Last Fetched</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Errors</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Enabled</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {feeds.map((feed) => (
            <>
              <tr
                key={feed.id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpanded(expanded === feed.id ? null : feed.id)}
              >
                <td className="px-4 py-3 font-medium text-gray-900">
                  {feed.name}
                  <span className="ml-2 text-xs text-gray-400 font-normal">
                    {feed.recent_articles.length > 0
                      ? `${feed.recent_articles.length} recent`
                      : "no articles"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                      CATEGORY_COLORS[feed.category] ?? "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {feed.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{formatDate(feed.last_fetched)}</td>
                <td className="px-4 py-3 text-gray-500">
                  {feed.error_count > 0 ? (
                    <span className="text-red-500 font-medium">{feed.error_count}</span>
                  ) : (
                    "0"
                  )}
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => toggleFeed(feed.id, feed.enabled)}
                    disabled={loading === feed.id}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                      feed.enabled ? "bg-gray-900" : "bg-gray-200"
                    } ${loading === feed.id ? "opacity-50 cursor-not-allowed" : ""}`}
                    aria-label={feed.enabled ? "Disable feed" : "Enable feed"}
                  >
                    <span
                      className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                        feed.enabled ? "translate-x-4" : "translate-x-1"
                      }`}
                    />
                  </button>
                </td>
              </tr>
              {expanded === feed.id && (
                <tr key={`${feed.id}-expanded`} className="bg-gray-50">
                  <td colSpan={5} className="px-4 py-3">
                    {feed.recent_articles.length === 0 ? (
                      <p className="text-gray-400 text-xs italic">No articles stored yet.</p>
                    ) : (
                      <ul className="space-y-1">
                        {feed.recent_articles.map((a) => (
                          <li key={a.link} className="text-xs text-gray-600">
                            <a
                              href={a.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="hover:text-blue-600 hover:underline"
                            >
                              {a.title}
                            </a>
                            <span className="ml-2 text-gray-400">{formatDate(a.created_at)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}
