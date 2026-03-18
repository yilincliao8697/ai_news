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
  source_type: string;
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

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  academic_institution: "Academic Institutions",
  academic_journal:     "Academic Journals",
  company_research:     "Company Research Blogs",
  company_blog:         "Company Blogs",
  independent_blog:     "Independent Blogs & Newsletters",
  science_media:        "Science & Media",
};

const SOURCE_TYPE_ORDER = [
  "academic_institution",
  "academic_journal",
  "company_research",
  "company_blog",
  "independent_blog",
  "science_media",
];

export function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function groupFeeds(feeds: FeedEntry[]): [string, FeedEntry[]][] {
  const grouped: Record<string, FeedEntry[]> = {};
  for (const feed of feeds) {
    const key = feed.source_type || "independent_blog";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(feed);
  }
  const ordered = SOURCE_TYPE_ORDER.filter((k) => grouped[k]);
  const remaining = Object.keys(grouped).filter((k) => !SOURCE_TYPE_ORDER.includes(k));
  return [...ordered, ...remaining].map((k) => [k, grouped[k]]);
}

type Props = {
  feeds: FeedEntry[];
  onArticlesChanged?: () => void;
  apiKey?: string;
};

export default function FeedTable({ feeds: initialFeeds, onArticlesChanged, apiKey }: Props) {
  const [feeds, setFeeds] = useState<FeedEntry[]>(initialFeeds);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState<number | null>(null);
  const [bulkLoading, setBulkLoading] = useState<Set<string>>(new Set());
  const [fetching, setFetching] = useState<Set<number>>(new Set());
  const [fetchDone, setFetchDone] = useState<Set<number>>(new Set());
  const [limitError, setLimitError] = useState<string | null>(null);

  const authHeaders: Record<string, string> = apiKey
    ? { "Content-Type": "application/json", "X-Admin-Key": apiKey }
    : { "Content-Type": "application/json" };

  function showError(msg: string) {
    setLimitError(msg);
    setTimeout(() => setLimitError(null), 4000);
  }

  function toggleGroup(key: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  async function toggleFeed(id: number, currentEnabled: boolean) {
    setLoading(id);
    try {
      const res = await fetch(`${API_BASE}/admin/feeds/${id}`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (res.status === 409) {
        showError("Feed limit reached (20 max). Disable a feed first.");
        return;
      }
      if (res.status === 401) {
        showError("Invalid admin key.");
        return;
      }
      if (!res.ok) throw new Error("Toggle failed");
      setFeeds((prev) =>
        prev.map((f) => (f.id === id ? { ...f, enabled: !currentEnabled } : f))
      );
      // Trigger targeted fetch if toggling ON with no articles
      const feed = feeds.find((f) => f.id === id);
      if (!currentEnabled && feed && feed.recent_articles.length === 0) {
        triggerFeedFetch(id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  }

  async function triggerFeedFetch(id: number) {
    setFetching((prev) => new Set(prev).add(id));
    try {
      await fetch(`${API_BASE}/feeds/${id}/fetch`, { method: "POST", headers: authHeaders });
      setFetchDone((prev) => new Set(prev).add(id));
      setTimeout(() => {
        setFetchDone((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }, 4000);
    } catch {
      // fail silently — scheduled pipeline will pick it up
    } finally {
      setFetching((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }

  async function bulkToggleGroup(sourceType: string, enable: boolean) {
    setBulkLoading((prev) => new Set(prev).add(sourceType));
    try {
      const res = await fetch(`${API_BASE}/admin/feeds/bulk-toggle`, {
        method: "PATCH",
        headers: authHeaders,
        body: JSON.stringify({ source_type: sourceType, enabled: enable }),
      });
      if (res.status === 409) {
        const data = await res.json();
        showError(data.detail ?? "Feed limit reached (20 max).");
        return;
      }
      if (res.status === 401) {
        showError("Invalid admin key.");
        return;
      }
      if (!res.ok) throw new Error("Bulk toggle failed");
      setFeeds((prev) =>
        prev.map((f) => (f.source_type === sourceType ? { ...f, enabled: enable } : f))
      );
    } catch (e) {
      console.error(e);
    } finally {
      setBulkLoading((prev) => {
        const next = new Set(prev);
        next.delete(sourceType);
        return next;
      });
    }
  }

  const groups = groupFeeds(feeds);

  return (
    <div className="space-y-4">
      {limitError && (
        <div className="mb-3 px-4 py-2 rounded-md bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
          {limitError}
        </div>
      )}
      {groups.map(([sourceType, groupedFeeds]) => {
        const label = SOURCE_TYPE_LABELS[sourceType] ?? sourceType;
        const enabledCount = groupedFeeds.filter((f) => f.enabled).length;
        const isCollapsed = collapsedGroups.has(sourceType);
        const isBulkLoading = bulkLoading.has(sourceType);

        return (
          <div key={sourceType} className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div
              onClick={() => toggleGroup(sourceType)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
            >
              <span className="font-semibold text-gray-800 dark:text-gray-100 text-sm">{label}</span>
              <div className="flex items-center gap-3">
                {apiKey && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      bulkToggleGroup(sourceType, enabledCount < groupedFeeds.length);
                    }}
                    disabled={isBulkLoading}
                    className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                      isBulkLoading
                        ? "opacity-50 cursor-not-allowed text-gray-400 border-gray-200 dark:border-gray-600"
                        : "text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600 hover:text-gray-700 dark:hover:text-gray-200"
                    }`}
                  >
                    {isBulkLoading
                      ? "..."
                      : enabledCount < groupedFeeds.length
                      ? "Enable all"
                      : "Disable all"}
                  </button>
                )}
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {enabledCount} / {groupedFeeds.length} enabled
                </span>
                <span className="text-gray-400 dark:text-gray-500 text-xs">{isCollapsed ? "▶" : "▼"}</span>
              </div>
            </div>

            {!isCollapsed && (
              <table className="min-w-full divide-y divide-gray-100 dark:divide-gray-700 text-sm">
                <thead className="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Feed</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Category</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Last Fetched</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Errors</th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 dark:text-gray-500">Enabled</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 dark:divide-gray-700 bg-white dark:bg-gray-900">
                  {groupedFeeds.map((feed) => (
                    <>
                      <tr
                        key={feed.id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                        onClick={() => setExpandedRow(expandedRow === feed.id ? null : feed.id)}
                      >
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                          {feed.name}
                          {fetching.has(feed.id) ? (
                            <span className="ml-2 text-xs text-blue-500 dark:text-blue-400 animate-pulse">
                              fetching…
                            </span>
                          ) : fetchDone.has(feed.id) ? (
                            <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">
                              check back soon
                            </span>
                          ) : (
                            <span className="ml-2 text-xs text-gray-400 dark:text-gray-500 font-normal">
                              {feed.recent_articles.length > 0
                                ? `${feed.recent_articles.length} recent`
                                : "no articles"}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                            CATEGORY_COLORS[feed.category] ?? "bg-gray-100 text-gray-600"
                          }`}>
                            {feed.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500 dark:text-gray-400">{formatDate(feed.last_fetched)}</td>
                        <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
                          {feed.error_count > 0 ? (
                            <span className="text-red-500 font-medium">{feed.error_count}</span>
                          ) : "0"}
                        </td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          {apiKey ? (
                            <button
                              onClick={() => toggleFeed(feed.id, feed.enabled)}
                              disabled={loading === feed.id}
                              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                                feed.enabled ? "bg-gray-900 dark:bg-gray-100" : "bg-gray-200 dark:bg-gray-600"
                              } ${loading === feed.id ? "opacity-50 cursor-not-allowed" : ""}`}
                              aria-label={feed.enabled ? "Disable feed" : "Enable feed"}
                            >
                              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white dark:bg-gray-900 shadow transition-transform ${
                                feed.enabled ? "translate-x-4" : "translate-x-1"
                              }`} />
                            </button>
                          ) : (
                            <span className={`text-base ${feed.enabled ? "text-gray-500 dark:text-gray-400" : "text-gray-300 dark:text-gray-600"}`}>
                              {feed.enabled ? "●" : "○"}
                            </span>
                          )}
                        </td>
                      </tr>
                      {expandedRow === feed.id && (
                        <tr key={`${feed.id}-expanded`} className="bg-gray-50 dark:bg-gray-800">
                          <td colSpan={5} className="px-4 py-3">
                            {feed.recent_articles.length === 0 ? (
                              <p className="text-gray-400 dark:text-gray-500 text-xs italic">No articles stored yet.</p>
                            ) : (
                              <ul className="space-y-1">
                                {feed.recent_articles.map((a) => (
                                  <li key={a.link} className="text-xs text-gray-600 dark:text-gray-300">
                                    <a
                                      href={a.link}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="hover:text-blue-600 hover:underline"
                                    >
                                      {a.title}
                                    </a>
                                    <span className="ml-2 text-gray-400 dark:text-gray-500">{formatDate(a.created_at)}</span>
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
            )}
          </div>
        );
      })}
    </div>
  );
}
