import { test } from "node:test";
import assert from "node:assert/strict";
import { retry, RetryError } from "../src/retry.ts";

test("returns the first successful value", async () => {
  let calls = 0;
  const value = await retry(async () => { calls++; return "ok"; }, { attempts: 3 });
  assert.equal(value, "ok");
  assert.equal(calls, 1);
});

test("uses every configured attempt before giving up", async () => {
  let calls = 0;
  await assert.rejects(
    () => retry(async () => { calls++; throw new Error("nope"); }, { attempts: 3 }),
    RetryError,
  );
  assert.equal(calls, 3);
});

test("succeeds on the final attempt", async () => {
  let calls = 0;
  const value = await retry(async () => {
    calls++;
    if (calls < 3) throw new Error("not yet");
    return "late";
  }, { attempts: 3 });
  assert.equal(value, "late");
  assert.equal(calls, 3);
});

test("a single attempt still runs the operation once", async () => {
  let calls = 0;
  await assert.rejects(
    () => retry(async () => { calls++; throw new Error("nope"); }, { attempts: 1 }),
    RetryError,
  );
  assert.equal(calls, 1);
});
