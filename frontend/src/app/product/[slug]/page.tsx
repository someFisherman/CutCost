"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getProductOffers, formatPrice } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { OfferCard } from "@/components/OfferCard";
import { Footer } from "@/components/Footer";
import { Loader2, Package } from "lucide-react";

export default function ProductPage() {
  const { slug } = useParams<{ slug: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["product-offers", slug],
    queryFn: () => getProductOffers(slug),
    enabled: !!slug,
  });

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border)] py-4 px-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <a href="/" className="font-bold text-xl shrink-0">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </a>
          <SearchBar />
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto px-4 py-8 w-full">
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
            <div className="flex items-start gap-4 mb-8 p-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
              <div className="w-16 h-16 rounded-lg bg-[var(--color-border)] flex items-center justify-center flex-shrink-0">
                {data.variant.image_url ? (
                  <img
                    src={data.variant.image_url}
                    alt={data.variant.display_name}
                    className="w-16 h-16 object-contain rounded-lg"
                  />
                ) : (
                  <Package className="w-8 h-8 text-[var(--color-text-secondary)]" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold">{data.variant.display_name}</h1>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  {data.product.brand} · {data.product.category}
                  {data.variant.attributes.storage && ` · ${data.variant.attributes.storage}`}
                  {data.variant.attributes.color && ` · ${data.variant.attributes.color}`}
                </p>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  {data.meta.total_offers} offer{data.meta.total_offers !== 1 ? "s" : ""} found
                  {data.offers.length > 0 && (
                    <> · Prices {formatPrice(
                      Math.min(...data.offers.map((o) => o.total_cost.total)),
                      data.meta.buyer_currency
                    )} – {formatPrice(
                      Math.max(...data.offers.map((o) => o.total_cost.total)),
                      data.meta.buyer_currency
                    )}</>
                  )}
                </p>
              </div>
            </div>

            {/* Filter bar */}
            <div className="flex items-center gap-4 mb-6 text-sm">
              <span className="text-[var(--color-text-secondary)]">Ship to:</span>
              <span className="font-medium">Switzerland 🇨🇭</span>
              <span className="text-[var(--color-text-secondary)] ml-auto">
                Sort: Best Deal
              </span>
            </div>

            {/* Offers */}
            {data.offers.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-[var(--color-text-secondary)]">No offers available for this product.</p>
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
