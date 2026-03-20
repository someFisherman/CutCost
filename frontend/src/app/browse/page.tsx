"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { browseProducts, getFilters } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { FilterSidebar } from "@/components/FilterSidebar";
import { SortBar } from "@/components/SortBar";
import { ModeToggle } from "@/components/ModeToggle";
import { ProductCard } from "@/components/ProductCard";
import { Footer } from "@/components/Footer";
import { Loader2, SlidersHorizontal, X } from "lucide-react";
import { Suspense, useCallback, useState } from "react";
import type { SearchMode, SortMode } from "@/lib/types";

function BrowseContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  const q = searchParams.get("q") || undefined;
  const category = searchParams.get("category") || undefined;
  const brand = searchParams.get("brand") || undefined;
  const product_line = searchParams.get("product_line") || undefined;
  const model = searchParams.get("model") || undefined;
  const storage = searchParams.get("storage") || undefined;
  const color = searchParams.get("color") || undefined;
  const condition = searchParams.get("condition") || undefined;
  const mode = (searchParams.get("mode") || "high_trust") as SearchMode;
  const sort = (searchParams.get("sort") || "best_deal") as SortMode;
  const page = parseInt(searchParams.get("page") || "1", 10);

  const activeFilters: Record<string, string> = {};
  if (category) activeFilters.category = category;
  if (brand) activeFilters.brand = brand;
  if (product_line) activeFilters.product_line = product_line;
  if (model) activeFilters.model = model;
  if (storage) activeFilters.storage = storage;
  if (color) activeFilters.color = color;
  if (condition) activeFilters.condition = condition;

  const updateParams = useCallback(
    (updates: Record<string, string | undefined>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === undefined || value === "") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      if (updates.page === undefined && !("page" in updates)) {
        params.delete("page");
      }
      router.push(`/browse?${params.toString()}`);
    },
    [searchParams, router]
  );

  const { data: browseData, isLoading: browseLoading } = useQuery({
    queryKey: ["browse", q, category, brand, product_line, model, storage, color, condition, mode, sort, page],
    queryFn: () =>
      browseProducts({
        q, category, brand, product_line, model, storage, color, condition, mode, sort, page,
      }),
  });

  const filterParams = { q, category, brand, product_line, model };
  const { data: filterData, isLoading: filterLoading } = useQuery({
    queryKey: ["filters", q, category, brand, product_line, model],
    queryFn: () => getFilters(filterParams),
  });

  const handleFilterChange = (key: string, value: string | undefined) => {
    updateParams({ [key]: value, page: undefined });
  };

  const activeTags = Object.entries(activeFilters).map(([key, value]) => ({
    key,
    label: `${key.replace("_", " ")}: ${value}`,
  }));

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border)] py-4 px-4">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <a href="/" className="font-bold text-xl shrink-0">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </a>
          <SearchBar initialQuery={q || ""} />
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto px-4 py-6 w-full">
        {/* Active filter tags */}
        {(activeTags.length > 0 || q) && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            {q && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-[var(--color-accent)] text-white">
                &quot;{q}&quot;
                <button onClick={() => updateParams({ q: undefined })} className="hover:opacity-70">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {activeTags.map((tag) => (
              <span
                key={tag.key}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm border border-[var(--color-accent)] text-[var(--color-accent)]"
              >
                {tag.label}
                <button
                  onClick={() => handleFilterChange(tag.key, undefined)}
                  className="hover:opacity-70"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Mode toggle */}
        <ModeToggle
          mode={mode}
          onModeChange={(m) => updateParams({ mode: m, page: undefined })}
        />

        <div className="flex gap-6">
          {/* Desktop sidebar */}
          <div className="hidden lg:block">
            <FilterSidebar
              filters={filterData}
              activeFilters={activeFilters}
              onFilterChange={handleFilterChange}
              isLoading={filterLoading}
            />
          </div>

          {/* Mobile filter button */}
          <button
            onClick={() => setMobileFiltersOpen(true)}
            className="lg:hidden fixed bottom-4 right-4 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-[var(--color-accent)] text-white shadow-lg"
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
            {Object.keys(activeFilters).length > 0 && (
              <span className="bg-white text-[var(--color-accent)] text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
                {Object.keys(activeFilters).length}
              </span>
            )}
          </button>

          {/* Mobile filter drawer */}
          {mobileFiltersOpen && (
            <div className="lg:hidden fixed inset-0 z-50">
              <div
                className="absolute inset-0 bg-black/50"
                onClick={() => setMobileFiltersOpen(false)}
              />
              <div className="absolute right-0 top-0 bottom-0 w-80 max-w-full bg-[var(--color-bg)] p-4 overflow-y-auto shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-bold">Filters</h2>
                  <button
                    onClick={() => setMobileFiltersOpen(false)}
                    className="p-1 rounded-lg hover:bg-[var(--color-border)]"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <FilterSidebar
                  filters={filterData}
                  activeFilters={activeFilters}
                  onFilterChange={(key, val) => {
                    handleFilterChange(key, val);
                  }}
                  isLoading={filterLoading}
                />
              </div>
            </div>
          )}

          {/* Product grid */}
          <div className="flex-1 min-w-0">
            <SortBar
              sort={sort}
              onSortChange={(s) => updateParams({ sort: s, page: undefined })}
              totalResults={browseData?.total || 0}
            />

            {browseLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
                <span className="ml-2 text-[var(--color-text-secondary)]">Loading products...</span>
              </div>
            ) : browseData && browseData.products.length > 0 ? (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {browseData.products.map((product) => (
                    <ProductCard key={product.variant_id} product={product} />
                  ))}
                </div>

                {/* Pagination */}
                {browseData.total_pages > 1 && (
                  <div className="flex items-center justify-center gap-2 mt-8">
                    <button
                      onClick={() => updateParams({ page: String(page - 1) })}
                      disabled={page <= 1}
                      className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-sm disabled:opacity-40 hover:border-[var(--color-accent)] transition-colors"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-[var(--color-text-secondary)]">
                      Page {browseData.page} of {browseData.total_pages}
                    </span>
                    <button
                      onClick={() => updateParams({ page: String(page + 1) })}
                      disabled={page >= browseData.total_pages}
                      className="px-4 py-2 rounded-lg border border-[var(--color-border)] text-sm disabled:opacity-40 hover:border-[var(--color-accent)] transition-colors"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-20">
                <p className="text-lg font-medium mb-2">No products found</p>
                <p className="text-[var(--color-text-secondary)]">
                  Try adjusting your filters or search query.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
        </div>
      }
    >
      <BrowseContent />
    </Suspense>
  );
}
