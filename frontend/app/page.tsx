import ArticleCard from "@/components/ArticleCard";
import TopicFilter from "@/components/TopicFilter";

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

type Props = {
  searchParams: Promise<{ topic?: string }>;
};

async function fetchArticles(topic?: string): Promise<Article[]> {
  const url = topic
    ? `${API_BASE}/articles?topic=${encodeURIComponent(topic)}`
    : `${API_BASE}/articles`;

  const res = await fetch(url, { next: { revalidate: 300 } }); // revalidate every 5 min
  if (!res.ok) return [];
  return res.json();
}

export default async function HomePage({ searchParams }: Props) {
  const { topic } = await searchParams;
  const articles = await fetchArticles(topic);

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 py-6 px-4">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">AI News</h1>
          <p className="text-sm text-gray-500 mt-1">
            Curated AI, tech, and science articles — summarized.
          </p>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        <TopicFilter activeTopic={topic} />

        {articles.length === 0 ? (
          <p className="text-gray-500 mt-8 text-center">No articles found.</p>
        ) : (
          <ul className="mt-6 space-y-4">
            {articles.map((article) => (
              <li key={article.link}>
                <ArticleCard article={article} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
