import FeedTable, { FeedEntry } from "@/components/FeedTable";
import AdminControls from "@/components/AdminControls";
import ThemeToggle from "@/components/ThemeToggle";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchFeeds(): Promise<FeedEntry[]> {
  const res = await fetch(`${API_BASE}/admin/feeds`, { cache: "no-store" });
  if (!res.ok) return [];
  return res.json();
}

export default async function AdminPage() {
  const feeds = await fetchFeeds();
  const enabledCount = feeds.filter((f) => f.enabled).length;
  const groupCount = new Set(feeds.map((f) => f.source_type).filter(Boolean)).size;

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 py-6 px-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Feed Registry</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {enabledCount} of {feeds.length} feeds enabled across {groupCount} source types.
              Click a row to preview recent articles.
            </p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-6">
        {feeds.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-center mt-8">
            No feeds found. Run{" "}
            <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">python scripts/import_feeds.py</code> first.
          </p>
        ) : (
          <>
            <AdminControls initialFeeds={feeds} />
            <FeedTable feeds={feeds} />
          </>
        )}
      </div>
    </main>
  );
}
