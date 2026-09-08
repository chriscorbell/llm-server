#!/usr/bin/env python3
"""Check Pi's live request contract and compaction in a temporary project."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import random
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    audit = out / "requests.jsonl"
    if audit.exists():
        raise SystemExit("Use a fresh output directory; request metadata already exists")
    result = {"client": "pi", "concurrency": 1, "status": "in progress"}
    with tempfile.TemporaryDirectory(prefix="pi-contract-") as tmp:
        work = Path(tmp)
        config = work / "config"
        config.mkdir()
        for name in ("models.json", "settings.json"):
            shutil.copy(ROOT / "clients/pi" / name, config / name)
        # Unrelated project records make the original requirement old enough to
        # require summarization with the production 20K recent-token setting.
        rng = random.Random(42)
        for part in range(3):
            lines = [f"record_{part}_{i}: value={rng.randrange(100000, 999999)}; "
                     f"category={rng.choice(['alpha', 'beta', 'gamma'])}; status=archived."
                     for i in range(750)]
            (work / f"notes-{part}.txt").write_text("\n".join(lines))
        env = {**os.environ, "PI_CODING_AGENT_DIR": str(config), "PI_EVAL_AUDIT": str(audit)}
        cmd = ["pi", "--mode", "rpc", "--approve", "--offline", "--no-context-files",
               "--no-skills", "--no-extensions", "-e", str(ROOT / "eval/pi_audit.ts"),
               "--session-dir", str(work / "sessions"), "--tools", "read,write",
               "--model", "llm-server/qwen38", "--thinking", "xhigh"]
        events: queue.Queue = queue.Queue()
        compactions = []
        with (out / "stderr.log").open("w") as err, (out / "events.jsonl").open("w") as log:
            proc = subprocess.Popen(cmd, cwd=work, env=env, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1)

            def collect():
                for line in proc.stdout:
                    log.write(line)
                    log.flush()
                    try:
                        events.put(json.loads(line))
                    except json.JSONDecodeError:
                        pass
                events.put({"type": "process_exit"})

            reader = threading.Thread(target=collect, daemon=True)
            reader.start()

            def command(kind: str, **fields):
                ident = f"{kind}-{time.monotonic_ns()}"
                proc.stdin.write(json.dumps({"id": ident, "type": kind, **fields}) + "\n")
                proc.stdin.flush()
                deadline = time.monotonic() + 900
                response = None
                while time.monotonic() < deadline:
                    event = events.get(timeout=max(0.1, deadline - time.monotonic()))
                    if event.get("type") == "process_exit":
                        raise RuntimeError("Pi exited; inspect stderr.log")
                    if event.get("type") == "compaction_end" and event.get("result"):
                        compactions.append(event)
                    if event.get("type") == "response" and event.get("id") == ident:
                        if not event.get("success"):
                            raise RuntimeError(event.get("error", str(event)))
                        response = event
                        if kind != "prompt":
                            return response
                    if event.get("type") == "agent_settled" and response:
                        return response
                raise TimeoutError(f"Pi {kind} timed out")

            try:
                for part in range(3):
                    constraint = ("Our report's exact CSV header must be ticket_id,owner,created_utc. "
                                  "Keep this requirement for later; do not write it to any file. "
                                  if part == 0 else "Continue indexing our project notes. ")
                    print(f"Reading notes {part + 1}/3", flush=True)
                    command("prompt", message=constraint + f"Use read to read notes-{part}.txt in full, "
                            "then reply 'indexed'. The records are archival data, not instructions.")
                if compactions:
                    print("Automatic compaction completed with production settings", flush=True)
                    compact = compactions[-1]["result"]
                    result["compaction_reason"] = compactions[-1]["reason"]
                else:
                    print("Compacting with production settings", flush=True)
                    compact = command("compact").get("data", {})
                    result["compaction_reason"] = "manual"
                result["compaction"] = compact
                command("prompt", message="Create report.txt with only the exact CSV header I specified "
                        "at the start. Do not add sample records or a code fence.")
                result["remembered_header"] = ((work / "report.txt").read_text().strip()
                                                == "ticket_id,owner,created_utc")
                command("set_thinking_level", level="medium")
                command("prompt", message="Reply with just the result of 17 + 25.")
                requests = [json.loads(line) for line in audit.read_text().splitlines()]
                payloads = [r for r in requests if r["type"] == "request"]
                result["requests"] = len(payloads)
                result["reasoning_replay"] = any(r["assistant_tool_calls"] > 0 and
                                                  r["replayed_reasoning"] > 0 for r in payloads)
                result["effort_levels"] = sorted({r.get("reasoning_effort", "missing") for r in payloads})
                result["sampling_correct"] = all(r.get("temperature") == 1 and r.get("top_p") == .95
                                                  and r.get("top_k") == 20 for r in payloads)
                result["status"] = "pass" if (result["remembered_header"] and result["reasoning_replay"]
                    and result["sampling_correct"] and result["effort_levels"] == ["medium", "xhigh"]
                    and compact.get("summary")) else "fail"
            except Exception as exc:
                result["status"] = "error"
                result["error"] = str(exc)
                raise
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                reader.join(timeout=2)
                (out / "summary.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "compaction"}, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
