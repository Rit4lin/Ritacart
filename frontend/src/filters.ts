type ReceiptFilterable = {
  store: string;
  source: string;
  needs_review: boolean;
};
type ReceiptFilters = { store: string; source: string; review: boolean };

export function filterReceipts<T extends ReceiptFilterable>(
  receipts: T[],
  filters: ReceiptFilters,
): T[] {
  return receipts.filter(
    (receipt) =>
      (!filters.store || receipt.store === filters.store) &&
      (!filters.source || receipt.source === filters.source) &&
      (!filters.review || receipt.needs_review),
  );
}
