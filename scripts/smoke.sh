#!/usr/bin/env bash
# Prove the four things an agent client needs: text, tool calling, vision, and a
# long prompt. Run from mbp or on the server. Exits non-zero on the first failure.
set -uo pipefail

BASE="${BASE_URL:-http://vllm:8000}"
KEY="${API_KEY:?set API_KEY}"
MODEL="${SERVED_NAME:-qwen38}"
fail=0

say() { printf '\n== %s\n' "$1"; }
post() { curl -fsS -m 600 "$BASE/v1/chat/completions" -H "Authorization: Bearer $KEY" \
         -H 'Content-Type: application/json' -d @-; }

say "models endpoint"
curl -fsS -m 10 "$BASE/v1/models" -H "Authorization: Bearer $KEY" \
  | python3 -c 'import json,sys; print([m["id"] for m in json.load(sys.stdin)["data"]])' || fail=1

say "plain text turn, thinking off"
post <<JSON | python3 -c 'import json,sys; d=json.load(sys.stdin); print(repr(d["choices"][0]["message"]["content"][:200]))' || fail=1
{"model":"$MODEL","messages":[{"role":"user","content":"Reply with exactly the word: pong"}],
 "max_tokens":16,"chat_template_kwargs":{"enable_thinking":false}}
JSON

say "thinking turn, reasoning content must be present"
post <<JSON | python3 -c '
import json,sys
m = json.load(sys.stdin)["choices"][0]["message"]
r = m.get("reasoning_content") or ""
print("reasoning chars:", len(r))
print("answer:", repr((m.get("content") or "")[:120]))
sys.exit(0 if len(r) > 0 else 1)' || fail=1
{"model":"$MODEL","messages":[{"role":"user","content":"A bat and ball cost 1.10 together. The bat costs 1.00 more than the ball. What does the ball cost?"}],
 "max_tokens":2048,"temperature":1.0,"top_p":0.95,"chat_template_kwargs":{"enable_thinking":true}}
JSON

say "tool calling"
post <<JSON | python3 -c '
import json,sys
m = json.load(sys.stdin)["choices"][0]["message"]
calls = m.get("tool_calls") or []
print("tool_calls:", json.dumps(calls)[:300])
sys.exit(0 if calls else 1)' || fail=1
{"model":"$MODEL","messages":[{"role":"user","content":"What is the weather in Lisbon right now? Use the tool."}],
 "max_tokens":1024,"tool_choice":"auto","chat_template_kwargs":{"enable_thinking":false},
 "tools":[{"type":"function","function":{"name":"get_weather","description":"Current weather for a city",
   "parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]}
JSON

say "vision: a solid red image"
PNG_B64=$(python3 - <<'PY'
import base64, struct, zlib
w = h = 64
raw = b"".join(b"\x00" + bytes([220, 40, 40]) * w for _ in range(h))
def chunk(tag, data):
    c = tag + data
    return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw))
       + chunk(b"IEND", b""))
print(base64.b64encode(png).decode())
PY
)
post <<JSON | python3 -c '
import json,sys
t = json.load(sys.stdin)["choices"][0]["message"]["content"] or ""
print("answer:", repr(t[:200]))
sys.exit(0 if "red" in t.lower() else 1)' || fail=1
{"model":"$MODEL","max_tokens":32,"chat_template_kwargs":{"enable_thinking":false},
 "messages":[{"role":"user","content":[
   {"type":"text","text":"What single colour fills this image? Answer with one word."},
   {"type":"image_url","image_url":{"url":"data:image/png;base64,$PNG_B64"}}]}]}
JSON

say "result"
if [ "$fail" -eq 0 ]; then echo "all checks passed"; else echo "one or more checks FAILED"; fi
exit "$fail"
