import { Article } from "@/app/page";

const TOPIC_COLORS: Record<string, string> = {
  research: "bg-purple-100 text-purple-700",
  industry: "bg-blue-100 text-blue-700",
  science:  "bg-green-100 text-green-700",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "America/Los_Angeles",
  });
}

type Props = { article: Article };

export default function ArticleCard({ article }: Props) {
  const badgeClass = TOPIC_COLORS[article.topic] ?? "bg-gray-100 text-gray-600";

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <a
          href={article.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-lg font-semibold text-gray-900 hover:text-blue-600 leading-snug"
        >
          {article.title}
        </a>
        <span
          className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full capitalize ${badgeClass}`}
        >
          {article.topic}
        </span>
      </div>

      <p className="mt-2 text-gray-600 text-sm leading-relaxed">{article.summary}</p>

      <footer className="mt-3 flex items-center gap-2 text-xs text-gray-400">
        <span>{article.source}</span>
        <span>·</span>
        <time dateTime={article.published_at ?? article.created_at}>
          {formatDate(article.published_at ?? article.created_at)}
        </time>
      </footer>
    </article>
  );
}
