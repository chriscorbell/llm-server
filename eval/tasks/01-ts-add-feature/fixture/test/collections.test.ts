import { test } from "node:test";
import assert from "node:assert/strict";
import { unique, partition, groupBy } from "../src/collections.ts";

test("unique removes duplicates", () => {
  assert.deepEqual(unique([1, 1, 2]), [1, 2]);
});

test("partition splits on the predicate", () => {
  assert.deepEqual(partition([1, 2, 3, 4], (n) => n % 2 === 0), [[2, 4], [1, 3]]);
});

test("groupBy keys by the selector", () => {
  const rows = [
    { team: "red", name: "ana" },
    { team: "blue", name: "bo" },
    { team: "red", name: "cy" },
  ];
  assert.deepEqual(groupBy(rows, (r) => r.team), {
    red: [{ team: "red", name: "ana" }, { team: "red", name: "cy" }],
    blue: [{ team: "blue", name: "bo" }],
  });
});

test("groupBy on an empty list gives an empty object", () => {
  assert.deepEqual(groupBy([], (r: { team: string }) => r.team), {});
});

test("groupBy preserves input order within a group", () => {
  const rows = [{ k: "a", n: 1 }, { k: "a", n: 2 }, { k: "a", n: 3 }];
  assert.deepEqual(groupBy(rows, (r) => r.k).a.map((r) => r.n), [1, 2, 3]);
});
