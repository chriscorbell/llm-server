#!/usr/bin/env python3
"""Score the vision task against the API directly.

opencode 1.18.27 attaches images with mime text/plain through `run --file`, so the
model never receives an image and the task cannot be scored through that client.
This talks to the server the way any correct client would: one user turn holding a
text part and an image_url part carrying a data URL.

The model must name the defect and return the corrected stylesheet. The result is
checked by the same headless layout verifier the opencode task uses, so a passing
score here means the same thing it would have meant there.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

TASK = Path(__file__).resolve().parent / "tasks" / "08-vision-css"

PROMPT = """The attached screenshot shows this page rendered at 1280 by 800.

Here is the stylesheet that produced it:

```css
{css}
```

Something is visibly wrong with the layout. Describe the defect in one sentence,
then return the complete corrected stylesheet in a single ```css fenced block.

Do not change the sidebar's width and do not stop it being fixed to the left edge.
"""


def ask(base_url: str, key: str, model: str, css: str, png: bytes) -> str:
    body = {
        "model": model,
        "max_tokens": 8192,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT.format(css=css)},
            {"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(png).decode()}},
        ]}],
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    message = json.loads(urllib.request.urlopen(req, timeout=1800).read())["choices"][0]["message"]
    return message.get("content") or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://100.103.136.98:8000")
    ap.add_argument("--key", default=os.environ.get("LLM_SERVER_API_KEY", ""))
    ap.add_argument("--model", default="qwen38")
    a = ap.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="vision-check-"))
    shutil.copytree(TASK / "fixture", workdir, dirs_exist_ok=True)
    css = (workdir / "styles.css").read_text()
    png = (TASK / "screenshot.png").read_bytes()

    answer = ask(a.base_url, a.key, a.model, css, png)
    print("--- model answer, first 400 chars ---")
    print(answer[:400])

    blocks = re.findall(r"```(?:css)?\s*\n(.*?)```", answer, re.S)
    if not blocks:
        print("\nFAIL: the reply contained no fenced stylesheet")
        return 1
    (workdir / "styles.css").write_text(max(blocks, key=len))

    verify = subprocess.run(["bash", str(TASK / "verify.sh")], cwd=workdir,
                            capture_output=True, text=True,
                            env={**os.environ, "TASK_DIR": str(TASK)}, timeout=300)
    print("\n--- verifier ---")
    print(verify.stdout.strip() or verify.stderr.strip())
    shutil.rmtree(workdir, ignore_errors=True)
    return verify.returncode


if __name__ == "__main__":
    raise SystemExit(main())
