type Props = {
  sources: string[];
  selected: string | null;
  onSelect: (source: string | null) => void;
};

export default function SourceFilter({ sources, selected, onSelect }: Props) {
  if (sources.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-2">
      <button
        onClick={() => onSelect(null)}
        className={`px-3 py-1 rounded-full text-sm border transition-colors ${
          selected === null
            ? "bg-gray-900 text-white border-gray-900 dark:bg-gray-100 dark:text-gray-900 dark:border-gray-100"
            : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-400"
        }`}
      >
        All Sources
      </button>
      {sources.map((source) => (
        <button
          key={source}
          onClick={() => onSelect(source === selected ? null : source)}
          className={`px-3 py-1 rounded-full text-sm border transition-colors ${
            selected === source
              ? "bg-gray-900 text-white border-gray-900 dark:bg-gray-100 dark:text-gray-900 dark:border-gray-100"
              : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-400"
          }`}
        >
          {source}
        </button>
      ))}
    </div>
  );
}
