# 2026-09-11 Monitor Xe GPU activity with gputop

Status: concluded
Profile: ad hoc
Author: agent thread on mbp

## Hypothesis

`intel_gpu_top` failed only because its automatic device selection looked for `i915`; selecting the B70's DRM node explicitly would make it monitor the `xe` device.

## Configuration

No configuration changed. The server continued running profile `a-int4draft`. These read-only probes compared automatic selection, explicit selection and the generic DRM fdinfo monitor from the same installed `igt-gpu-tools` 2.3-1 package:

```bash
sudo intel_gpu_top -L
sudo intel_gpu_top
sudo intel_gpu_top -d drm:/dev/dri/card0 -l -s 250 -n 2
sudo gputop -n 2 -d 0.5
```

Baseline for comparison: none. This was an operational tooling check, not an inference benchmark.

## Measurements

| Probe | Result |
|---|---|
| Kernel driver for `/dev/dri/card0` | `xe` |
| `intel_gpu_top -L` | Listed Intel Battlemage device `0xe223` as `card0` and `renderD128` |
| `intel_gpu_top` automatic selection | Exit 1 |
| `intel_gpu_top -d drm:/dev/dri/card0` | Exit 1 |
| `intel_gpu_top -d drm:/dev/dri/renderD128` | Exit 1 |
| `gputop -n 2 -d 0.5` | Exit 0; two samples displayed |
| Idle engine activity in the two `gputop` samples | 0.0% |
| Largest vLLM allocation shown by `gputop` | 31 GiB allocated, 30 GiB resident |

## What happened

Automatic selection failed with:

```text
No device filter specified and no discrete/integrated i915 devices found
```

Explicit selection found the DRM node but failed when `intel_gpu_top` tried to discover i915-style engine counters:

```text
Failed to detect engines! (No such file or directory)
(Kernel 4.16 or newer is required for i915 PMU support.)
```

The kernel does expose the B70 PMU as `/sys/bus/event_source/devices/xe_0000_4c_00.0`. Its events are `engine-active-ticks`, `engine-total-ticks`, GT frequency and GT C6 residency. They are not the per-engine `*-busy` files that `intel_gpu_top` 2.3 discovers. The [2.3 source](https://gitlab.freedesktop.org/drm/igt-gpu-tools/-/blob/v2.3/tools/intel_gpu_top.c) confirms that automatic selection calls the i915-only device finders and engine discovery scans for names ending in `-busy`.

`gputop`, installed by the same package, successfully read the DRM fdinfo accounting exposed for the `xe` clients. It displayed the vLLM processes, memory allocation and resident memory, plus render, video, vector, copy and compute activity columns.

## Outcome

Refuted. An explicit DRM selector gets past device selection but does not make `intel_gpu_top` compatible with this `xe` PMU interface. Use `sudo gputop` for interactive utilization and per-process GPU memory monitoring on this server.

## Consequences

No server configuration changed and the inference container was not restarted. A Finding was added to `STATUS.md` so future sessions use `gputop` instead of repeating the failed `intel_gpu_top` selectors.
