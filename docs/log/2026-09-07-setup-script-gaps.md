# 2026-09-07 Three gaps between the setup script and reality

Status: concluded
Profile: none, this is about the install path
Author: agent thread on mbp

## Hypothesis

The server was brought up by hand across a long session, so `scripts/setup-server.sh` may no longer describe a path that actually works from nothing. Audit it against what the machine turned out to need.

## What was wrong

**The script would have aborted on a fresh install.** It required three image-processor files, following the upstream cookbook's warning that vision serving dies without `preprocessor_config.json`, `processor_config.json` and `video_preprocessor_config.json`. The published checkpoint at revision `9d189a60` ships only `processor_config.json`. Vision works anyway, verified end to end by `eval/vision_check.py` reading a screenshot and returning a stylesheet that passes the layout check. The check now requires the one file that exists, and says what happens if a re-pack drops it.

**Docker Compose was missing and undocumented.** Ubuntu 26.04's Docker packaging does not include the Compose plugin, so every command in the README fails with `docker: unknown command: docker compose`. This was hit during first boot and fixed by hand with `apt install docker-compose-v2`, but it lived only in a log entry, so the next person following the README would hit the same wall. The setup script now checks for it and installs it.

**The health endpoint is not on localhost.** The container publishes on the Tailscale address only, so `curl http://127.0.0.1:8000/health` fails even when run on the server itself. This cost a confusing round of failures when the smoke test was first run there. The default in `scripts/smoke.sh` was already the hostname, which works from both machines, and now carries a comment saying why localhost does not.

## Outcome

Confirmed, three separate defects. Two would have broken a fresh install outright.

## Consequences

`scripts/setup-server.sh` fixed on both counts and syntax checked. `scripts/smoke.sh` annotated. Worth noting the general shape: the errors were not in anything measured today, they were in the path nobody had walked end to end since the machine started working. A cookbook that only describes the state you arrived at is not a cookbook.
