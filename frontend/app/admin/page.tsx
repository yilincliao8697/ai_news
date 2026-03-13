import FeedTable, { FeedEntry } from "@/components/FeedTable";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchFeeds(): Promise<FeedEntry[]> {
  const res = await fetch(`${API_BASE}/admin/feeds`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export default async function AdminPage() {
  const feeds = await fetchFeeds();
  const enabledCount = feeds.filter((f) => f.enabled).length;

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 py-6 px-4">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Feed Registry</h1>
          <p className="text-sm text-gray-500 mt-1">
            {enabledCount} of {feeds.length} feeds enabled. Click a row to preview recent articles.
          </p>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {feeds.length === 0 ? (
          <p className="text-gray-500 text-center mt-8">
            No feeds found. Run{" "}
            <code className="bg-gray-100 px-1 rounded">python scripts/import_feeds.py</code> first.
          </p>
        ) : (
          <FeedTable feeds={feeds} />
        )}
      </div>
    </main>
  );
}
