"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { searchProducts } from "@/lib/api";
import { SearchBar } from "@/components/SearchBar";
import { Footer } from "@/components/Footer";
import { useRouter } from "next/navigation";
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
    if (data?.redirect_to) {
      router.push(data.redirect_to);
    }
  }, [data, router]);

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

        {data?.type === "empty" && (
          <div className="text-center py-20">
            <p className="text-lg font-medium mb-2">No products found for &quot;{q}&quot;</p>
            <p className="text-[var(--color-text-secondary)]">
              Try a more specific search, like &quot;iPhone 16 Pro 256GB&quot;
            </p>
          </div>
        )}

        {data?.type === "disambiguation" && data.variants.length > 0 && (
          <div>
            <p className="text-lg font-medium mb-4">
              Did you mean...?
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
                      {Object.values(v.attributes).join(" · ")}
                    </p>
                  </div>
                  <span className="text-[var(--color-accent)]">&rarr;</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {data?.type === "multiple" && data.variants.length > 0 && (
          <div>
            <p className="text-lg font-medium mb-4">
              Multiple matches for &quot;{q}&quot;
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
                      {Object.values(v.attributes).join(" · ")}
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
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-6 h-6 animate-spin text-[var(--color-accent)]" />
      </div>
    }>
      <SearchContent />
    </Suspense>
  );
}
