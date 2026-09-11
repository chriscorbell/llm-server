#!/usr/bin/env python3
"""Repeated short-output correctness checks for speculative-depth and engine changes.

This targets the short-prompt XPU graph failure reported upstream. Passing these
cases is an integration check, not proof that all logits match eager execution.
The write tool is only declared to the model; no returned tool call is executed.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bench import pi_api_key

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--out", required=True, type=Path)
ap.add_argument("--repetitions", type=int, default=3)
ap.add_argument("--base-url", default="http://100.103.136.98:8000")
a = ap.parse_args()
key = pi_api_key()
if not key:
    raise SystemExit("No llm-server key in Pi's auth store")
cases = [
    ("addition", "What is 17 + 25? Return only the integer.", "42"),
    ("multiplication", "What is 9 * 9? Return only the integer.", "81"),
    ("python", "Evaluate Python sum([4, 6, 8]). Return only the integer.", "18"),
    ("lowercase", "Convert HELLO to lowercase. Return only that word.", "hello"),
    ("json", 'Return exactly this JSON object: {"ok":true,"count":3}', {"ok": True, "count": 3}),
    ("tool", "Use write to save exactly hello to greeting.txt.", None),
]
rows = []
for rep in range(a.repetitions):
    for name, prompt, expected in cases:
        body = {"model": "qwen38", "messages": [{"role": "user", "content": prompt}],
                "temperature": 0, "top_p": 1, "top_k": 20, "max_tokens": 128,
                "seed": 42, "chat_template_kwargs": {"enable_thinking": False}}
        if name == "tool":
            body["tool_choice"] = "auto"
            body["tools"] = [{"type": "function", "function": {
                "name": "write", "description": "Write a UTF-8 file.", "parameters": {
                    "type": "object", "properties": {"path": {"type": "string"},
                    "content": {"type": "string"}}, "required": ["path", "content"]}}}]
        request = urllib.request.Request(a.base_url + "/v1/chat/completions",
            data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + key,
                                                     "Content-Type": "application/json"})
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.load(response)
        message = data["choices"][0]["message"]
        answer = (message.get("content") or "").strip()
        try:
            if name == "tool":
                calls = message.get("tool_calls") or []
                passed = len(calls) == 1 and calls[0]["function"]["name"] == "write"
                if passed:
                    args = json.loads(calls[0]["function"]["arguments"])
                    passed = args == {"path": "greeting.txt", "content": "hello"}
            elif name == "json":
                passed = json.loads(answer) == expected
            else:
                passed = answer == expected
        except (ValueError, KeyError, TypeError):
            passed = False
        row = {"case": name, "repetition": rep + 1, "passed": passed,
               "seconds": time.monotonic() - started, "usage": data.get("usage"),
               "message": message}
        rows.append(row)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"passed": sum(r["passed"] for r in rows),
                                     "total": len(rows), "concurrency": 1,
                                     "thinking": False, "results": rows}, indent=2))
        print(f"{name} repetition {rep + 1}: {'pass' if passed else 'FAIL'}", flush=True)
raise SystemExit(0 if all(r["passed"] for r in rows) else 1)
