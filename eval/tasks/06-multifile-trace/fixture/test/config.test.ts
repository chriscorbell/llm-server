import { test } from "node:test";
import assert from "node:assert/strict";
import { mergeConfig } from "../src/merge.ts";
import { loadConfig } from "../src/load.ts";

test("the override wins where it defines a value", () => {
  assert.deepEqual(mergeConfig({ a: 1, b: 2 }, { a: 9 }), { a: 9, b: 2 });
});

test("the base survives where the override is silent", () => {
  assert.deepEqual(mergeConfig({ a: 1, b: 2 }, {}), { a: 1, b: 2 });
});

test("an explicit undefined does not clobber the base", () => {
  assert.deepEqual(mergeConfig({ a: 1 }, { a: undefined }), { a: 1 });
});

test("loadConfig reads the file over the defaults", () => {
  const config = loadConfig(new URL("../config.json", import.meta.url).pathname);
  assert.equal(config.port, 8080);
  assert.equal(config.host, "0.0.0.0");
  assert.equal(config.logLevel, "debug");
});
