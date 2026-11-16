import { test } from "node:test";
import { strict as assert } from "node:assert";
import { formatPercent } from "../src/format.ts";

test("formats percentage values using Spanish decimal conventions", () => {
  assert.equal(formatPercent("4.50"), "4,5 %");
  assert.equal(formatPercent("21.00"), "21 %");
});
