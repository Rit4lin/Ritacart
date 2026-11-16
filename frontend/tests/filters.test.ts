import { test } from "node:test";
import { strict as assert } from "node:assert";
import { filterReceipts } from "../src/filters.ts";

const receipts = [
  {
    store: "Mercadona",
    source: "email",
    purchased_at: "2026-10-01T10:00:00",
    needs_review: false,
  },
  {
    store: "Carrefour",
    source: "manual",
    purchased_at: "2026-11-02T10:00:00",
    needs_review: true,
  },
];

test("receipt filters combine store, source and review state", () => {
  assert.deepEqual(
    filterReceipts(receipts, {
      store: "Carrefour",
      source: "manual",
      review: true,
    }),
    [receipts[1]],
  );
  assert.deepEqual(
    filterReceipts(receipts, {
      store: "Carrefour",
      source: "email",
      review: false,
    }),
    [],
  );
  assert.deepEqual(
    filterReceipts(receipts, { store: "", source: "", review: false }),
    receipts,
  );
});
