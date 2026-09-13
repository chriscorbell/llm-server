#!/usr/bin/env python3
"""Download and verify the pinned Turbo GGUF and vision projector on vllm."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def verified(path, spec):
    if not path.is_file() or path.stat().st_size != spec["size"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == spec["sha256"]


def main():
    manifest = json.loads((Path(__file__).resolve().parents[1] / "compose/turbo-model.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path.home() / "models" / manifest["directory"])
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    for spec in manifest["files"]:
        target = args.directory / spec["name"]
        if verified(target, spec):
            print(f"Verified existing {target.name}", flush=True)
            continue
        if target.exists():
            raise SystemExit(f"Checksum mismatch: {target}. Preserve it and choose another directory.")
        partial = target.with_suffix(target.suffix + ".partial")
        url = f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{spec['name']}"
        started = time.monotonic()
        print(f"Downloading {spec['name']} ({spec['size']} bytes)", flush=True)
        subprocess.run([
            "curl", "--fail", "--location", "--silent", "--show-error",
            "--retry", "5", "--connect-timeout", "30", "--continue-at", "-",
            "--output", str(partial), url,
        ], check=True)
        if not verified(partial, spec):
            raise SystemExit(f"Checksum mismatch: {partial}. Partial file retained for inspection.")
        partial.replace(target)
        print(f"Verified {target.name} in {time.monotonic() - started:.1f} s", flush=True)


if __name__ == "__main__":
    main()
