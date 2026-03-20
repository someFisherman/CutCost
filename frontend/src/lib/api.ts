import type {
  AutocompleteItem,
  ProductOffersResponse,
  SearchResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function searchProducts(query: string): Promise<SearchResult> {
  return fetcher(`/api/search?q=${encodeURIComponent(query)}`);
}

export async function getAutocomplete(
  partial: string
): Promise<{ suggestions: AutocompleteItem[] }> {
  return fetcher(`/api/autocomplete?q=${encodeURIComponent(partial)}`);
}

export async function getProductOffers(
  slug: string,
  params?: { country?: string; condition?: string; sort?: string }
): Promise<ProductOffersResponse> {
  const searchParams = new URLSearchParams();
  if (params?.country) searchParams.set("country", params.country);
  if (params?.condition) searchParams.set("condition", params.condition);
  if (params?.sort) searchParams.set("sort", params.sort);

  const qs = searchParams.toString();
  return fetcher(`/api/products/${slug}/offers${qs ? `?${qs}` : ""}`);
}

export function formatPrice(amount: number, currency: string): string {
  return new Intl.NumberFormat("de-CH", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatCountry(code: string): string {
  const flags: Record<string, string> = {
    CH: "🇨🇭",
    DE: "🇩🇪",
    AT: "🇦🇹",
    GB: "🇬🇧",
    US: "🇺🇸",
    FR: "🇫🇷",
    IT: "🇮🇹",
  };
  return flags[code] || code;
}
