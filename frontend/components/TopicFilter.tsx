const TOPICS = ["research", "industry", "science"] as const;

type Props = {
  selected: string | null;
  onSelect: (topic: string | null) => void;
};

export default function TopicFilter({ selected, onSelect }: Props) {
  return (
    <nav className="flex gap-2 flex-wrap">
      {TOPICS.map((topic) => (
        <button
          key={topic}
          onClick={() => onSelect(topic)}
          className={`px-3 py-1 rounded-full text-sm font-medium capitalize transition-colors ${
            selected === topic
              ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          }`}
        >
          {topic}
        </button>
      ))}
      <button
        onClick={() => onSelect(null)}
        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
          selected === null
            ? "bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900"
            : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
        }`}
      >
        All
      </button>
    </nav>
  );
}
