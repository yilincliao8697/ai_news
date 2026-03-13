"use client";

import { useEffect, useState } from "react";
import ArticleCard from "@/components/ArticleCard";
import SourceFilter from "@/components/SourceFilter";
import ThemeToggle from "@/components/ThemeToggle";
import DigestView from "@/components/DigestView";

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

const TABS = [
  { key: "digest",   label: "Daily Digest" },
  { key: "research", label: "Research" },
  { key: "industry", label: "Industry" },
  { key: "science",  label: "Science" },
  { key: "all",      label: "All" },
] as const;

type TabKey = typeof TABS[number]["key"];

export default function HomePage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("digest");
  const [selectedSource, setSelectedSource] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/articles`)
      .then((res) => res.json())
      .then((data) => setArticles(data))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  }, []);

  function handleTabChange(tab: TabKey) {
    setActiveTab(tab);
    setSelectedSource(null);
  }

  const selectedTopic = activeTab === "digest" || activeTab === "all" ? null : activeTab;

  const topicFiltered = selectedTopic
    ? articles.filter((a) => a.topic === selectedTopic)
    : articles;

  const availableSources = selectedTopic
    ? Array.from(new Set(topicFiltered.map((a) => a.source))).sort()
    : [];

  const displayed = selectedSource
    ? topicFiltered.filter((a) => a.source === selectedSource)
    : topicFiltered;

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 py-6 px-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">AI News</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Curated AI, tech, and science articles — summarized.
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Tabs */}
        <nav className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-gray-900 text-gray-900 dark:border-gray-100 dark:text-gray-100"
                  : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {loading ? (
          <p className="text-gray-400 dark:text-gray-500 mt-8 text-center">Loading...</p>
        ) : activeTab === "digest" ? (
          <DigestView articles={articles} />
        ) : (
          <>
            <SourceFilter
              sources={availableSources}
              selected={selectedSource}
              onSelect={setSelectedSource}
            />
            {displayed.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 mt-8 text-center">No articles found.</p>
            ) : (
              <ul className="mt-6 space-y-4">
                {displayed.map((article) => (
                  <li key={article.link}>
                    <ArticleCard article={article} />
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </main>
  );
}
