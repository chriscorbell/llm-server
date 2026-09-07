import { loadConfig } from "./load.ts";

const config = loadConfig(new URL("../config.json", import.meta.url).pathname);
console.log(`listening on ${config.host}:${config.port} at ${config.logLevel}`);
