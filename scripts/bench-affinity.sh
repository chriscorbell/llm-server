#!/usr/bin/env bash
# Compare one-CCX pinning with the unpinned baseline without restarting vLLM.
# Each arm gets six measured code repetitions across three alternating pairs.
set -euo pipefail
cd "$(dirname "$0")/.."
output="${1:-eval/results/2026-09-11-tuning}"
baseline=$(ssh vllm "docker inspect -f '{{.HostConfig.CpusetCpus}}' qwen38")
all_cpus=$(ssh vllm 'cat /sys/devices/system/cpu/online')
if [[ -n "$baseline" && "$baseline" != "$all_cpus" ]]; then
  echo "This comparison requires an initially unpinned container" >&2
  exit 1
fi
# Docker update omits an empty cpuset instead of clearing the existing pin.
# Explicitly restore every online CPU; recreate later to restore empty metadata.
restore() { ssh vllm "docker update --cpuset-cpus '$all_cpus' qwen38 >/dev/null"; }
trap restore EXIT
for round in 0 1 2; do
  order="unpinned pinned"
  if [[ "$round" == 1 ]]; then order="pinned unpinned"; fi
  for arm in $order; do
    cpus="$all_cpus"
    if [[ "$arm" == pinned ]]; then cpus="0-3,32-35"; fi
    ssh vllm "docker update --cpuset-cpus '$cpus' qwen38 >/dev/null"
    actual=$(ssh vllm "docker inspect -f '{{.HostConfig.CpusetCpus}}' qwen38")
    [[ "$actual" == "$cpus" ]] || { echo "Affinity override did not apply" >&2; exit 1; }
    effective=$(ssh vllm 'docker exec qwen38 cat /sys/fs/cgroup/cpuset.cpus.effective')
    [[ "$effective" == "$cpus" ]] || { echo "Effective affinity differs from Docker setting" >&2; exit 1; }
    printf 'round %s %s applied cpuset=%s effective=%s\n' "$round" "$arm" "$actual" "$effective"
    python3 -u scripts/bench.py --base-url http://100.103.136.98:8000 \
      --corpus-file "$output/corpus.txt" --workload code --warm \
      --prompt-tokens 8192 --gen 768 -n 2 --seed "$((42000 + round * 10))" \
      --prompt-id "cpu-pair-$round" \
      --json "$output/cpu-$round-$arm.json" > "$output/cpu-$round-$arm.log" 2>&1
  done
done
