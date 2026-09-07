import { test } from "node:test";
import assert from "node:assert/strict";
import { createUser } from "../src/create-user.ts";
import { updateUser } from "../src/update-user.ts";

test("createUser normalises a valid email", () => {
  assert.deepEqual(createUser({ email: "  Ana@Example.COM ", age: 30 }),
    { ok: true, email: "ana@example.com" });
});

test("createUser rejects a malformed email", () => {
  const r = createUser({ email: "nope", age: 30 });
  assert.equal(r.ok, false);
  assert.ok(r.ok === false && r.errors.includes("email must contain a local part and a domain"));
});

test("createUser rejects an out of range age", () => {
  const r = createUser({ email: "a@b.com", age: 12 });
  assert.ok(r.ok === false && r.errors.includes("age must be at least 13"));
});

test("createUser rejects a fractional age", () => {
  const r = createUser({ email: "a@b.com", age: 30.5 });
  assert.ok(r.ok === false && r.errors.includes("age must be a whole number"));
});

test("updateUser applies the same email rules", () => {
  const r = updateUser("u1", { email: "@b.com", age: 30 });
  assert.ok(r.ok === false && r.errors.includes("email must contain a local part and a domain"));
});

test("updateUser additionally rejects an empty id", () => {
  const r = updateUser("", { email: "a@b.com", age: 30 });
  assert.ok(r.ok === false && r.errors.includes("id must not be empty"));
});

test("updateUser accepts a valid pair", () => {
  assert.deepEqual(updateUser("u1", { email: "A@B.com", age: 40 }),
    { ok: true, email: "a@b.com" });
});
