# Pi configuration moved

The complete MacBook Pi configuration is now in the private [pi-config repository](https://github.com/chriscorbell/pi-config), checked out at `/Users/chris/Code/pi-config`.

That includes `models.json`, global settings and prompt additions, the `llm-server` extension, package pins, advisor/web/goal/todo settings, Orca extension snapshots, Pi GUI preferences, and the source for this repository's three Pi prompt templates. There is no current Pi configuration to edit under `clients/pi` anymore.

Install or compare the configuration from its new checkout:

```sh
cd ~/Code/pi-config
python3 scripts/config.py install
python3 scripts/config.py check
```

The installer links the project-specific `bench`, `log`, and `status` prompts into this repository's ignored `.pi/prompts/` directory. Their scope remains this project. Global instructions still come from the shared AGENTS.md repository.

`eval/pi_contract.py` and `eval/pi_warmup.py` read `~/Code/pi-config/agent/` by default. Set `PI_CONFIG_REPO` to the pi-config checkout if it lives elsewhere. They continue to run from this server repository because they measure the inference service's Pi contract and cache behavior.

Inference deployment and historical experiments remain here. [Migration and verification](../../docs/log/2026-09-22-pi-config-migration.md).
