# 2026-09-11 Check btop monitoring for the Xe B70

Status: concluded
Profile: ad hoc
Author: agent thread on mbp

## Hypothesis

The installed GPU-enabled `btop` build would detect the Arc Pro B70 and provide historical GPU graphs alongside its CPU, memory, network and process panels.

## Configuration

No configuration changed. The running profile remained `a-int4draft`. The read-only check used the distribution build already installed on `vllm`:

```bash
btop --version
sudo timeout 4s btop --tty
```

Baseline for comparison: [`gputop` Xe monitoring](2026-09-11-xe-gpu-monitoring.md), which detects the B70 and its vLLM clients but does not draw history graphs.

## Measurements

| Probe | Result |
|---|---|
| Installed btop package | 1.4.6-2 |
| Build configuration | `GPU_SUPPORT=true` |
| Kernel driver | `xe` |
| GPU panel or GPU hotkey in the live UI | Absent |
| CPU, memory, disk, network and process panels | Present |

## What happened

`btop` started normally and displayed its system panels, but it did not add a GPU panel or a GPU toggle for the B70. This was not caused by a GPU-disabled package build; `btop --version` reports `GPU_SUPPORT=true`.

The [1.4.6 Linux collector source](https://github.com/aristocratos/btop/blob/v1.4.6/src/linux/btop_collect.cpp) defines its Intel PMU device as `i915` and initializes it through the same i915-style engine discovery that fails in `intel_gpu_top` on this server. The newer `xe` PMU name and event layout have no separate path in that release.

Ubuntu 26.04 offers `nvtop` 3.2.0-2 but it is not installed. Upstream identifies 3.2.0 as the release that added `xe` support. That makes `nvtop` the next candidate for a graphing GPU TUI, but this check did not install or run it.

## Outcome

Refuted. `btop` 1.4.6-2 cannot provide B70 graphs with the `xe` driver despite being compiled with GPU support.

## Consequences

No server configuration changed and the inference container was not restarted. `STATUS.md` now records the `btop` limitation and the untested `nvtop` 3.2.0-2 candidate.
