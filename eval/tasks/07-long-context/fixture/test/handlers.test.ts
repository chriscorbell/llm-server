import { test } from "node:test";
import assert from "node:assert/strict";
import * as handlers from "../src/handlers.ts";
import type { Handler } from "../src/handlers.ts";
import type { Store } from "../src/types.ts";

const store: Store = { read: async (id) => ({ id }) };
const unauthorised = { params: { id: "x" } };

test("every handler refuses an unauthorised request", async () => {
  const entries = Object.entries(handlers).filter(
    ([, value]) => typeof value === "function",
  ) as [string, Handler][];
  assert.ok(entries.length > 100, "expected the generated handlers to be present");

  const permissive: string[] = [];
  for (const [name, handler] of entries) {
    try {
      await handler(unauthorised as never, store);
      permissive.push(name);
    } catch (error) {
      if ((error as Error).message !== "forbidden") permissive.push(name);
    }
  }
  assert.deepEqual(permissive, [], `these handlers skipped the auth check: ${permissive}`);
});

test("an authorised request still reads the record", async () => {
  const [, handler] = Object.entries(handlers).find(
    ([, value]) => typeof value === "function",
  ) as [string, Handler];
  const result = await handler(
    { params: { id: "abc" }, auth: { canWrite: true } } as never,
    store,
  );
  assert.equal((result as { id: string }).id, "abc");
});
