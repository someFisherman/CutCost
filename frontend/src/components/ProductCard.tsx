"use client";

import { Package, ShieldCheck, Tag } from "lucide-react";
import { formatPrice } from "@/lib/api";
import type { BrowseProduct } from "@/lib/types";

interface ProductCardProps {
  product: BrowseProduct;
}

export function ProductCard({ product }: ProductCardProps) {
  const attrs = product.attributes;
  const specs = [attrs.storage, attrs.color, attrs.screen].filter(Boolean);

  return (
    <a
      href={`/product/${product.slug}`}
      className="group flex flex-col rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden hover:border-[var(--color-accent)] hover:shadow-lg transition-all"
    >
      {/* Image area */}
      <div className="aspect-square bg-[var(--color-border)]/30 flex items-center justify-center p-4">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.display_name}
            className="max-h-full max-w-full object-contain group-hover:scale-105 transition-transform"
          />
        ) : (
          <Package className="w-12 h-12 text-[var(--color-text-secondary)]" />
        )}
      </div>

      {/* Content */}
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wide mb-1">
          {product.brand}
        </p>
        <h3 className="font-semibold text-sm leading-tight mb-2 line-clamp-2 group-hover:text-[var(--color-accent)] transition-colors">
          {product.display_name}
        </h3>

        {specs.length > 0 && (
          <p className="text-xs text-[var(--color-text-secondary)] mb-3">
            {specs.join(" \u00B7 ")}
          </p>
        )}

        <div className="mt-auto">
          {product.best_price !== null && product.best_price_currency ? (
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold text-[var(--color-accent)]">
                {formatPrice(product.best_price, product.best_price_currency)}
              </span>
              {product.offer_count > 0 && (
                <span className="text-xs text-[var(--color-text-secondary)]">
                  from {product.offer_count} {product.offer_count === 1 ? "offer" : "offers"}
                </span>
              )}
            </div>
          ) : (
            <span className="text-sm text-[var(--color-text-secondary)]">No offers</span>
          )}

          <div className="flex items-center gap-2 mt-2">
            {product.best_trust_tier === "high" && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[var(--color-success)] bg-green-50 dark:bg-green-950 px-1.5 py-0.5 rounded-full">
                <ShieldCheck className="w-3 h-3" />
                Verified
              </span>
            )}
            {product.condition_available.length > 0 && product.condition_available.some((c) => c !== "new") && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-[var(--color-warning)] bg-yellow-50 dark:bg-yellow-950 px-1.5 py-0.5 rounded-full">
                <Tag className="w-3 h-3" />
                Refurbished
              </span>
            )}
          </div>
        </div>
      </div>
    </a>
  );
}
