export interface CostComponent {
  value: number;
  currency: string;
  source: "extracted" | "curated" | "estimated" | "unknown";
  note: string;
}

export interface CostBreakdown {
  base_price: CostComponent;
  shipping: CostComponent;
  import_vat: CostComponent;
  customs_fee: CostComponent;
  import_duty: CostComponent;
  total: number;
  total_low: number | null;
  total_high: number | null;
  currency: string;
  confidence: "high" | "medium" | "low";
}

export interface MerchantInfo {
  name: string;
  slug: string;
  country: string;
  logo_url: string | null;
  trust_score: number;
  trust_tier: "high" | "medium" | "low" | "blocked";
}

export interface Offer {
  id: string;
  merchant: MerchantInfo;
  price: number;
  price_currency: string;
  total_cost: CostBreakdown;
  condition: string;
  availability: string;
  delivery_days_min: number | null;
  delivery_days_max: number | null;
  match_confidence: number | null;
  mismatch_flags: Array<{ code: string; detail: string }>;
  url: string;
  affiliate_url: string | null;
  is_affiliate: boolean;
  rank: number;
  label: string | null;
  explanation: string;
}

export interface ProductInfo {
  id: string;
  brand: string;
  model: string;
  canonical_name: string;
  category: string;
  image_url: string | null;
  slug: string;
}

export interface VariantInfo {
  id: string;
  display_name: string;
  slug: string;
  attributes: Record<string, string>;
  image_url: string | null;
}

export interface ProductOffersResponse {
  product: ProductInfo;
  variant: VariantInfo;
  offers: Offer[];
  meta: {
    total_offers: number;
    buyer_country: string;
    buyer_currency: string;
    sort: string;
    mode: string;
    disclaimer: string;
  };
}

export interface AutocompleteItem {
  variant_id: string;
  product_id: string;
  display_name: string;
  slug: string;
  category: string;
  brand: string;
  image_url: string | null;
  type: "variant" | "category";
  filter_url: string | null;
}

export interface ParsedQuery {
  brand: string | null;
  product_line: string | null;
  model: string | null;
  storage: string | null;
  color: string | null;
  has_filters: boolean;
}

export interface SearchResult {
  query: string;
  type: "exact" | "disambiguation" | "multiple" | "browse_redirect" | "empty";
  matched_variant: VariantInfo | null;
  matched_product: ProductInfo | null;
  variants: VariantInfo[];
  redirect_to: string | null;
  parsed_query: ParsedQuery | null;
}

export interface BrowseProduct {
  variant_id: string;
  product_id: string;
  display_name: string;
  slug: string;
  brand: string;
  model: string;
  category: string;
  product_line: string | null;
  attributes: Record<string, string>;
  image_url: string | null;
  best_price: number | null;
  best_price_currency: string | null;
  offer_count: number;
  best_trust_tier: string | null;
  condition_available: string[];
}

export interface BrowseResponse {
  products: BrowseProduct[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  filters_applied: Record<string, string>;
  mode: string;
}

export interface FilterOption {
  value: string;
  label: string;
  count: number;
}

export interface FilterOptionsResponse {
  categories: FilterOption[];
  brands: FilterOption[];
  product_lines: FilterOption[];
  models: FilterOption[];
  storages: FilterOption[];
  colors: FilterOption[];
  conditions: FilterOption[];
  price_min: number | null;
  price_max: number | null;
}

export type SortMode =
  | "best_deal"
  | "price_asc"
  | "price_desc"
  | "trust_desc"
  | "delivery_asc";

export type SearchMode = "high_trust" | "full_search";

export interface CategorySuggestion {
  id: string;
  name: string;
  name_de: string;
  icon: string;
  breadcrumb: string;
  depth: number;
  browse_params: Record<string, string>;
  match_score: number;
}

export interface CategorySearchResponse {
  categories: CategorySuggestion[];
}

export interface DeepSearchStartResponse {
  job_id: string;
  status: string;
  progress: number;
  message: string;
}

export interface DeepSearchStatusResponse {
  id: string;
  query: string;
  status: "queued" | "running" | "completed" | "failed" | "not_found";
  progress: number;
  scanned_products: number;
  total_products: number;
  offers_upserted: number;
  started_at: string;
  completed_at: string | null;
  message: string;
  error: string | null;
}
