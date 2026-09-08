# Vendored patches

These runtime patches come from the [Intel Arc Pro B70 Inference Cookbook](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook) by SergiioB, MIT licensed. Vendored at upstream commit `966c593a8b375c4df5173d8d07b6be4db7835fdb`, fetched 2026-09-07.

They are copied rather than submoduled so that a Profile is reproducible from this repository alone. Verify them with `scripts/verify-patches.sh` before blaming the engine for a startup failure.

| File | SHA-256 | What it does |
|---|---|---|
| `patch_mtp_nightly.py` | `4d7a02c4ea10ca7c00dc89ad927fa3dafa747dbf0553d2adf24e30a3c53e9c14` | Builds the preserved BF16 MTP draft outside the GPTQ quantization config, so native speculative decoding loads. |
| `patch_mtp_boundary.py` | `41d2f74e5fef1f074b76b5a90dd1016de437228431802cfb1fa7bd7ce4cc9b50` | Handles the partial final speculative group at the exact 131,072-token boundary. |
| `patch_draft_lmhead_int4.py` | `db3768becdf1ac52a54dbd27a89ceb42338f8febbd32b1f9c8b6d6ffdd76649b` | Quantizes a copy of the draft's LM head to INT4 g128 at load and routes the draft's logit passes through it. Gated by `B70_DRAFT_LMHEAD_INT4=1`; a no-op without it. Target verification stays FP16. |
| `patch_draft_mtp_int4.py` | `2f6d36c419438862157ad0b625a12264f84ea8c7a6d026d6d0d414aa46a14405` | Quantizes the five draft MTP linears to INT4 g128 in `load_weights` and frees their BF16 copies. Gated by `B70_DRAFT_MTP_INT4=1`; a no-op without it. |
| `patch_gdn_mixed_split_v5.py` | `8e4a3cbe5f424f308af74ff215d0fcb8d31f63ac3f07cf359ed2269956c3fc80` | Fixes a crash in `gdn_attention` on batches that mix speculative and non-speculative sequences. Only needed when `MAX_NUM_SEQS` is above 1. Not applied by default. |

Do not edit these files. If one needs changing, record why in a log entry and keep the upstream copy alongside.
