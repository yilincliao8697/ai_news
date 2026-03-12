import Link from "next/link";

const TOPICS = ["ai", "tech", "science"] as const;

type Props = { activeTopic?: string };

export default function TopicFilter({ activeTopic }: Props) {
  return (
    <nav className="flex gap-2 flex-wrap">
      <Link
        href="/"
        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
          !activeTopic
            ? "bg-gray-900 text-white"
            : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
        }`}
      >
        All
      </Link>
      {TOPICS.map((topic) => (
        <Link
          key={topic}
          href={`/?topic=${topic}`}
          className={`px-3 py-1 rounded-full text-sm font-medium capitalize transition-colors ${
            activeTopic === topic
              ? "bg-gray-900 text-white"
              : "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
          }`}
        >
          {topic}
        </Link>
      ))}
    </nav>
  );
}
