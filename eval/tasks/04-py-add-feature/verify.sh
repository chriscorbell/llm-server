#!/usr/bin/env bash
set -euo pipefail
python3 -m unittest discover -s . -p 'test_*.py' 2>&1
grep -q -- '--top' summarize.py || { echo "FAIL: --top flag not wired into the CLI"; exit 1; }
