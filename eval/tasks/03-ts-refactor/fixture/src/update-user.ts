import type { UserInput, Result } from "./create-user.ts";

export function updateUser(id: string, input: UserInput): Result {
  const errors: string[] = [];
  if (id.length === 0) errors.push("id must not be empty");

  const email = input.email.trim().toLowerCase();
  if (!email.includes("@") || email.startsWith("@") || email.endsWith("@")) {
    errors.push("email must contain a local part and a domain");
  }
  if (email.length > 254) errors.push("email must be at most 254 characters");
  if (!Number.isInteger(input.age)) errors.push("age must be a whole number");
  if (input.age < 13) errors.push("age must be at least 13");
  if (input.age > 130) errors.push("age must be at most 130");

  if (errors.length > 0) return { ok: false, errors };
  return { ok: true, email: input.email.trim().toLowerCase() };
}
