"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Search, ArrowRight, FolderOpen } from "lucide-react";
import { getAutocomplete } from "@/lib/api";
import type { AutocompleteItem } from "@/lib/types";

export function SearchBar({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<AutocompleteItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      const data = await getAutocomplete(q);
      setSuggestions(data.suggestions);
      setIsOpen(data.suggestions.length > 0);
    } catch {
      setSuggestions([]);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(query), 200);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchSuggestions]);

  function navigate(item: AutocompleteItem) {
    if (item.type === "category" && item.filter_url) {
      router.push(item.filter_url);
    } else if (item.slug) {
      router.push(`/product/${item.slug}`);
    }
    setIsOpen(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedIndex >= 0 && suggestions[selectedIndex]) {
      navigate(suggestions[selectedIndex]);
    } else if (query.trim()) {
      router.push(`/browse?q=${encodeURIComponent(query.trim())}`);
    }
    setIsOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--color-text-secondary)]" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedIndex(-1);
          }}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 150)}
          onKeyDown={handleKeyDown}
          placeholder='Search any product... e.g. "iPhone 16 Pro 256GB"'
          className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl
                     bg-[var(--color-surface)] border border-[var(--color-border)]
                     focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]
                     placeholder:text-[var(--color-text-secondary)]"
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {isOpen && suggestions.length > 0 && (
        <ul className="absolute z-50 w-full mt-2 py-2 rounded-xl
                       bg-[var(--color-surface)] border border-[var(--color-border)]
                       shadow-lg max-h-80 overflow-y-auto">
          {suggestions.map((item, idx) => (
            <li key={`${item.type}-${item.variant_id || item.filter_url}-${idx}`}>
              <button
                type="button"
                className={`w-full text-left px-4 py-3 flex items-center gap-3
                           hover:bg-[var(--color-border)] transition-colors
                           ${idx === selectedIndex ? "bg-[var(--color-border)]" : ""}`}
                onMouseDown={() => navigate(item)}
              >
                {item.type === "category" ? (
                  <>
                    <FolderOpen className="w-4 h-4 text-[var(--color-accent)] flex-shrink-0" />
                    <span className="flex-1 font-medium text-[var(--color-accent)]">
                      {item.display_name}
                    </span>
                    <ArrowRight className="w-4 h-4 text-[var(--color-accent)]" />
                  </>
                ) : (
                  <>
                    <span className="text-xs uppercase tracking-wide text-[var(--color-text-secondary)] w-16 flex-shrink-0">
                      {item.brand}
                    </span>
                    <span className="flex-1 font-medium truncate">{item.display_name}</span>
                    <span className="text-xs text-[var(--color-text-secondary)] flex-shrink-0">
                      {item.category}
                    </span>
                  </>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
