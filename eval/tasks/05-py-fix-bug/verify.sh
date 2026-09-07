#!/usr/bin/env bash
set -euo pipefail
python3 -m unittest discover -s . -p 'test_*.py' 2>&1
