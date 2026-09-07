#!/usr/bin/env bash
# Renders the page headless and measures the layout. The check script is injected
# into a temporary copy, so the agent under test cannot edit the check itself.
set -euo pipefail

CHROME="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [ ! -x "$CHROME" ]; then
  echo "SKIP: no Chrome at $CHROME (set CHROME_BIN)"
  exit 2
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp styles.css "$tmp/"
python3 "$TASK_DIR/inject-check.py" "$tmp"

dom="$("$CHROME" --headless --disable-gpu --window-size=1280,800 \
      --virtual-time-budget=3000 --dump-dom "file://$tmp/index.html" 2>/dev/null)"

# Match the rendered <title>, not the string literals inside the injected script.
if echo "$dom" | grep -q '<title>LAYOUT_PASS</title>'; then
  echo "layout ok: the main content clears the fixed sidebar"
else
  echo "FAIL: the main content still sits under the fixed sidebar"
  exit 1
fi
