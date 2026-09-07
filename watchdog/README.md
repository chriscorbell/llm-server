# GPU wedge watchdog

The `xe` driver can reset a compute or copy engine under sustained load. After the reset the userspace Level Zero context stays wedged, and vLLM hangs until the container restarts. This watchdog notices and restarts it.

It acts only when both signals agree: the health endpoint is failing and a kernel engine-reset signature appeared since the last good check. That pairing is what keeps it from restarting a healthy server during a long prefill.

Vendored from SergiioB's [Intel Arc Pro B70 Inference Cookbook](https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook), MIT licensed, upstream commit `966c593a8b375c4df5173d8d07b6be4db7835fdb`. The unit file is edited for this machine: container `qwen38`, and the health URL on the Tailscale address, because the server does not publish on localhost.

## Install

```bash
ssh vllm 'bash -s' < watchdog/install.sh
```

## Watch it

```bash
ssh vllm 'journalctl -u xpu-wedge-watchdog -f'
```

Every event is one line with an ISO-8601 timestamp. If it ever fires, that is an Experiment: record what the kernel log said and what the load was.
