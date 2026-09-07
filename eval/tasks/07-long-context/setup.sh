#!/usr/bin/env bash
# Generates the large source file so the repository stays small. Deterministic:
# the same seed always plants the bug in the same handler.
set -euo pipefail
python3 - <<'GEN'
import random, pathlib
rng = random.Random(20260907)
n = 240
names = [f"handle{verb}{noun}{i:03d}"
         for i, (verb, noun) in enumerate(
             [(rng.choice(["Get","Put","Post","Delete","Patch"]),
               rng.choice(["Order","Invoice","User","Session","Report","Ticket","Asset"]))
              for _ in range(n)])]
broken = rng.randrange(n)
out = ['import type { Request, Store } from "./types.ts";', '',
       'export type Handler = (req: Request, store: Store) => Promise<unknown>;', '']
for i, name in enumerate(names):
    guard = "" if i == broken else '  if (!req.auth?.canWrite) throw new Error("forbidden");\n'
    out.append(f'''/** Handler {i} of {n}. Generated. */
export const {name}: Handler = async (req, store) => {{
{guard}  const record = await store.read(req.params.id);
  if (!record) throw new Error("not found");
  return {{ ...record, touchedBy: "{name}" }};
}};
''')
pathlib.Path("src").mkdir(exist_ok=True)
pathlib.Path("src/handlers.ts").write_text("\n".join(out))
GEN
echo "generated src/handlers.ts with $(wc -l < src/handlers.ts) lines"
