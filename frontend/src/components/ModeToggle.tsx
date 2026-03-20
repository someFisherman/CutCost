"use client";

import { ShieldCheck, Globe } from "lucide-react";
import type { SearchMode } from "@/lib/types";
import clsx from "clsx";

interface ModeToggleProps {
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
}

const MODE_OPTIONS: { value: SearchMode; label: string; icon: typeof ShieldCheck; description: string }[] = [
  {
    value: "high_trust",
    label: "High Trust",
    icon: ShieldCheck,
    description: "Verified merchants only",
  },
  {
    value: "full_search",
    label: "Full Search",
    icon: Globe,
    description: "All merchants",
  },
];

export function ModeToggle({ mode, onModeChange }: ModeToggleProps) {
  return (
    <div className="flex rounded-xl border border-[var(--color-border)] overflow-hidden mb-4">
      {MODE_OPTIONS.map((opt) => {
        const Icon = opt.icon;
        const isActive = mode === opt.value;
        return (
          <button
            key={opt.value}
            onClick={() => onModeChange(opt.value)}
            className={clsx(
              "flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]"
            )}
          >
            <Icon className="w-4 h-4" />
            <span>{opt.label}</span>
            <span
              className={clsx(
                "hidden sm:inline text-xs",
                isActive ? "text-white/70" : "text-[var(--color-text-secondary)]"
              )}
            >
              — {opt.description}
            </span>
          </button>
        );
      })}
    </div>
  );
}
