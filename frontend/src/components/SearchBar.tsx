"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Search, ArrowRight, FolderOpen, Compass, X } from "lucide-react";
import { getAutocomplete } from "@/lib/api";
import type { AutocompleteItem } from "@/lib/types";

interface SearchBarProps {
  initialQuery?: string;
  showGuidedHint?: boolean;
  onSwitchToGuided?: () => void;
}

export function SearchBar({ initialQuery = "", showGuidedHint = false, onSwitchToGuided }: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<AutocompleteItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [hintDismissed, setHintDismissed] = useState(false);
  const justSubmitted = useRef(false);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimer = useRef<number | null>(null);

  const showGuidedPopup = showGuidedHint && !hintDismissed && query.length >= 2 && !isOpen;

  const fetchSuggestions = useCallback(async (q: string) => {
    if (justSubmitted.current) return;
    if (q.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }
    try {
      const data = await getAutocomplete(q);
      if (!justSubmitted.current) {
        setSuggestions(data.suggestions);
        setIsOpen(data.suggestions.length > 0);
      }
    } catch {
      setSuggestions([]);
    }
  }, []);

  useEffect(() => {
    if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    debounceTimer.current = window.setTimeout(() => fetchSuggestions(query), 200);
    return () => {
      if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    };
  }, [query, fetchSuggestions]);

  function navigate(item: AutocompleteItem) {
    setIsOpen(false);
    setSuggestions([]);
    inputRef.current?.blur();
    if (item.type === "category" && item.filter_url) {
      router.push(item.filter_url);
    } else if (item.slug) {
      router.push(`/product/${item.slug}`);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    justSubmitted.current = true;
    setIsOpen(false);
    setSuggestions([]);
    inputRef.current?.blur();

    if (selectedIndex >= 0 && suggestions[selectedIndex]) {
      const item = suggestions[selectedIndex];
      if (item.type === "category" && item.filter_url) {
        router.push(item.filter_url);
      } else if (item.slug) {
        router.push(`/product/${item.slug}`);
      }
    } else if (query.trim()) {
      router.push(`/browse?q=${encodeURIComponent(query.trim())}`);
    }

    setTimeout(() => {
      justSubmitted.current = false;
    }, 500);
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
      inputRef.current?.blur();
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
            justSubmitted.current = false;
            setQuery(e.target.value);
            setSelectedIndex(-1);
          }}
          onFocus={() => {
            if (!justSubmitted.current && suggestions.length > 0) {
              setIsOpen(true);
            }
          }}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
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
                       shadow-lg max-h-[60vh] overflow-y-auto overscroll-contain">
          {suggestions.map((item, idx) => (
            <li key={`${item.type}-${item.variant_id || item.filter_url}-${idx}`}>
              <button
                type="button"
                className={`w-full text-left px-4 py-3 flex items-center gap-3
                           hover:bg-[var(--color-border)] transition-colors
                           ${idx === selectedIndex ? "bg-[var(--color-border)]" : ""}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  navigate(item);
                }}
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

      {showGuidedPopup && onSwitchToGuided && (
        <div className="absolute z-50 w-full mt-2 p-4 rounded-xl
                        bg-[var(--color-surface)] border border-[var(--color-accent)]/30
                        shadow-lg">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Compass className="w-4 h-4 text-[var(--color-accent)]" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium mb-1">Try Guided Search</p>
              <p className="text-xs text-[var(--color-text-secondary)] mb-3">
                Browse by category for better results. Pick a category, then narrow down step by step.
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    onSwitchToGuided();
                  }}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--color-accent)] text-white hover:opacity-90 transition-opacity"
                >
                  Switch to Guided Search
                </button>
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setHintDismissed(true);
                  }}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)] transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
            <button
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                setHintDismissed(true);
              }}
              className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)] flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </form>
  );
}
