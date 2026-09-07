/**
 * Merge a partial override over a base object. Values present in the override win;
 * keys absent from the override keep the base value.
 */
export function mergeConfig<T extends Record<string, unknown>>(
  base: T,
  override: Partial<T>,
): T {
  const merged = { ...base };
  for (const key of Object.keys(base) as (keyof T)[]) {
    const value = override[key];
    if (value !== undefined) merged[key] = base[key];
  }
  return merged;
}
