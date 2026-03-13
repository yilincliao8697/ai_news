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

function isWithinDays(date: Date, days: number): boolean {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return date >= cutoff;
}

type Props = { articles: Article[] };

export default function DigestView({ articles }: Props) {
  const recent = articles.filter((a) => isWithinDays(getEffectiveDate(a), 7));

  const grouped = new Map<string, Article[]>();
  for (const article of recent) {
    const key = toLocalDateKey(getEffectiveDate(article));
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(article);
  }

  const sortedGroups = Array.from(grouped.entries()).sort(
    ([, a], [, b]) =>
      getEffectiveDate(b[0]).getTime() - getEffectiveDate(a[0]).getTime()
  );

  if (sortedGroups.length === 0) {
    return (
      <p className="text-gray-400 dark:text-gray-500 text-center mt-12">
        No articles in the last 7 days.
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
              <li key={article.link} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0" />
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
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
