import { ExternalLink, Trophy, AlertTriangle } from "lucide-react";
import { formatCountry, formatPrice } from "@/lib/api";
import type { Offer } from "@/lib/types";
import { TrustBadge } from "./TrustBadge";
import { CostBreakdown } from "./CostBreakdown";
import clsx from "clsx";

interface OfferCardProps {
  offer: Offer;
}

export function OfferCard({ offer }: OfferCardProps) {
  const isBestDeal = offer.label === "best_deal";
  const isRisky = offer.label === "risky";
  const clickUrl = offer.affiliate_url || offer.url;

  return (
    <div
      className={clsx(
        "rounded-xl border p-5 transition-shadow hover:shadow-md",
        isBestDeal && "border-[var(--color-success)] bg-green-50/50 dark:bg-green-950/30",
        isRisky && "border-[var(--color-danger)] bg-red-50/50 dark:bg-red-950/30",
        !isBestDeal && !isRisky && "border-[var(--color-border)] bg-[var(--color-surface)]"
      )}
    >
      {isBestDeal && (
        <div className="flex items-center gap-2 mb-3 text-[var(--color-success)] font-semibold text-sm">
          <Trophy className="w-4 h-4" />
          Best Deal
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        {/* Merchant info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-lg">{offer.merchant.name}</span>
            <span className="text-sm">{formatCountry(offer.merchant.country)}</span>
            <TrustBadge tier={offer.merchant.trust_tier} compact />
          </div>
          <TrustBadge tier={offer.merchant.trust_tier} />
        </div>

        {/* Price */}
        <div className="text-right flex-shrink-0">
          <div className="text-2xl font-bold">
            {formatPrice(offer.total_cost.total, offer.total_cost.currency)}
          </div>
          <div className="text-sm text-[var(--color-text-secondary)]">
            total cost
          </div>
          {offer.price_currency !== offer.total_cost.currency && (
            <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              listed: {formatPrice(offer.price, offer.price_currency)}
            </div>
          )}
        </div>
      </div>

      {/* Details row */}
      <div className="mt-3 flex flex-wrap gap-3 text-sm text-[var(--color-text-secondary)]">
        {offer.condition !== "unknown" && (
          <span className="capitalize">{offer.condition.replace("_", " ")}</span>
        )}
        {offer.delivery_days_min && (
          <span>
            {offer.delivery_days_min === offer.delivery_days_max
              ? `${offer.delivery_days_min}d delivery`
              : `${offer.delivery_days_min}–${offer.delivery_days_max}d delivery`}
          </span>
        )}
        {offer.total_cost.shipping.value === 0 && (
          <span className="text-[var(--color-success)]">Free shipping</span>
        )}
      </div>

      {/* Mismatch warnings */}
      {offer.mismatch_flags.length > 0 && (
        <div className="mt-3 p-2 rounded-lg bg-yellow-50 dark:bg-yellow-950/50 text-sm flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-[var(--color-warning)] flex-shrink-0 mt-0.5" />
          <span>
            {offer.mismatch_flags.map((f) => f.detail).join(". ")}
          </span>
        </div>
      )}

      {/* Explanation */}
      <p className="mt-3 text-sm text-[var(--color-text-secondary)] italic">
        {offer.explanation}
      </p>

      {/* Cost breakdown (expandable) */}
      <div className="mt-3">
        <CostBreakdown
          breakdown={offer.total_cost}
          showListedPrice={
            offer.price_currency !== offer.total_cost.currency
              ? { amount: offer.price, currency: offer.price_currency }
              : undefined
          }
        />
      </div>

      {/* CTA */}
      <a
        href={clickUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={clsx(
          "mt-4 flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg font-medium transition-colors",
          isRisky
            ? "bg-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-800"
            : "bg-[var(--color-accent)] text-white hover:opacity-90"
        )}
      >
        <ExternalLink className="w-4 h-4" />
        {isRisky ? "View at your own risk" : "View Deal"}
      </a>

      {offer.is_affiliate && (
        <p className="mt-2 text-[10px] text-[var(--color-text-secondary)] text-center">
          Affiliate link — CutCost may earn a commission
        </p>
      )}
    </div>
  );
}
