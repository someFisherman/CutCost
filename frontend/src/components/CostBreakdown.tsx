"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Info } from "lucide-react";
import { formatPrice } from "@/lib/api";
import type { CostBreakdown as CostBreakdownType } from "@/lib/types";
import clsx from "clsx";

interface CostBreakdownProps {
  breakdown: CostBreakdownType;
  showListedPrice?: { amount: number; currency: string };
}

export function CostBreakdown({ breakdown, showListedPrice }: CostBreakdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  const hasImportCosts =
    breakdown.import_vat.value > 0 ||
    breakdown.customs_fee.value > 0 ||
    breakdown.import_duty.value > 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-sm text-[var(--color-text-secondary)]
                   hover:text-[var(--color-text)] transition-colors"
      >
        {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        Cost breakdown
      </button>

      {isOpen && (
        <div className="mt-2 pl-4 border-l-2 border-[var(--color-border)] space-y-1 text-sm">
          {showListedPrice && (
            <Row
              label="Listed price"
              value={formatPrice(showListedPrice.amount, showListedPrice.currency)}
              source="extracted"
            />
          )}
          <Row
            label="Price (converted)"
            value={formatPrice(breakdown.base_price.value, breakdown.currency)}
            source={breakdown.base_price.source}
            note={breakdown.base_price.note}
          />
          <Row
            label="Shipping"
            value={formatPrice(breakdown.shipping.value, breakdown.currency)}
            source={breakdown.shipping.source}
            note={breakdown.shipping.note}
          />
          {hasImportCosts && (
            <>
              <Row
                label="Import VAT"
                value={formatPrice(breakdown.import_vat.value, breakdown.currency)}
                source={breakdown.import_vat.source}
                note={breakdown.import_vat.note}
              />
              {breakdown.customs_fee.value > 0 && (
                <Row
                  label="Customs fee"
                  value={formatPrice(breakdown.customs_fee.value, breakdown.currency)}
                  source={breakdown.customs_fee.source}
                />
              )}
              {breakdown.import_duty.value > 0 && (
                <Row
                  label="Import duty"
                  value={formatPrice(breakdown.import_duty.value, breakdown.currency)}
                  source={breakdown.import_duty.source}
                />
              )}
            </>
          )}
          <div className="pt-1 border-t border-[var(--color-border)] font-semibold flex justify-between">
            <span>Total</span>
            <span>{formatPrice(breakdown.total, breakdown.currency)}</span>
          </div>
          {breakdown.total_low && breakdown.total_high && (
            <p className="text-xs text-[var(--color-text-secondary)]">
              Range: {formatPrice(breakdown.total_low, breakdown.currency)} –{" "}
              {formatPrice(breakdown.total_high, breakdown.currency)}
            </p>
          )}
          <p
            className={clsx(
              "text-xs",
              breakdown.confidence === "high" && "text-[var(--color-success)]",
              breakdown.confidence === "medium" && "text-[var(--color-warning)]",
              breakdown.confidence === "low" && "text-[var(--color-danger)]"
            )}
          >
            Confidence: {breakdown.confidence}
          </p>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  source,
  note,
}: {
  label: string;
  value: string;
  source: string;
  note?: string;
}) {
  const isEstimated = source === "estimated" || source === "unknown";
  return (
    <div className="flex justify-between items-start">
      <span className="text-[var(--color-text-secondary)]">
        {label}
        {isEstimated && " ~"}
      </span>
      <span className="flex items-center gap-1">
        {value}
        {note && (
          <span title={note} className="cursor-help">
            <Info className="w-3 h-3 text-[var(--color-text-secondary)]" />
          </span>
        )}
      </span>
    </div>
  );
}
