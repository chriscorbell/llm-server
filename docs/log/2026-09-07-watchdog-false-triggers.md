# 2026-09-07 Watchdog accepts unrelated kernel messages

Status: concluded, repair outstanding
Profile: ad hoc, read-only inspection of the installed watchdog

## Hypothesis

The installed watchdog only starts recovery when repeated health failures coincide with a GPU failure signature.

## Configuration

No configuration change. Read the active unit's journal and exercise only the installed signature expression with GNU grep. This command does not invoke recovery:

```bash
ssh vllm python3 - <<'PY'
from pathlib import Path
import re, subprocess
s = Path('/usr/local/bin/xpu-wedge-watchdog.sh').read_text()
pattern = re.search("SIGNATURES='(.*?)'", s, re.S).group(1)
for line in [
    'veth88b9e4a: renamed from eth0',
    'nothing related to a GPU',
    'xe 0000:4c:00.0: [drm] Tile0: GT0: Fault response: Unsuccessful -EINVAL',
]:
    r = subprocess.run(['grep', '-Ei', pattern], input=line+'\n',
                       text=True, capture_output=True)
    print(repr(line), 'exit=', r.returncode, 'match=', repr(r.stdout))
PY
ssh vllm 'journalctl -u xpu-wedge-watchdog --since "2026-09-07 23:00:00 UTC" --no-pager'
```

Installed script SHA-256: `c514d4f25b953bf1042a77288dcb4e5b2f7ef0b922183fc2b1b1262a414c9b3e`.

Baseline: documented behavior in [watchdog README](../../watchdog/README.md).

## Measurements

| Check | Observed |
|---|---|
| Unrelated network message rejected | 0/1 |
| Arbitrary non-GPU sentence rejected | 0/1 |
| Genuine GPU fault message accepted | 1/1 |
| Recovery commands since 23:00 UTC through inspection | 21 |
| Recovery timeout messages in that interval | 19 |
| Successful recovery messages in that interval | 2 |
| Current watchdog state | enabled and active |
| Current inference container state | healthy |

Inference throughput, TTFT, VRAM, MTP acceptance, and coding quality were not measured. These counts do not establish that every restart was unnecessary; real GPU faults also appear in the kernel log.

## What happened

GNU grep treats newlines as separate patterns. Four lines of `SIGNATURES` begin with `|`, creating an empty alternative. Consequently, any line can satisfy the supposed GPU signature check.

The installed watchdog recorded this exact sequence:

```text
[2026-09-08T00:21:08Z] WEDGE trigger=kernel streak=16 first_match=veth88b9e4a: renamed from eth0
[2026-09-08T00:21:08Z] RECOVERY run cmd='docker restart qwen38'
[2026-09-08T00:24:19Z] RECOVERY_FAILED container=qwen38 waited=180s
```

Similar network-message triggers continued through 00:31:11 UTC. It reported recovery at 00:33:27 UTC, after 125 seconds. The matcher reproduction accepted both unrelated strings and the genuine fault string, each with exit code 0.

An initial reproduction on macOS did not match any of the three strings. That result is not applicable to the Linux service; the decisive reproduction used the installed script and GNU grep on `vllm`.

Source inspection also finds that the script advances its kernel baseline on every scan before health is checked. With `FAIL_STREAK=3`, a one-time real fault on the first failed scan can be forgotten by the third scan once the matcher is repaired. The repair therefore needs to retain the fault until health recovers. The existing self-test uses `FAIL_STREAK=1` and cannot check that case. This second defect is a source finding, not a reproduced recovery test.

`recover()` does not save container logs and GPU state before restarting. A dependable repair should capture those first, allow startup time, and limit repeated recovery attempts.

## Outcome

Refuted. The active watchdog does not enforce its documented GPU-signature condition. This is a reliability issue independent of model quality or decode performance.

## Consequences

Recorded the defect in `STATUS.md` and made watchdog repair the first readiness step. No service, watchdog, model, kernel, or driver change was made during this assessment.
