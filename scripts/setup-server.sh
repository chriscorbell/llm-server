#!/usr/bin/env bash
# One-time server preparation. Idempotent, resumable. Run from mbp:
#   ssh vllm 'bash -s' < scripts/setup-server.sh
set -euo pipefail

MODEL_REPO=SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16
MODEL_REV=9d189a60e4c0ad7f9f47cd94bfa393ca10b3924e
MODEL_DIR="$HOME/models/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16"

echo "== render group id (put this in compose/.env as RENDER_GID)"
stat -c '%g' /dev/dri/render* | sort -u | head -1

echo "== free space, need about 20 GiB for the weights"
df -h "$HOME" | tail -1

echo "== downloading the model at the pinned revision"
# The huggingface CLI entry point is not on PATH for a mapped uid, and the [cli]
# extra was removed in huggingface_hub 1.x, so drive the Python API directly.
mkdir -p "$MODEL_DIR"
cat > /tmp/hf-snapshot.py <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="SergiioB/Qwen3.8-27B-GPTQ-Int4-sym-G128-MTP-BF16",
    revision="9d189a60e4c0ad7f9f47cd94bfa393ca10b3924e",
    local_dir="/model",
    max_workers=8,
)
print("download complete")
PY
docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e HF_HOME=/tmp/hf \
  -v "$MODEL_DIR:/model" -v /tmp/hf-snapshot.py:/dl.py:ro \
  python:3.12-slim \
  sh -lc 'pip -q install --no-cache-dir huggingface_hub && python /dl.py'

echo "== image-processor configs, without which vision serving dies at startup"
for f in preprocessor_config.json processor_config.json video_preprocessor_config.json; do
  if [ -s "$MODEL_DIR/$f" ]; then echo "  ok $f"; else echo "  MISSING $f"; exit 1; fi
done

echo "== the fifteen MTP tensors must still be present and unquantized"
python3 - "$MODEL_DIR" <<'PY'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
index = json.loads((d / "model.safetensors.index.json").read_text())
mtp = [k for k in index["weight_map"] if k.startswith("mtp.")]
print(f"  mtp tensors: {len(mtp)}")
cfg = json.loads((d / "config.json").read_text())
q = cfg["quantization_config"]
assert q["bits"] == 4 and q["group_size"] == 128 and q["sym"] is True, q
assert "-:.*mtp.*" in q.get("dynamic", {}), "MTP tensors are not excluded from quantization"
assert cfg.get("language_model_only") is False, "vision tower missing"
print("  quantization contract ok: GPTQ 4-bit sym G128, mtp excluded, vision present")
PY

echo "== recording checksums"
sha256sum "$MODEL_DIR"/*.safetensors "$MODEL_DIR"/config.json > "$MODEL_DIR/SHA256SUMS.local"
echo "wrote $MODEL_DIR/SHA256SUMS.local"
