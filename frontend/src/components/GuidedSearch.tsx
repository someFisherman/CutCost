"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronRight,
  Search,
  Smartphone,
  Monitor,
  Home,
  Dumbbell,
  Shirt,
  Headphones,
  Tv,
  Camera,
  Tablet,
  Laptop,
  Sofa,
  Zap,
  Wind,
  ArrowLeft,
} from "lucide-react";
import { searchCategories, getCategoryChildren } from "@/lib/api";
import type { CategorySuggestion } from "@/lib/types";

const ICON_MAP: Record<string, React.ElementType> = {
  smartphone: Smartphone, monitor: Monitor, home: Home, dumbbell: Dumbbell,
  shirt: Shirt, headphones: Headphones, tv: Tv, camera: Camera,
  tablet: Tablet, laptop: Laptop, sofa: Sofa, zap: Zap, wind: Wind,
};

interface GuidedSearchProps {
  onBrowse?: (params: Record<string, string>) => void;
  initialQuery?: string;
}

export function GuidedSearch({ onBrowse, initialQuery = "" }: GuidedSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [categories, setCategories] = useState<CategorySuggestion[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<{ id: string; name: string }[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimer = useRef<number | null>(null);

  const loadTopCategories = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await searchCategories("");
      setCategories(data.categories);
    } catch {
      setCategories([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTopCategories();
  }, [loadTopCategories]);

  useEffect(() => {
    if (initialQuery.trim().length > 0) {
      setQuery(initialQuery.trim());
    }
  }, [initialQuery]);

  const handleSearch = useCallback(async (q: string) => {
    try {
      setIsLoading(true);
      const data = await searchCategories(q);
      setCategories(data.categories);
    } catch {
      setCategories([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    if (query.length === 0 && breadcrumb.length === 0) {
      loadTopCategories();
      return;
    }
    if (query.length > 0) {
      debounceTimer.current = window.setTimeout(() => handleSearch(query), 150);
    }
    return () => {
      if (debounceTimer.current !== null) window.clearTimeout(debounceTimer.current);
    };
  }, [query, breadcrumb.length, handleSearch, loadTopCategories]);

  async function drillDown(cat: CategorySuggestion) {
    try {
      const children = await getCategoryChildren(cat.id);
      if (children.categories.length > 0) {
        setBreadcrumb((prev) => [...prev, { id: cat.id, name: cat.name_de }]);
        setCategories(children.categories);
        setQuery("");
      } else {
        navigateToBrowse(cat);
      }
    } catch {
      navigateToBrowse(cat);
    }
  }

  function navigateToBrowse(cat: CategorySuggestion) {
    const params = new URLSearchParams();
    for (const [key, val] of Object.entries(cat.browse_params)) {
      if (val) params.set(key, val);
    }
    if (onBrowse) {
      onBrowse(cat.browse_params);
    }
    router.push(`/browse?${params.toString()}`);
  }

  function goBack() {
    const newBreadcrumb = breadcrumb.slice(0, -1);
    setBreadcrumb(newBreadcrumb);
    if (newBreadcrumb.length === 0) {
      loadTopCategories();
    } else {
      const parentId = newBreadcrumb[newBreadcrumb.length - 1].id;
      getCategoryChildren(parentId).then((data) => setCategories(data.categories));
    }
    setQuery("");
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg)]">
          <div className="flex items-center gap-2 text-sm">
            {breadcrumb.length > 0 && (
              <button
                onClick={goBack}
                className="flex items-center gap-1 text-[var(--color-accent)] hover:underline flex-shrink-0"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back
              </button>
            )}
            <div className="flex items-center gap-1 text-[var(--color-text-secondary)] min-w-0 truncate">
              {breadcrumb.length === 0 ? (
                <span className="font-medium text-[var(--color-text)]">What are you looking for?</span>
              ) : (
                breadcrumb.map((b, i) => (
                  <span key={b.id} className="flex items-center gap-1">
                    {i > 0 && <ChevronRight className="w-3 h-3 flex-shrink-0" />}
                    <span className={i === breadcrumb.length - 1 ? "font-medium text-[var(--color-text)]" : ""}>
                      {b.name}
                    </span>
                  </span>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Search input */}
        <div className="relative px-4 py-2 border-b border-[var(--color-border)]">
          <Search className="absolute left-7 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-secondary)]" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={breadcrumb.length > 0 ? "Filter..." : "Type to search categories..."}
            className="w-full pl-8 pr-2 py-2 text-sm bg-transparent focus:outline-none placeholder:text-[var(--color-text-secondary)]"
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        {/* Category list */}
        <div className="max-h-[300px] overflow-y-auto overscroll-contain">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-12 rounded-lg bg-[var(--color-border)] animate-pulse" />
              ))}
            </div>
          ) : categories.length > 0 ? (
            <div className="py-1">
              {categories.map((cat) => {
                const Icon = ICON_MAP[cat.icon] || Monitor;
                return (
                  <button
                    key={cat.id}
                    onClick={() => drillDown(cat)}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--color-border)] transition-colors text-left"
                  >
                    <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-[var(--color-accent)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{cat.name_de}</p>
                      {cat.breadcrumb !== cat.name_de && (
                        <p className="text-xs text-[var(--color-text-secondary)] truncate">{cat.breadcrumb}</p>
                      )}
                    </div>
                    <ChevronRight className="w-4 h-4 text-[var(--color-text-secondary)] flex-shrink-0" />
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-sm text-[var(--color-text-secondary)]">
              No categories found for &quot;{query}&quot;
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
