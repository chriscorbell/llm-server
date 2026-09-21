# DeepSeek V4.1 Flash with RAM and NVMe offloading

Checked September 11, 2026. This is source research, not an Experiment. No checkpoint was downloaded, no inference request was run, and no server configuration changed. Chris's objective is maximum local agentic capability; fitting all weights in VRAM is not a requirement.

## Decision

DeepSeek V4.1 Flash deserves consideration as a capability upgrade. The sources checked so far do not establish a working deployment on this server's one Intel Arc Pro B70, 60 GiB usable host RAM, and NVMe storage. Retain Qwen3.8-27B as the working default, while treating a correct V4.1 runtime with expert streaming as a separate feasibility question. Lack of VRAM residency does not prove a model impossible to run.

## What the successful NVMe deployment actually does

The published [four-GPU deployment](https://github.com/0xSero/deepseek-v4.1-flash-4x-rtx-pro-6000) runs the native mixed-precision checkpoint, about 510 GB on disk. It keeps the approximately 189 GiB Engram lookup tables on NVMe and uses a bounded 64 GiB row cache on a 128 GB host. Cache misses fetch original rows and scales. Its requirements still include four 96 GB RTX PRO 6000 Blackwell GPUs and CUDA 13. The launcher checks for those exact GPUs. Arithmetic, JSON, a tool round trip and a single image pass; broader quality and reliability checks remain pending. This is evidence that Engram offloading works, not a measurement on a small single-GPU system.

[SGLang's implementation report](https://www.lmsys.org/blog/2026-09-10-deepseek-v41) explains why this is useful: the tables are large, but each decoding step reads few rows. Its host-memory placement moves the tables off the GPU while dequantization, gating and projection stay on the GPU. Neither this mechanism nor KV-cache offloading removes the separate memory requirement for the model's expert weights.

For this server, the remaining weights also exceed available RAM and VRAM at the published precision. A runtime would need to stream computation weights from storage, use a separately validated smaller quantization, or both. The NVMe lookup result alone does not establish the latency or correctness of that additional mechanism.

## Portable runtime status

The [V4.1 GGUF author](https://huggingface.co/vcruz305/DeepSeek-V4.1-Flash-GGUF) explicitly says these files do not run on upstream llama.cpp yet. Conversion works; a separate runtime branch has the loader, Engram and hyper-connections, with sparse attention still missing. The published Q2_K tensor payload is 246.3 GiB and Q3_K_M is 323.4 GiB. These are artifact measurements, not successful inference or quality results. The [conversion pull request](https://github.com/ggml-org/llama.cpp/pull/28696) also labels itself conversion-only. A downloadable GGUF does not establish an Intel execution path.

[FreeToken](https://github.com/FlashML-org/FreeToken) currently advertises DeepSeek V4 Flash and NVIDIA RTX 30/40/50 support. That source does not establish support for V4.1 Flash on Intel XPU. An isolated CPU expert-kernel measurement would also be insufficient to establish complete model inference.

Actual SSD expert streaming exists for the older DeepSeek V4 Flash 0731 in [Whallm](https://github.com/yanun0323/Whallm), formerly `deepseek_ssd`. Common tensors stay in memory while requested routed experts load from SSD. The implementation targets Apple Silicon and lists V4 Flash 0731 and Qwen3.8 Flash Next. It demonstrates that SSD capacity can extend the feasible model size; it does not demonstrate V4.1 support or an Intel port.

## What would change the recommendation

A useful reproduction needs the exact V4.1 checkpoint revision and precision, the engine commit, a complete generated response, working multi-turn tool calls, and the hardware and memory allocation. It must distinguish Engram lookup offload, expert weight offload and KV-cache offload. For this machine, measure actual prompt length, concurrency, cold and cached first-token time, decoding rate, RAM/VRAM peaks and SSD bytes read. Do not predict local speed from another GPU or from a CPU kernel microbenchmark.

The current server was checked over SSH at 15:25 UTC: Qwen is healthy with zero Docker restarts, MTP4, FP16 KV, a 98,304-token limit, and the original pinned image. Pi still uses xhigh and compacts above 57,344 estimated tokens. No fresh quality comparison has been run. [Model selection assessment](2026-09-11-local-model-alternatives.md)

## Follow-up: cheaper CPU and SSD routes

Further research on September 11 found new implementations beyond the NVIDIA deployment above. These are upstream reports, not local reproductions. The four-GPU recipe is not a minimum hardware requirement.

The [Day1DeepseekV4.1-CPU fork](https://github.com/gjabdelnoor/Day1DeepseekV4.1-CPU), inspected at commit `7b5a4b3a5b0d61b8c6f4407aa91ed52461ea3a63`, adds CPU Engram, sparse-indexer and shared-band attention kernels. Its author used a Xeon Gold 6338 with AVX-512. The [author's deployment report](https://www.reddit.com/r/LocalLLaMA/comments/1wcu3fw/cpu_only_experimental_sloppy_deepseek_v41_flash/) specifies eight 64 GB DDR4 RDIMMs and Engram tables on a SATA SSD. Published throughput lacks exact prompt length and concurrency, so it is not a transferable benchmark. The README reports only short-prompt spot checks and one long retrieval, with no perplexity or reference-model comparison. Architecture correctness, agentic quality and compatibility with this Threadripper remain unvalidated. The code establishes a concrete CPU candidate to inspect; buying hardware does not resolve those gaps.

[Salvatore Sanfilippo reports V4.1 SSD streaming on a 128 GB M5 Max](https://bsky.app/profile/antirez.bsky.social/post/3mv6sb4qkrc2o). The announcement says release awaits quality checks and omits quantization, context length and concurrency. The inspected [DwarfStar README](https://github.com/antirez/ds4) lists Metal, CUDA and ROCm, with V4.1 absent from its supported-model list. This is evidence against treating 512 GB RAM as an architectural minimum, but not a ready Intel Arc deployment.

[Vontra's experimental two-bit MLX build](https://huggingface.co/Vontra/DeepSeek-V4.1-Flash-MLX-2bit-MTP) includes a custom text runtime. On a 256 GiB M3 Ultra, it reports 160.88 GiB resident backbone, 57.22 GiB Engram on SSD and 166.69 GiB peak process RSS. Validation covers two short prompts, with a 128-token diagnostic context cap; tool calls and broad quality are untested. It does not prove that a 192 GB Threadripper upgrade would provide a usable agent. Two-bit quality must be evaluated separately from DeepSeek's published scores.

[PipeNetwork's custom MLX port](https://huggingface.co/pipenetwork/DeepSeek-V4.1-Flash-MLX-mixed-4_8bit) targets a 512 GB Mac and reports numerical checks plus WikiText-2 perplexity. It is another non-NVIDIA implementation, but does not establish the cheapest route or Intel support.

For Chris, the next purchase decision should follow runtime validation. An existing-machine experiment costs no hardware money. A used DDR4 server with 512 GB is a candidate for holding the backbone in RAM and Engram on SSD, while a correct expert-streaming implementation may reduce that capacity requirement. See the [hardware and price assessment](2026-09-11-deepseek-budget-hardware.md). No hardware was purchased and no service was changed.

Code inspection found two practical details for that future experiment. The CPU fork's `scripts/build-cpu-dsv41.sh` forces `GGML_AVX512=ON`, which must not be copied unchanged for the AVX2 Threadripper. Its inherited argument parser has `--no-repack` and `--lazy-mode`; avoiding a resident repacked copy is a possible step toward testing disk-backed weights. Engram lazy reads alone are not a measured expert-streaming implementation. Neither a native CPU build nor an actual 64 GB inference run has been attempted. The local Mac is an M5 Pro with 48 GiB, so the 128 GB M5 Max report is not a matching owned machine either.
