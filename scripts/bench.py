#!/usr/bin/env python3
"""Measure decode speed, time to first token, prefill rate and MTP acceptance.

Client-side timing against the OpenAI-compatible endpoint, which is what the
agent client actually experiences. Reports medians over n repetitions.

Every run uses a unique random prefix so prefix caching does not silently turn a
cold measurement into a warm one. Pass --warm to measure the cached path instead.

Usage:
  ./bench.py --base-url http://vllm:8000 --key "$API_KEY" --prompt-tokens 512 --gen 128 -n 5
"""
import argparse, json, statistics, time, urllib.request, uuid, sys, re

def post_stream(url, key, body, timeout=1800):
    req = urllib.request.Request(
        url + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    t0 = time.monotonic()
    ttft = None
    ntok = 0
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            delta = chunk["choices"][0].get("delta", {})
            if delta.get("content") or delta.get("reasoning_content"):
                if ttft is None:
                    ttft = time.monotonic() - t0
                ntok += 1
    total = time.monotonic() - t0
    return ttft, ntok, total

def metrics(url, key):
    """Scrape MTP acceptance from the Prometheus endpoint."""
    try:
        req = urllib.request.Request(url + "/metrics", headers={"Authorization": f"Bearer {key}"})
        text = urllib.request.urlopen(req, timeout=10).read().decode()
    except Exception:
        return {}
    out = {}
    for name in ("vllm:spec_decode_num_accepted_tokens_total",
                 "vllm:spec_decode_num_draft_tokens_total"):
        m = re.search(rf"^{re.escape(name)}\{{[^}}]*\}}\s+([0-9.e+]+)$", text, re.M)
        if m:
            out[name] = float(m.group(1))
    return out

def filler(n_tokens):
    """Roughly n_tokens of unique, low-entropy English so prefill is realistic."""
    uniq = uuid.uuid4().hex
    words = ("the quick brown fox jumps over the lazy dog while counting "
             "tokens for a benchmark run ").split()
    body = " ".join(words[i % len(words)] for i in range(int(n_tokens * 0.78)))
    return f"session {uniq}\n{body}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--key", default="change-me")
    ap.add_argument("--model", default="qwen38")
    ap.add_argument("--prompt-tokens", type=int, default=512)
    ap.add_argument("--gen", type=int, default=128)
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--thinking", action="store_true", help="leave thinking on (default off for stable timing)")
    ap.add_argument("--warm", action="store_true", help="reuse the same prompt to measure the cached path")
    ap.add_argument("--json", help="write results to this path")
    a = ap.parse_args()

    fixed = filler(a.prompt_tokens) if a.warm else None
    m0 = metrics(a.base_url, a.key)
    rows = []
    for i in range(a.n + 1):  # first is a discarded warmup of the same shape
        body = {
            "model": a.model,
            "messages": [{"role": "user", "content": (fixed or filler(a.prompt_tokens)) +
                          "\n\nReply with exactly one plain paragraph of prose."}],
            "max_tokens": a.gen,
            "stream": True,
            "temperature": 1.0 if a.thinking else 0.7,
            "top_p": 0.95 if a.thinking else 0.8,
            "chat_template_kwargs": {"enable_thinking": bool(a.thinking)},
        }
        ttft, ntok, total = post_stream(a.base_url, a.key, body)
        if i == 0:
            continue
        if ttft is None or ntok < 2:
            print(f"rep {i}: no tokens returned", file=sys.stderr); continue
        rows.append({
            "ttft_s": ttft,
            "decode_tok_s": (ntok - 1) / (total - ttft) if total > ttft else 0.0,
            "prefill_tok_s": a.prompt_tokens / ttft,
            "gen_tokens": ntok,
        })
        print(f"rep {i}: ttft {ttft:.2f}s  decode {rows[-1]['decode_tok_s']:.1f} tok/s")

    m1 = metrics(a.base_url, a.key)
    acc = None
    da = m1.get("vllm:spec_decode_num_accepted_tokens_total", 0) - m0.get("vllm:spec_decode_num_accepted_tokens_total", 0)
    dd = m1.get("vllm:spec_decode_num_draft_tokens_total", 0) - m0.get("vllm:spec_decode_num_draft_tokens_total", 0)
    if dd > 0:
        acc = 100.0 * da / dd

    med = lambda k: statistics.median(r[k] for r in rows)
    result = {
        "prompt_tokens": a.prompt_tokens, "gen": a.gen, "n": len(rows),
        "thinking": a.thinking, "prefix_cache_path": "warm" if a.warm else "cold",
        "ttft_s_median": round(med("ttft_s"), 3),
        "decode_tok_s_median": round(med("decode_tok_s"), 1),
        "prefill_tok_s_median": round(med("prefill_tok_s"), 1),
        "mtp_acceptance_pct": round(acc, 1) if acc is not None else None,
    }
    print("\n" + json.dumps(result, indent=2))
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"result": result, "reps": rows}, f, indent=2)

if __name__ == "__main__":
    main()
