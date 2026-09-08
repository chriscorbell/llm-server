# 2026-09-07 CPU governor makes no difference; pinning untested

Status: partial, cancelled before the pinning arm completed
Profile: A, BF16 KV at 98,304
Author: agent thread on mbp

## Hypothesis

During decode one CPU thread runs at 99.5% while the GPU holds its boost clock, and measured decode sits about 30% below what memory bandwidth allows. If that single engine-core loop is the limiter, then keeping its core at full clock, or keeping it on one L3 slice instead of migrating across the eight on this Threadripper, should show up as throughput.

## Configuration

The governor arms were measured live on one container, so no restart noise sits between them. The pinning arm needed a restart because `cpuset` is a container property.

## Measurements

| Arm | Decode at 512 | Decode at 8,192 |
|---|---|---|
| schedutil, unpinned | 44.9 tok/s | 43.1 tok/s |
| performance, unpinned | 42.5 tok/s | 42.9 tok/s |

Draft acceptance sat between 38.6% and 43.1% across every arm, with no pattern.

## Outcome

The governor does nothing, which is the expected result once you check the machine rather than the setting. Boost was already enabled and cores were already running at 4.34 GHz under load, so `performance` had nothing left to ask for. The 2.4 tok/s difference at 512 runs the wrong way and sits inside the spread seen all day.

The pinning arm produced no valid measurement and was then cancelled at Chris's request.

Its first attempt was invalid in a way worth recording. The run reported `cpuset=` empty: the variable was lost through nested quoting in the driver, so the container ran unpinned while the log claimed otherwise. The numbers looked like a clean null result and would have been reported as "pinning does not help" from a run where pinning was never on. Verifying `docker inspect -f '{{.HostConfig.CpusetCpus}}'` is what caught it, and any future arm should assert the setting actually applied before trusting the throughput.

`cpuset: "${CPUSET:-}"` in the compose file is verified working; setting `CPUSET=0-3,32-35` produces `CpusetCpus=[0-3,32-35]` on the container.

## Consequences

Governor left at schedutil, the machine's default. The container runs unpinned. Both were restored and verified after cancellation.

The question of whether the engine-core thread is the limiter stays open in `STATUS.md`. Pinning is the cheap remaining test; the expensive and more likely answer is that per-step launch overhead on this XPU stack, where graph capture only covers batch sizes 1 through 8, is what separates measured decode from the bandwidth ceiling.
