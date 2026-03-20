import type {
  AutocompleteItem,
  BrowseResponse,
  FilterOptionsResponse,
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
  params?: { country?: string; condition?: string; sort?: string; mode?: string }
): Promise<ProductOffersResponse> {
  const searchParams = new URLSearchParams();
  if (params?.country) searchParams.set("country", params.country);
  if (params?.condition) searchParams.set("condition", params.condition);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.mode) searchParams.set("mode", params.mode);

  const qs = searchParams.toString();
  return fetcher(`/api/products/${slug}/offers${qs ? `?${qs}` : ""}`);
}

export async function browseProducts(
  params: Record<string, string | number | undefined>
): Promise<BrowseResponse> {
  const searchParams = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== "") {
      searchParams.set(key, String(val));
    }
  }
  const qs = searchParams.toString();
  return fetcher(`/api/browse${qs ? `?${qs}` : ""}`);
}

export async function getFilters(
  category?: string
): Promise<FilterOptionsResponse> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return fetcher(`/api/filters${qs}`);
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
    CH: "\u{1F1E8}\u{1F1ED}",
    DE: "\u{1F1E9}\u{1F1EA}",
    AT: "\u{1F1E6}\u{1F1F9}",
    GB: "\u{1F1EC}\u{1F1E7}",
    US: "\u{1F1FA}\u{1F1F8}",
    FR: "\u{1F1EB}\u{1F1F7}",
    IT: "\u{1F1EE}\u{1F1F9}",
  };
  return flags[code] || code;
}
