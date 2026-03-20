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
}

export interface SearchResult {
  query: string;
  type: "exact" | "disambiguation" | "multiple" | "empty";
  matched_variant: VariantInfo | null;
  matched_product: ProductInfo | null;
  variants: VariantInfo[];
  redirect_to: string | null;
}
