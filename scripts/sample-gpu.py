#!/usr/bin/env python3
"""Sample global B70 VRAM usage and clock without creating a GPU context.

Run on the server through SSH with sudo. Prints one JSON object per second.
Use the timestamps to join samples to benchmark started_at/finished_at values.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=int, default=3600)
args = parser.parse_args()
memory = Path("/sys/kernel/debug/dri/0000:4c:00.0/tile0/vram_mm")
frequency = Path("/sys/class/drm/card0/device/tile0/gt0/freq0/cur_freq")
print(json.dumps({"pid": os.getpid(), "started_at": time.time()}), flush=True)
for _ in range(args.seconds):
    text = memory.read_text()
    used = int(re.search(r"^\s*usage:\s*(\d+)$", text, re.M)[1])
    total = int(re.search(r"^\s*size:\s*(\d+)$", text, re.M)[1])
    print(json.dumps({"time": time.time(), "vram_used_bytes": used,
                      "vram_total_bytes": total, "gpu_mhz": int(frequency.read_text())}), flush=True)
    time.sleep(1)
