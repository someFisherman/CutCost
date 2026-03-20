"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getProductOffers, formatPrice } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { OfferCard } from "@/components/OfferCard";
import { ModeToggle } from "@/components/ModeToggle";
import { Footer } from "@/components/Footer";
import { Loader2, Package, ArrowUpDown } from "lucide-react";
import { useState } from "react";
import type { SearchMode, SortMode } from "@/lib/types";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "best_deal", label: "Best Deal" },
  { value: "price_asc", label: "Price: Low to High" },
  { value: "price_desc", label: "Price: High to Low" },
  { value: "trust_desc", label: "Most Trusted" },
  { value: "delivery_asc", label: "Fastest Delivery" },
];

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();
  const [sort, setSort] = useState<SortMode>("best_deal");
  const [mode, setMode] = useState<SearchMode>("high_trust");
  const [condition, setCondition] = useState("all");

  const { data, isLoading, error } = useQuery({
    queryKey: ["product-offers", slug, sort, mode, condition],
    queryFn: () => getProductOffers(slug, { sort, mode, condition }),
    enabled: !!slug,
  });

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border)] py-4 px-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <a href="/" className="font-bold text-xl shrink-0">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </a>
          <SearchBar />
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
            <span className="ml-2 text-[var(--color-text-secondary)]">Loading offers...</span>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-[var(--color-danger)]">Failed to load product. Please try again.</p>
          </div>
        )}

        {data && (
          <>
            {/* Product header */}
            <div className="flex items-start gap-4 mb-6 p-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
              <div className="w-20 h-20 rounded-lg bg-[var(--color-border)] flex items-center justify-center flex-shrink-0">
                {data.variant.image_url ? (
                  <img
                    src={data.variant.image_url}
                    alt={data.variant.display_name}
                    className="w-20 h-20 object-contain rounded-lg"
                  />
                ) : (
                  <Package className="w-10 h-10 text-[var(--color-text-secondary)]" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold">{data.variant.display_name}</h1>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  {data.product.brand} \u00B7 {data.product.category}
                  {data.variant.attributes.storage && ` \u00B7 ${data.variant.attributes.storage}`}
                  {data.variant.attributes.color && ` \u00B7 ${data.variant.attributes.color}`}
                </p>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  {data.meta.total_offers} offer{data.meta.total_offers !== 1 ? "s" : ""} found
                  {data.offers.length > 0 && (
                    <> \u00B7 Prices {formatPrice(
                      Math.min(...data.offers.map((o) => o.total_cost.total)),
                      data.meta.buyer_currency
                    )} \u2013 {formatPrice(
                      Math.max(...data.offers.map((o) => o.total_cost.total)),
                      data.meta.buyer_currency
                    )}</>
                  )}
                </p>
                <a
                  href={`/browse?brand=${encodeURIComponent(data.product.brand)}`}
                  className="inline-block mt-2 text-xs text-[var(--color-accent)] hover:underline"
                >
                  View all {data.product.brand} products
                </a>
              </div>
            </div>

            {/* Mode toggle */}
            <ModeToggle mode={mode} onModeChange={setMode} />

            {/* Filter/sort controls */}
            <div className="flex items-center gap-4 mb-6 text-sm flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-[var(--color-text-secondary)]">Condition:</span>
                <select
                  value={condition}
                  onChange={(e) => setCondition(e.target.value)}
                  className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] cursor-pointer text-sm"
                >
                  <option value="all">All</option>
                  <option value="new">New</option>
                  <option value="refurbished">Refurbished</option>
                  <option value="used">Used</option>
                </select>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                <ArrowUpDown className="w-4 h-4 text-[var(--color-text-secondary)]" />
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortMode)}
                  className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] cursor-pointer text-sm"
                >
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Offers */}
            {data.offers.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-[var(--color-text-secondary)]">
                  No offers available{mode === "high_trust" ? " from trusted merchants" : ""}. Try switching to{" "}
                  {mode === "high_trust" ? "Full Search" : "High Trust"} mode.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {data.offers.map((offer) => (
                  <OfferCard key={offer.id} offer={offer} />
                ))}
              </div>
            )}

            {/* Disclaimer */}
            <p className="mt-8 text-xs text-[var(--color-text-secondary)] text-center">
              {data.meta.disclaimer}
            </p>
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
