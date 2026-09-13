#!/usr/bin/env python3
"""Check Qwen3.8 GPTQ, MTP and vision metadata without loading weights or a GPU."""
import argparse
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    config = json.loads((args.directory / "config.json").read_text())
    quant = config["quantization_config"]
    expected = {"quant_method": "gptq", "bits": 4, "group_size": 128,
                "sym": True, "desc_act": False}
    for key, value in expected.items():
        if quant.get(key) != value:
            raise SystemExit(f"Unexpected {key}: {quant.get(key)!r}; expected {value!r}")
    if config["architectures"] != ["Qwen3_5ForConditionalGeneration"]:
        raise SystemExit("Expected the multimodal Qwen3.5 architecture")
    if not (args.directory / "processor_config.json").is_file():
        raise SystemExit("Missing processor_config.json")

    index = json.loads((args.directory / "model.safetensors.index.json").read_text())["weight_map"]
    headers = {}
    for shard in sorted(set(index.values())):
        with (args.directory / shard).open("rb") as source:
            size = struct.unpack("<Q", source.read(8))[0]
            if size > 16 * 1024 * 1024:
                raise SystemExit(f"Unexpected Safetensors header size in {shard}: {size}")
            headers[shard] = json.loads(source.read(size))
    mtp = {name: headers[shard][name] for name, shard in index.items()
           if name.startswith("mtp.")}
    if len(mtp) != 15 or any(tensor["dtype"] != "BF16" for tensor in mtp.values()):
        raise SystemExit("Expected exactly 15 preserved BF16 MTP tensors")
    vision = [name for name in index if name.startswith("model.visual.")]
    if not vision:
        raise SystemExit("Vision tensors are missing")
    qweights = [name for name in index if name.endswith(".qweight")]
    if len(qweights) != 400:
        raise SystemExit(f"Expected 400 quantized body tensors, found {len(qweights)}")
    print(json.dumps({"passed": True, "quantization": expected,
                      "shards": len(headers), "qweight_tensors": len(qweights),
                      "vision_tensors": len(vision), "mtp_tensors": len(mtp),
                      "mtp_dtype": "BF16",
                      "mtp_shapes": {name: tensor["shape"] for name, tensor in mtp.items()}},
                     indent=2))


if __name__ == "__main__":
    main()
