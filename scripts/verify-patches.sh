#!/usr/bin/env bash
# Verify the vendored patches still match the upstream hashes recorded in NOTICE.md.
set -euo pipefail
cd "$(dirname "$0")/../compose/patches"
sha256sum -c - <<'SUMS'
4d7a02c4ea10ca7c00dc89ad927fa3dafa747dbf0553d2adf24e30a3c53e9c14  patch_mtp_nightly.py
41d2f74e5fef1f074b76b5a90dd1016de437228431802cfb1fa7bd7ce4cc9b50  patch_mtp_boundary.py
8e4a3cbe5f424f308af74ff215d0fcb8d31f63ac3f07cf359ed2269956c3fc80  patch_gdn_mixed_split_v5.py
SUMS
