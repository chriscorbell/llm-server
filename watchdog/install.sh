#!/usr/bin/env bash
# Install the wedge watchdog as a systemd unit. Run from mbp:
#   ssh vllm 'bash -s' < watchdog/install.sh
set -euo pipefail
cd "$HOME/Code/llm-server"

echo "== offline self-test before installing"
bash watchdog/xpu-wedge-watchdog.sh --self-test

sudo install -m 0755 watchdog/xpu-wedge-watchdog.sh /usr/local/bin/xpu-wedge-watchdog.sh
sudo install -m 0644 watchdog/xpu-wedge-watchdog.service /etc/systemd/system/xpu-wedge-watchdog.service
sudo systemctl daemon-reload

sudo systemctl enable xpu-wedge-watchdog
sudo systemctl restart xpu-wedge-watchdog
sleep 2
systemctl --no-pager --lines=10 status xpu-wedge-watchdog || true
