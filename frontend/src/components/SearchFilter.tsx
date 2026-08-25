import { categoryStyle } from '../utils/colors';

interface Props {
  search: string;
  onSearchChange: (v: string) => void;
  presentCategories: string[];
  hiddenCategories: Set<string>;
  onToggleCategory: (cat: string) => void;
}

export default function SearchFilter({
  search,
  onSearchChange,
  presentCategories,
  hiddenCategories,
  onToggleCategory,
}: Props) {
  return (
    <div className="p-3 space-y-3">
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          Search
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Semantic or raw name…"
          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-sky-500"
        />
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
          Categories
        </div>
        {presentCategories.length === 0 && (
          <div className="text-xs text-gray-600">No events to filter.</div>
        )}
        <div className="space-y-1">
          {presentCategories.map((cat) => {
            const style = categoryStyle(cat);
            const hidden = hiddenCategories.has(cat);
            return (
              <label
                key={cat}
                className="flex items-center gap-2 text-xs cursor-pointer select-none"
              >
                <input
                  type="checkbox"
                  checked={!hidden}
                  onChange={() => onToggleCategory(cat)}
                  className="accent-sky-500"
                />
                <span
                  className="inline-block w-3 h-3 rounded-sm"
                  style={{ background: style.color }}
                />
                <span className={hidden ? 'text-gray-600 line-through' : 'text-gray-300'}>
                  {style.displayName}
                </span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}
