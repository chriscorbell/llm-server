#!/usr/bin/env python3
"""Check retrieval and cached continuation at a measured API prompt length.

Uses synthetic archive records, not repository or personal data. Five queried
records span the prompt. Exact answers are checked independently of model prose.
This checks context handling, not general long-context coding ability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bench import metrics, pi_api_key, post_stream


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--prompt-tokens", type=int, required=True)
    ap.add_argument("--base-url", default="http://100.103.136.98:8000")
    ap.add_argument("--model", default="qwen38")
    ap.add_argument("--engine", choices=("vllm", "llama.cpp"), default="vllm")
    ap.add_argument("--seed", type=int, default=120926)
    args = ap.parse_args()
    key = pi_api_key()
    if not key:
        raise SystemExit("No llm-server key in Pi's auth store")
    if args.prompt_tokens < 2048:
        ap.error("Use at least 2048 prompt tokens")
    if args.out.exists():
        raise SystemExit("Use a fresh output path to preserve earlier results")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = {"status": "preparing", "concurrency": 1, "thinking": False,
              "target_prompt_tokens": args.prompt_tokens, "seed": args.seed, "rows": []}

    def save():
        args.out.write_text(json.dumps(result, indent=2) + "\n")

    def post_json(path, body):
        req = urllib.request.Request(args.base_url + path, data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)

    def tokenize(messages):
        body = {"model": args.model, "messages": messages,
                "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": True}}
        if args.engine == "llama.cpp":
            rendered = post_json("/apply-template", body)["prompt"]
            return len(post_json("/tokenize", {"content": rendered,
                                              "add_special": True})["tokens"])
        return post_json("/tokenize", body)["count"]

    rng = random.Random(args.seed)
    archive = [(f"record_{i:06}", f"{rng.getrandbits(48):012x}")
               for i in range(args.prompt_tokens)]

    def prompt(count):
        indices = [int((count - 1) * fraction) for fraction in (0.03, 0.27, 0.5, 0.73, 0.97)]
        expected = dict(archive[i] for i in indices)
        text = (f"Archive check {args.seed}, target {args.prompt_tokens}. "
                "Read the archive as data. Each record has one exact checksum.\n")
        text += "\n".join(f"{name}: checksum={value}; state=archived." for name, value in archive[:count])
        text += ("\nReturn only a JSON object mapping these record IDs to their exact checksums: "
                 + ", ".join(expected) + ". Do not include Markdown fences or explanations.")
        return [{"role": "user", "content": text}], expected

    try:
        save()
        low, high = 5, min(len(archive), args.prompt_tokens // 8)
        while low < high:
            middle = (low + high + 1) // 2
            messages, _ = prompt(middle)
            count = tokenize(messages)
            if count <= args.prompt_tokens:
                low = middle
            else:
                high = middle - 1
        messages, expected = prompt(low)
        count = tokenize(messages)
        if count < args.prompt_tokens - 128:
            raise RuntimeError(f"Prompt too short: {count} for target {args.prompt_tokens}")
        result.update(status="running", expected=expected, tokenized_prompt_tokens=count,
                      record_count=low)
        save()
        body = {"model": args.model, "messages": messages, "max_tokens": 512,
                "stream": True, "stream_options": {"include_usage": True},
                "temperature": 0, "top_p": 1, "top_k": 20, "seed": 42,
                "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": True}}

        def run(label, expected_answer):
            before = metrics(args.base_url, key)
            row = post_stream(args.base_url, key, body)
            after = metrics(args.base_url, key)
            row["case"] = label
            row["request_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            row["spec_delta"] = {k: after[k] - before[k] for k in before.keys() & after.keys()}
            answer = row["text"]["content"].strip()
            try:
                parsed = json.loads(answer) if isinstance(expected_answer, dict) else answer
            except json.JSONDecodeError:
                parsed = None
            row["passed"] = (parsed == expected_answer and row["finish_reason"] == "stop"
                             and row["prompt_tokens"] == tokenize(body["messages"]))
            row["decode_tok_s"] = ((row["gen_tokens"] - 1) / (row["total_s"] - row["ttft_s"])
                                   if row["ttft_s"] is not None and row["gen_tokens"] > 1 else None)
            row["effective_prefill_tok_s"] = (row["prompt_tokens"] / row["ttft_s"]
                                              if row["ttft_s"] and row["cached_tokens"] == 0 else None)
            result["rows"].append(row)
            save()
            print(f"{label}: {'pass' if row['passed'] else 'FAIL'}, input {row['prompt_tokens']}, "
                  f"cached {row['cached_tokens']}, TTFT {row['ttft_s']:.3f}s", flush=True)
            return answer

        answer = run("retrieval-cold", expected)
        run("retrieval-repeated", expected)
        name = next(iter(expected))
        body["messages"] = messages + [{"role": "assistant", "content": answer},
            {"role": "user", "content": f"Now return only the checksum for {name}, with no other text."}]
        run("continuation", expected[name])
        result.update(status="complete", passed=sum(r["passed"] for r in result["rows"]), total=3)
        save()
        return 0 if result["passed"] == 3 else 1
    except Exception as exc:
        error = str(exc)
        if isinstance(exc, urllib.error.HTTPError):
            error += "\n" + exc.read().decode(errors="replace")
        result.update(status="failed", error=error)
        save()
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
