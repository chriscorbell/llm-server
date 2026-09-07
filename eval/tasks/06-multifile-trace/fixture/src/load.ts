import { readFileSync } from "node:fs";
import { defaults } from "./defaults.ts";
import { mergeConfig } from "./merge.ts";

export type Config = { port: number; host: string; logLevel: string };

export function loadConfig(path: string): Config {
  const raw = JSON.parse(readFileSync(path, "utf8")) as Partial<Config>;
  return mergeConfig(defaults as unknown as Config, raw);
}
