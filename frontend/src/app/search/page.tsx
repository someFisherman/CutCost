"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { searchProducts } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { Footer } from "@/components/Footer";
import { useEffect, Suspense } from "react";
import { Loader2 } from "lucide-react";

function SearchContent() {
  const searchParams = useSearchParams();
  const q = searchParams.get("q") || "";
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["search", q],
    queryFn: () => searchProducts(q),
    enabled: q.length > 0,
  });

  useEffect(() => {
    if (!data) return;

    if (data.redirect_to) {
      router.replace(data.redirect_to);
      return;
    }

    if (data.type === "multiple" || data.type === "browse_redirect") {
      const params = new URLSearchParams();
      params.set("q", q);
      if (data.parsed_query?.brand) params.set("brand", data.parsed_query.brand);
      if (data.parsed_query?.product_line) params.set("product_line", data.parsed_query.product_line);
      if (data.parsed_query?.storage) params.set("storage", data.parsed_query.storage);
      if (data.parsed_query?.color) params.set("color", data.parsed_query.color);
      router.replace(`/browse?${params.toString()}`);
      return;
    }

    if (data.type === "empty") {
      router.replace(`/browse?q=${encodeURIComponent(q)}`);
    }
  }, [data, router, q]);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border)] py-4 px-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <a href="/" className="font-bold text-xl shrink-0">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </a>
          <SearchBar initialQuery={q} />
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto px-4 py-8 w-full">
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
            <span className="ml-2 text-[var(--color-text-secondary)]">Searching...</span>
          </div>
        )}

        {error && (
          <div className="text-center py-20">
            <p className="text-[var(--color-danger)]">Search failed. Please try again.</p>
          </div>
        )}

        {data?.type === "disambiguation" && data.variants.length > 0 && (
          <div>
            <p className="text-lg font-medium mb-4">
              Which variant did you mean?
            </p>
            <div className="grid gap-3">
              {data.variants.map((v) => (
                <a
                  key={v.id}
                  href={`/product/${v.slug}`}
                  className="flex items-center gap-4 p-4 rounded-xl
                             border border-[var(--color-border)] bg-[var(--color-surface)]
                             hover:border-[var(--color-accent)] transition-colors"
                >
                  <div className="flex-1">
                    <p className="font-medium">{v.display_name}</p>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      {Object.values(v.attributes).join(" \u00B7 ")}
                    </p>
                  </div>
                  <span className="text-[var(--color-accent)]">&rarr;</span>
                </a>
              ))}
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
