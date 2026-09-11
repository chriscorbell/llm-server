#!/usr/bin/env bash
# Collect GPU and driver state. Run this BEFORE restarting anything, because a
# restart destroys the evidence a log entry needs.
set -uo pipefail
echo "=== date ==="; date -Is
echo "=== xe driver and card ==="
sudo dmesg --time-format iso | grep -iE ' xe |level.?zero|GPU HANG|reset|VRAM' | tail -40
echo "=== VRAM ==="
if command -v xpu-smi >/dev/null; then xpu-smi stats -d 0 2>/dev/null | head -30; fi
cat /sys/class/drm/card0/device/tile0/gt0/freq0/cur_freq 2>/dev/null | sed 's/^/gt0 cur_freq: /'
echo "=== container ==="
docker ps -a --filter name=qwen38 --format '{{.Names}}\t{{.Status}}\t{{.Image}}'
echo "=== last 60 container log lines ==="
docker logs --tail 60 qwen38 2>&1 || echo "no container"
echo "=== health endpoint ==="
curl -fsS -m 5 "${BASE_URL:-http://100.103.136.98:${PORT:-8000}}/health" && echo " OK" || echo " UNREACHABLE"
