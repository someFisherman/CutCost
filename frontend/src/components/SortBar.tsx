"use client";

import { ArrowUpDown } from "lucide-react";
import type { SortMode } from "@/lib/types";

interface SortBarProps {
  sort: SortMode;
  onSortChange: (sort: SortMode) => void;
  totalResults: number;
}

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "best_deal", label: "Best Deal" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "trust_desc", label: "Most Trusted" },
  { value: "delivery_asc", label: "Fastest Delivery" },
];

export function SortBar({ sort, onSortChange, totalResults }: SortBarProps) {
  return (
    <div className="flex items-center justify-between gap-4 mb-4">
      <p className="text-sm text-[var(--color-text-secondary)]">
        <span className="font-medium text-[var(--color-text)]">{totalResults}</span>{" "}
        {totalResults === 1 ? "product" : "products"} found
      </p>

      <div className="flex items-center gap-2">
        <ArrowUpDown className="w-4 h-4 text-[var(--color-text-secondary)]" />
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortMode)}
          className="text-sm bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] cursor-pointer"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
