"use client";

import { useEffect, useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import DigestView from "@/components/DigestView";
import FeedTable, { FeedEntry } from "@/components/FeedTable";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Article = {
  title: string;
  link: string;
  source: string;
  topic: string;
  summary: string;
  created_at: string;
  published_at: string | null;
};

const TOP_TABS = [
  { key: "digest", label: "Digest" },
  { key: "feeds",  label: "Feed Registry" },
] as const;

const DIGEST_TABS = [
  { key: "all",      label: "All" },
  { key: "research", label: "Research" },
  { key: "industry", label: "Industry" },
  { key: "science",  label: "Science" },
] as const;

type TopTab = typeof TOP_TABS[number]["key"];
type DigestTab = typeof DIGEST_TABS[number]["key"];

function getLastUpdated(articles: Article[], topic: string): string | null {
  const relevant = topic === "all" ? articles : articles.filter((a) => a.topic === topic);
  if (relevant.length === 0) return null;
  const latest = relevant.reduce((best, a) => {
    const d = new Date(a.published_at ?? a.created_at);
    return d > best ? d : best;
  }, new Date(0));
  return (
    latest.toLocaleDateString("en-US", { month: "long", day: "numeric" }) +
    " at " +
    latest.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  );
}

export default function HomePage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [feeds, setFeeds] = useState<FeedEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [topTab, setTopTab] = useState<TopTab>("digest");
  const [digestTab, setDigestTab] = useState<DigestTab>("all");

  useEffect(() => {
    fetch(`${API_BASE}/articles`)
      .then((res) => res.json())
      .then((data) => setArticles(data))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));

    fetch(`${API_BASE}/admin/feeds`)
      .then((r) => r.json())
      .then(setFeeds)
      .catch(() => {});
  }, []);

  async function refreshArticles() {
    const data = await fetch(`${API_BASE}/articles`)
      .then((r) => r.json())
      .catch(() => []);
    setArticles(data);
  }

  const lastUpdated = getLastUpdated(articles, digestTab);

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 py-6 px-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">AI News</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Curated AI, tech, and science articles — summarized.
            </p>
          </div>
          <div className="flex items-center gap-4">
            <nav className="flex gap-1">
              {TOP_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setTopTab(tab.key)}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    topTab === tab.key
                      ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900"
                      : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {topTab === "digest" && (
          <>
            <nav className="flex border-b border-gray-200 dark:border-gray-700 mb-2">
              {DIGEST_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setDigestTab(tab.key)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    digestTab === tab.key
                      ? "border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100"
                      : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            {lastUpdated && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 mb-4">
                Updated {lastUpdated}
              </p>
            )}

            {loading ? (
              <p className="text-gray-400 dark:text-gray-500 mt-8 text-center">Loading...</p>
            ) : (
              <DigestView articles={articles} topic={digestTab} />
            )}
          </>
        )}

        {topTab === "feeds" && (
          <FeedTable feeds={feeds} onArticlesChanged={refreshArticles} />
        )}
      </div>
    </main>
  );
}
