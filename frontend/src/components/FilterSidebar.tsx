"use client";

import { ChevronDown, ChevronUp, X } from "lucide-react";
import { useState } from "react";
import type { FilterOptionsResponse } from "@/lib/types";

interface FilterSidebarProps {
  filters: FilterOptionsResponse | undefined;
  activeFilters: Record<string, string>;
  onFilterChange: (key: string, value: string | undefined) => void;
  isLoading: boolean;
}

function FilterSection({
  title,
  options,
  activeValue,
  filterKey,
  onFilterChange,
}: {
  title: string;
  options: { value: string; label: string; count: number }[];
  activeValue?: string;
  filterKey: string;
  onFilterChange: (key: string, value: string | undefined) => void;
}) {
  const [isOpen, setIsOpen] = useState(true);

  if (options.length === 0) return null;

  return (
    <div className="border-b border-[var(--color-border)] pb-3 mb-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-sm font-semibold mb-2 hover:text-[var(--color-accent)] transition-colors"
      >
        {title}
        {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {isOpen && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() =>
                onFilterChange(
                  filterKey,
                  activeValue === opt.value ? undefined : opt.value
                )
              }
              className={`flex items-center justify-between w-full px-2 py-1.5 rounded-lg text-sm transition-colors ${
                activeValue === opt.value
                  ? "bg-[var(--color-accent)] text-white"
                  : "hover:bg-[var(--color-border)]"
              }`}
            >
              <span className="truncate">{opt.label}</span>
              <span
                className={`text-xs ml-2 flex-shrink-0 ${
                  activeValue === opt.value
                    ? "text-white/70"
                    : "text-[var(--color-text-secondary)]"
                }`}
              >
                {opt.count}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function FilterSidebar({
  filters,
  activeFilters,
  onFilterChange,
  isLoading,
}: FilterSidebarProps) {
  const activeCount = Object.values(activeFilters).filter(Boolean).length;

  return (
    <aside className="w-full lg:w-64 flex-shrink-0">
      <div className="sticky top-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg">Filters</h2>
          {activeCount > 0 && (
            <button
              onClick={() => {
                for (const key of Object.keys(activeFilters)) {
                  onFilterChange(key, undefined);
                }
              }}
              className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
            >
              <X className="w-3 h-3" />
              Clear all ({activeCount})
            </button>
          )}
        </div>

        {isLoading || !filters ? (
          <div className="space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-[var(--color-border)] rounded w-20 mb-2" />
                <div className="space-y-1">
                  <div className="h-8 bg-[var(--color-border)] rounded" />
                  <div className="h-8 bg-[var(--color-border)] rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            <FilterSection
              title="Category"
              options={filters.categories}
              activeValue={activeFilters.category}
              filterKey="category"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Brand"
              options={filters.brands}
              activeValue={activeFilters.brand}
              filterKey="brand"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Product Line"
              options={filters.product_lines}
              activeValue={activeFilters.product_line}
              filterKey="product_line"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Model"
              options={filters.models}
              activeValue={activeFilters.model}
              filterKey="model"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Storage"
              options={filters.storages}
              activeValue={activeFilters.storage}
              filterKey="storage"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Color"
              options={filters.colors}
              activeValue={activeFilters.color}
              filterKey="color"
              onFilterChange={onFilterChange}
            />
            <FilterSection
              title="Condition"
              options={filters.conditions}
              activeValue={activeFilters.condition}
              filterKey="condition"
              onFilterChange={onFilterChange}
            />
          </>
        )}
      </div>
    </aside>
  );
}
