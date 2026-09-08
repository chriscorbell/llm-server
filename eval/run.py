#!/usr/bin/env python3
"""Run the coding task suite against a model through opencode and score it.

Each task gets a fresh copy of its fixture in a temporary directory, so tasks are
independent and repeatable. Pass or fail comes from the task's verify.sh, never
from reading the model's prose.

  ./run.py --model llm-server/qwen38
  ./run.py --client pi --model llm-server/qwen38 --tasks 02,08
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS_DIR = HERE / "tasks"


def discover(selector: str | None) -> list[Path]:
    tasks = sorted(p for p in TASKS_DIR.iterdir() if (p / "prompt.md").exists())
    if not selector:
        return tasks
    wanted = {s.strip() for s in selector.split(",") if s.strip()}
    return [t for t in tasks if t.name.split("-")[0] in wanted or t.name in wanted]


def run_task(task: Path, model: str, timeout: int, keep: bool,
             client: str, thinking: str) -> dict:
    workdir = Path(tempfile.mkdtemp(prefix=f"eval-{task.name}-"))
    shutil.copytree(task / "fixture", workdir, dirs_exist_ok=True)

    setup = task / "setup.sh"
    if setup.exists():
        subprocess.run(["bash", str(setup)], cwd=workdir, check=True,
                       stdout=subprocess.DEVNULL)

    prompt = (task / "prompt.md").read_text().strip()
    screenshot = task / "screenshot.png"
    if (client == "opencode" and screenshot.exists()
            and not os.environ.get("EVAL_CLIENT_SENDS_IMAGES")):
        # opencode 1.18.27 attaches images with mime text/plain, so the model never
        # receives an image and the task measures the client, not the model. Score
        # vision with eval/vision_check.py against the API instead. Set
        # EVAL_CLIENT_SENDS_IMAGES=1 once the client is fixed to re-enable this.
        shutil.rmtree(workdir, ignore_errors=True)
        return {
            "task": task.name, "status": "skip", "seconds": 0.0, "verify_exit": 2,
            "verify_tail": ["skipped: this client cannot attach images;"
                            " run eval/vision_check.py"],
            "workdir": None,
        }, "skipped: client cannot attach images"

    if client == "opencode":
        cmd = ["opencode", "run", "--dir", str(workdir), "-m", model, "--auto",
               "--title", f"eval {task.name}"]
        if screenshot.exists():
            # --file is a greedy array option: "-f path prompt" swallows the prompt as a
            # second filename and fails with "File not found". The = form takes one value.
            cmd += [f"--file={screenshot}"]
        cmd += [prompt]
    else:
        cmd = ["pi", "--no-session", "--approve", "--model", model,
               "--thinking", thinking, "--mode", "json", "--tools",
               "read,bash,edit,write,grep,find,ls", "-p"]
        if screenshot.exists():
            cmd += [f"@{screenshot}"]
        cmd += [prompt]

    started = time.monotonic()
    timed_out = False
    try:
        agent = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                               timeout=timeout)
        agent_out = agent.stdout + agent.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        agent_out = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    elapsed = time.monotonic() - started

    env = {**os.environ, "TASK_DIR": str(task)}
    verify = subprocess.run(["bash", str(task / "verify.sh")], cwd=workdir,
                            capture_output=True, text=True, env=env, timeout=600)
    status = {0: "pass", 2: "skip"}.get(verify.returncode, "fail")
    if timed_out:
        status = "timeout"

    result = {
        "task": task.name,
        "status": status,
        "seconds": round(elapsed, 1),
        "verify_exit": verify.returncode,
        "verify_tail": verify.stdout.strip().splitlines()[-12:],
        "workdir": str(workdir) if keep else None,
    }
    if not keep:
        shutil.rmtree(workdir, ignore_errors=True)
    return result, agent_out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", choices=("opencode", "pi"), default="opencode")
    ap.add_argument("--model", required=True, help="opencode provider/model")
    ap.add_argument("--thinking", default="xhigh", help="Pi thinking level")
    ap.add_argument("--tasks", help="comma separated task numbers, default all")
    ap.add_argument("--out", help="directory for results, default eval/results/<timestamp>")
    ap.add_argument("--timeout", type=int, default=3600, help="seconds per task")
    ap.add_argument("--keep", action="store_true", help="keep the temporary workdirs")
    a = ap.parse_args()

    tasks = discover(a.tasks)
    if not tasks:
        print("no tasks matched", file=sys.stderr)
        return 1

    out = Path(a.out) if a.out else HERE / "results" / time.strftime("%Y-%m-%dT%H-%M")
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for task in tasks:
        print(f"--- {task.name}", flush=True)
        result, agent_out = run_task(task, a.model, a.timeout, a.keep,
                                     a.client, a.thinking)
        (out / f"{task.name}.log").write_text(agent_out)
        results.append(result)
        print(f"    {result['status']} in {result['seconds']}s", flush=True)

    passed = sum(r["status"] == "pass" for r in results)
    scored = sum(r["status"] != "skip" for r in results)
    summary = {"client": a.client, "model": a.model, "thinking": a.thinking,
               "when": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "passed": passed, "scored": scored, "results": results}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = [f"# Task suite: {a.model}", "", f"{passed} of {scored} passed.", "",
             "| Task | Result | Seconds |", "|---|---|---|"]
    lines += [f"| {r['task']} | {r['status']} | {r['seconds']} |" for r in results]
    (out / "summary.md").write_text("\n".join(lines) + "\n")

    print(f"\n{passed}/{scored} passed. Results in {out}")
    return 0 if passed == scored else 1


if __name__ == "__main__":
    raise SystemExit(main())
