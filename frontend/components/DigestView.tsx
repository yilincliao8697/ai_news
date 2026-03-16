"use client";

import { useState } from "react";
import { Article } from "@/app/page";

const TOPIC_COLORS: Record<string, string> = {
  research: "bg-purple-100 text-purple-700",
  industry: "bg-blue-100 text-blue-700",
  science:  "bg-green-100 text-green-700",
};

function getEffectiveDate(article: Article): Date {
  return new Date(article.published_at ?? article.created_at);
}

function toLocalDateKey(date: Date): string {
  return date.toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
}

function firstSentence(text: string): string {
  const match = text.match(/[^.!?]*[.!?]/);
  return match ? match[0].trim() : text.trim();
}

type Props = {
  articles: Article[];
  topic: "all" | "research" | "industry" | "science";
};

export default function DigestView({ articles, topic }: Props) {
  const [expandedLink, setExpandedLink] = useState<string | null>(null);

  const todayKey = toLocalDateKey(new Date());

  const filtered = articles.filter((a) => {
    const d = getEffectiveDate(a);
    if (toLocalDateKey(d) !== todayKey) return false;
    if (topic !== "all" && a.topic !== topic) return false;
    return true;
  });

  const grouped = new Map<string, Article[]>();
  for (const article of filtered) {
    const key = toLocalDateKey(getEffectiveDate(article));
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(article);
  }

  const sortedGroups = Array.from(grouped.entries()).sort(
    ([, a], [, b]) =>
      getEffectiveDate(b[0]).getTime() - getEffectiveDate(a[0]).getTime()
  );

  const emptyMessage = topic === "all" ? "No articles today." : `No ${topic} articles today.`;

  if (sortedGroups.length === 0) {
    return (
      <p className="text-gray-400 dark:text-gray-500 text-center mt-12">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="space-y-8">
      {sortedGroups.map(([dateLabel, dayArticles]) => (
        <div key={dateLabel}>
          <h2 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-3">
            {dateLabel}
          </h2>
          <ul className="space-y-2">
            {dayArticles.map((article) => (
              <li key={article.link} className="group">
                <div className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <a
                          href={article.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-800 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 hover:underline text-sm leading-snug"
                        >
                          {firstSentence(article.summary)}
                        </a>
                        <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">
                          {article.source}
                        </span>
                        <span className={`ml-1 inline-block px-1.5 py-0.5 rounded text-xs font-medium capitalize ${
                          TOPIC_COLORS[article.topic] ?? "bg-gray-100 text-gray-600"
                        }`}>
                          {article.topic}
                        </span>
                      </div>
                      <button
                        onClick={() =>
                          setExpandedLink(expandedLink === article.link ? null : article.link)
                        }
                        className="flex-shrink-0 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xs mt-0.5"
                        aria-label={expandedLink === article.link ? "Collapse" : "Expand"}
                      >
                        {expandedLink === article.link ? "˅" : "›"}
                      </button>
                    </div>

                    {expandedLink === article.link && (
                      <div className="mt-2 p-3 rounded-md bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                          {article.title}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-2">
                          {article.summary}
                        </p>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400 dark:text-gray-500">{article.source}</span>
                            <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium capitalize ${
                              TOPIC_COLORS[article.topic] ?? "bg-gray-100 text-gray-600"
                            }`}>
                              {article.topic}
                            </span>
                          </div>
                          <a
                            href={article.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                          >
                            Read article →
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
