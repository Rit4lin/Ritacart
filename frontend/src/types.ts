export type Page =
  | "inicio"
  | "compras"
  | "productos"
  | "estadisticas"
  | "habitos"
  | "configuracion";
export type ImportStatus = {
  enabled: boolean;
  last_run: string | null;
  last_success: string | null;
  last_error: string | null;
  imported_receipts_last_run: number;
};
export type ReceiptSummary = {
  id: number;
  store: string;
  purchased_at: string;
  total: string;
  source_filename: string;
  source: "email" | "manual";
  imported_at: string;
  item_count: number;
  needs_review: boolean;
};
export type ReceiptDetail = ReceiptSummary & {
  subtotal: string | null;
  reference: string | null;
  line_discount_total: string;
  adjustments: Array<{ label: string; amount: string; raw_text: string }>;
  parser_warnings: string[];
  source_extracted_text: string;
  items: Array<{
    id: number;
    raw_name: string;
    quantity: string | null;
    unit: string | null;
    unit_price: string | null;
    price_per_kg: string | null;
    total_price: string | null;
    gross_total_price: string | null;
    discount_amount: string;
  }>;
  vat_breakdown: Array<{
    rate: string;
    taxable_base: string;
    tax_amount: string;
  }>;
};
export type ProductSummary = {
  id: number;
  name: string;
  purchase_count: number;
  total_quantity: string;
  last_purchased_at: string | null;
  category: { id: number; name: string; slug: string } | null;
};
export type Category = {
  id: number;
  name: string;
  slug: string;
  product_count: number;
};
export type PriceSummary = {
  price_unit: string;
  current_price: string;
  previous_price: string | null;
  change_absolute: string | null;
  change_percent: string | null;
  min_price: string;
  max_price: string;
  average_price: string;
};
export type ProductAnalytics = ProductSummary & {
  aliases: string[];
  first_purchased_at: string | null;
  total_spend: string;
  average_days_between_purchases: string | null;
  price_summary: PriceSummary[];
  monthly_purchases: Array<{
    month: string;
    purchase_count: number;
    total_quantity: string;
  }>;
  monthly_spend: Array<{ month: string; total_spend: string }>;
  seasonal_purchases: Array<{ month: number; purchase_count: number }>;
  price_history: Array<{ date: string; price: string; price_unit: string }>;
};
export type Overview = {
  total_spend: string;
  receipt_count: number;
  current_month_spend: string;
  latest_receipt: ReceiptSummary | null;
};
export type StatisticsRange = "3m" | "6m" | "1y" | "all";
export type Statistics = {
  range: StatisticsRange;
  period: {
    total_spend: string;
    receipt_count: number;
    average_basket: string;
    average_weekly_spend: string;
    average_days_between_shops: string | null;
  };
  comparisons: { current_month: Comparison; current_year: Comparison };
  monthly_spend: Array<{
    month: string;
    total_spend: string;
    receipt_count: number;
    average_basket: string;
  }>;
  purchases_by_weekday: Array<{ weekday: number; receipt_count: number }>;
  purchases_by_hour: Array<{ hour: number; receipt_count: number }>;
};
export type Comparison = {
  current: string;
  previous: string;
  difference: string;
  percentage_change: string | null;
};
export type InsightProduct = {
  id: number;
  name: string;
  purchase_count: number;
  last_purchased_at: string | null;
  total_spend?: string;
  price_unit?: string;
  current_price?: string;
  previous_price?: string | null;
  change_absolute?: string | null;
  change_percent?: string | null;
};
export type ProductInsights = {
  most_expensive_by_spend: InsightProduct[];
  most_frequently_purchased: InsightProduct[];
  biggest_price_increases_percent: InsightProduct[];
  biggest_price_decreases_percent: InsightProduct[];
  biggest_price_increases_absolute: InsightProduct[];
  biggest_price_decreases_absolute: InsightProduct[];
};
export type CategoryAnalytics = {
  range: StatisticsRange;
  summary: {
    total_products: number;
    categorized_products: number;
    uncategorized_products: number;
    categorized_percentage: string;
    observed_spend: string;
  };
  categories: Array<{
    category_id: number | null;
    name: string;
    slug: string;
    total_spend: string;
    percentage: string;
    product_count: number;
    current_month_spend: string;
    previous_month_spend: string;
    change_absolute: string;
    change_percent: string | null;
    top_products: Array<{ id: number; name: string; total_spend: string }>;
  }>;
  monthly_spend: Array<{
    month: string;
    categories: Array<{
      category_id: number | null;
      slug: string;
      total_spend: string;
    }>;
  }>;
};
export type HabitProduct = {
  product_id: number;
  name: string;
  category: { id: number; name: string; slug: string } | null;
  purchase_count: number;
  first_purchased_at: string;
  last_purchased_at: string;
  days_since_last_purchase: number;
  average_days_between_purchases: string | null;
  median_days_between_purchases: string | null;
  typical_quantity: string | null;
  current_price: string | null;
  price_unit: string | null;
  total_spend: string;
  status?: string;
};
export type BasketInsights = {
  basket: {
    items: HabitProduct[];
    current_basket_cost: string;
    basket_price_history: Array<{
      month: string;
      cost: string;
      coverage: string;
    }>;
    personal_inflation: {
      baseline_month: string;
      baseline_cost: string;
      current_cost: string;
      change_absolute: string;
      change_percent: string;
      coverage_current: string;
      coverage_baseline: string;
    } | null;
    basket_comparisons: Record<
      string,
      {
        month: string;
        cost: string;
        change_absolute: string;
        change_percent: string;
        coverage: string;
      } | null
    >;
  };
  due_soon_products: HabitProduct[];
  inactive_regular_products: HabitProduct[];
  most_regular_products: HabitProduct[];
  new_products: HabitProduct[];
};
export type SearchResults = {
  products: Array<{ id: number; name: string }>;
  receipts: Array<{
    id: number;
    store: string;
    purchased_at: string;
    total: string;
    item_count: number;
  }>;
};
export type DataHealth = {
  total_receipts: number;
  total_receipt_items: number;
  total_products: number;
  uncategorized_products: number;
  receipts_needing_review: number;
  receipts_without_items: number;
  possible_duplicate_receipts: number;
  parser_warning_count: number;
};
