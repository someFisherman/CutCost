import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import clsx from "clsx";

interface TrustBadgeProps {
  tier: "high" | "medium" | "low" | "blocked";
  score?: number;
  compact?: boolean;
}

const config = {
  high: {
    icon: ShieldCheck,
    label: "Verified",
    labelDe: "Verifiziert",
    className: "text-[var(--color-success)]",
    bgClass: "bg-green-50 dark:bg-green-950",
  },
  medium: {
    icon: ShieldAlert,
    label: "Caution",
    labelDe: "Vorsicht",
    className: "text-[var(--color-warning)]",
    bgClass: "bg-yellow-50 dark:bg-yellow-950",
  },
  low: {
    icon: ShieldX,
    label: "Unverified",
    labelDe: "Nicht verifiziert",
    className: "text-[var(--color-danger)]",
    bgClass: "bg-red-50 dark:bg-red-950",
  },
  blocked: {
    icon: ShieldX,
    label: "Blocked",
    labelDe: "Blockiert",
    className: "text-[var(--color-danger)]",
    bgClass: "bg-red-50 dark:bg-red-950",
  },
};

export function TrustBadge({ tier, score, compact = false }: TrustBadgeProps) {
  const { icon: Icon, label, className, bgClass } = config[tier];

  if (compact) {
    return (
      <span className={clsx("inline-flex items-center gap-1", className)} title={label}>
        <Icon className="w-4 h-4" />
      </span>
    );
  }

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        className,
        bgClass
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </span>
  );
}
