#!/usr/bin/env python3
"""Select the installed Qwen profile or restore the previous model settings."""

import json
import os
from pathlib import Path
import re
import sys
import tempfile
import tomllib


def write_private(path, content):
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"qwen", "openai"}:
        raise SystemExit("Usage: select-provider.py qwen|openai")

    root = Path.home() / ".codex"
    config_path = (root / "config.toml").resolve()
    profile_path = root / "qwen.config.toml"
    original_path = root / "qwen-original-settings.json"
    text = config_path.read_text()
    config = tomllib.loads(text)
    profile_text = profile_path.read_text()
    profile = tomllib.loads(profile_text)
    settings = {key: value for key, value in profile.items() if key != "model_providers"}
    original = {key: config.get(key) for key in settings}

    if sys.argv[1] == "qwen":
        if not original_path.exists():
            if config.get("model_provider") == "vllm":
                raise SystemExit("Qwen is already active and original settings are missing.")
            write_private(original_path, json.dumps(original, indent=2) + "\n")
        existing_provider = config.get("model_providers", {}).get("vllm")
        if existing_provider is None:
            text += "\n" + profile_text[profile_text.index("[model_providers.vllm]"):]
        elif existing_provider != profile["model_providers"]["vllm"]:
            raise SystemExit("The existing vllm provider differs from the Qwen profile.")
        if not Path(settings["model_catalog_json"]).is_file():
            raise SystemExit("Install the Qwen model catalog first.")
    else:
        if not original_path.exists():
            raise SystemExit("No saved model settings to restore.")
        settings = json.loads(original_path.read_text())

    table_start = re.search(r"(?m)^\[", text)
    boundary = table_start.start() if table_start else len(text)
    prefix, tables = text[:boundary], text[boundary:]
    keys = "|".join(re.escape(key) for key in settings)
    prefix = re.sub(rf"(?m)^(?:{keys})\s*=.*\n?", "", prefix)
    selected = "".join(
        f"{key} = {json.dumps(value)}\n"
        for key, value in settings.items() if value is not None
    )
    updated = selected + prefix + tables
    tomllib.loads(updated)
    write_private(config_path, updated)
    print(f"Selected {sys.argv[1]} for new Codex tasks. Restart the desktop app to reload it.")


if __name__ == "__main__":
    main()
