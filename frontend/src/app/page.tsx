"use client";

import { SearchBar } from "@/components/SearchBar";
import { GuidedSearch } from "@/components/GuidedSearch";
import { Footer } from "@/components/Footer";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

export default function HomePage() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<"guided" | "search">("guided");
  const guidedQuery = searchParams.get("q") || "";

  useEffect(() => {
    if (searchParams.get("guided") === "1") {
      setActiveTab("guided");
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold tracking-tight mb-4">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </h1>
          <p className="text-xl text-[var(--color-text-secondary)] max-w-lg mx-auto">
            Find the cheapest safe place to buy anything.
          </p>
          <p className="text-sm text-[var(--color-text-secondary)] mt-2">
            Real total cost &middot; Merchant trust &middot; Cross-border comparison
          </p>
        </div>

        {/* Tab toggle */}
        <div className="flex rounded-xl border border-[var(--color-border)] overflow-hidden mb-6 w-full max-w-md">
          <button
            onClick={() => setActiveTab("guided")}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "guided"
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]"
            }`}
          >
            Guided Search
          </button>
          <button
            onClick={() => setActiveTab("search")}
            className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === "search"
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-border)]"
            }`}
          >
            Quick Search
          </button>
        </div>

        {/* Guided search */}
        {activeTab === "guided" && <GuidedSearch initialQuery={guidedQuery} />}

        {/* Quick search */}
        {activeTab === "search" && (
          <div className="w-full max-w-2xl">
            <SearchBar showGuidedHint onSwitchToGuided={() => setActiveTab("guided")} />

            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {[
                { label: "iPhone 16 Pro", url: "/browse?brand=Apple&product_line=iPhone" },
                { label: "Samsung Galaxy S25 Ultra", url: "/browse?q=Samsung+Galaxy+S25+Ultra" },
                { label: "Google Pixel 9 Pro", url: "/browse?q=Google+Pixel+9+Pro" },
                { label: "Browse All", url: "/browse" },
              ].map((example) => (
                <a
                  key={example.label}
                  href={example.url}
                  className="px-3 py-1.5 text-sm rounded-full
                             border border-[var(--color-border)]
                             text-[var(--color-text-secondary)]
                             hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]
                             transition-colors"
                >
                  {example.label}
                </a>
              ))}
            </div>
          </div>
        )}

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl text-center">
          <Feature
            title="True Total Cost"
            description="Price + shipping + duties + VAT + currency conversion. The real number."
          />
          <Feature
            title="Merchant Trust"
            description="We verify merchants and flag suspicious deals so you buy with confidence."
          />
          <Feature
            title="Cross-Border"
            description="Compare prices across countries. Is Amazon.de actually cheaper after customs?"
          />
        </div>
      </main>

      <Footer />
    </div>
  );
}

function Feature({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-[var(--color-text-secondary)]">{description}</p>
    </div>
  );
}
