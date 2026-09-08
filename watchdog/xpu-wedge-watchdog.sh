#!/usr/bin/env bash
#
# xpu-wedge-watchdog.sh - detect and recover from Intel Arc GPU (Xe2 / Battlemage)
# Level-Zero wedge during sustained LLM inference.
#
# Problem:
#   Under sustained multi-GPU Level-Zero inference load, the xe kernel driver can
#   reset a compute/copy engine (ccs/bcs) and return "Fault response: Unsuccessful
#   -ENOENT/-EINVAL". After the reset the userspace Level-Zero context stays wedged
#   permanently: the serving engine hangs (vLLM: TimeoutError -> EngineDeadError)
#   until the container is restarted. Corroborating reports:
#     - intel/compute-runtime#948 (dual Arc Pro B70, vLLM TP=2)
#     - vllm-project/vllm#41663 (same hardware, GP fault + bcs engine reset)
#     - darktable#20257 (same ccs engine-reset signature via OpenCL, no vLLM)
#
# What this watchdog does:
#   1. Polls a health endpoint (OpenAI-compatible /health by default).
#   2. Watches kernel logs for engine-reset / fault-response signatures.
#   3. When health is down AND a wedge signature appeared since the last good
#      check -> run the recovery command (default: docker restart) and verify.
#   4. Emits every event as one parseable line with an ISO-8601 timestamp.
#
# Usage:
#   ./xpu-wedge-watchdog.sh               # single pass
#   ./xpu-wedge-watchdog.sh --loop        # keep scanning (used by systemd)
#   ./xpu-wedge-watchdog.sh --self-test   # offline detection test, no docker
#
# Configuration (env vars, all optional):
#   HEALTH_URL        health endpoint                 (default http://127.0.0.1:8000/health)
#   HEALTH_OK_CODES   space-separated ok status codes (default "200" "0"=unreachable-forbidden? see code)
#   CONTAINER         container name for default recovery (default vllm-serve)
#   RECOVERY_CMD      full recovery command           (default "docker restart $CONTAINER")
#   SCAN_INTERVAL_S   seconds between scans in --loop (default 10)
#   HEALTH_TIMEOUT_S  curl timeout per check           (default 5)
#   FAIL_STREAK       failed checks before acting      (default 3)
#   RECOVERY_TIMEOUT_S max seconds to wait for health  (default 600)
#   MAX_RECOVERY_ATTEMPTS restarts allowed per incident (default 2)
#   TRIGGER_MODE      both|kernel|health              (default both)
#   KMSG_SOURCE       auto|journal|dmesg|file:/path    (default auto)
#   STATE_FILE        persisted kernel snapshot        (default /tmp/...)
#   DIAGNOSTICS_DIR   pre-restart evidence directory   (default /tmp/...)
#   WEBHOOK_URL       optional notification endpoint   (default empty)
#
# Exit codes: 0 ok/recovered, 2 no usable kernel-log source, 3 recovery failed.

set -u

# ---- Config with defaults -------------------------------------------------
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
HEALTH_OK_CODES="${HEALTH_OK_CODES:-200}"
CONTAINER="${CONTAINER:-vllm-serve}"
RECOVERY_CMD="${RECOVERY_CMD:-docker restart "$CONTAINER"}"
SCAN_INTERVAL_S="${SCAN_INTERVAL_S:-10}"
HEALTH_TIMEOUT_S="${HEALTH_TIMEOUT_S:-5}"
FAIL_STREAK="${FAIL_STREAK:-3}"
RECOVERY_TIMEOUT_S="${RECOVERY_TIMEOUT_S:-600}"
MAX_RECOVERY_ATTEMPTS="${MAX_RECOVERY_ATTEMPTS:-2}"
TRIGGER_MODE="${TRIGGER_MODE:-both}"          # both | kernel | health
KMSG_SOURCE="${KMSG_SOURCE:-auto}"            # auto | journal | dmesg | file:/path
STATE_FILE="${STATE_FILE:-/tmp/xpu-wedge-watchdog.state}"
FAULT_FILE="${FAULT_FILE:-${STATE_FILE}.fault}"
STREAK_FILE="${STREAK_FILE:-${STATE_FILE}.streak}"
ATTEMPTS_FILE="${ATTEMPTS_FILE:-${STATE_FILE}.attempts}"
DIAGNOSTICS_DIR="${DIAGNOSTICS_DIR:-/tmp/xpu-wedge-watchdog-diagnostics}"
WEBHOOK_URL="${WEBHOOK_URL:-}"

# Kernel signatures that correlate with the L0 wedge (see issues above).
# grep treats each line as an independent pattern. A leading `|` would create an
# empty alternative and match every kernel line, so each line starts with text.
SIGNATURES='Engine reset: engine_class=(ccs|bcs)
Fault response: Unsuccessful
trying reset from guc_exec_queue_timedout_job
TLB invalidation fence timeout
Completion-Wait loop timed out'

SNAPSHOT_TAIL=500
SELF="$(readlink -f "$0")"

# ---- State -----------------------------------------------------------------
STREAK=0                 # consecutive failed health checks
RECOVERY_ATTEMPTS=0      # restarts attempted during the current incident

# ---- Logging ----------------------------------------------------------------
stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log()  { printf '[%s] %s\n' "$(stamp)" "$*"; }

notify() {
  [ -n "$WEBHOOK_URL" ] || return 0
  curl -sS -o /dev/null -w "" --max-time 5 \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$(printf '%s' "$*" | sed 's/"/\\"/g')\"}" "$WEBHOOK_URL" \
    >/dev/null 2>&1 || true
}

read_counter() {
  local file="$1" value=0
  [ -r "$file" ] && value="$(cat "$file" 2>/dev/null || true)"
  case "$value" in
    ''|*[!0-9]*) value=0 ;;
  esac
  printf '%s\n' "$value"
}

save_incident_state() {
  printf '%s\n' "$STREAK" > "$STREAK_FILE"
  printf '%s\n' "$RECOVERY_ATTEMPTS" > "$ATTEMPTS_FILE"
}

reset_incident() {
  STREAK=0
  RECOVERY_ATTEMPTS=0
  save_incident_state
  rm -f "$FAULT_FILE"
}

# ---- Health check ------------------------------------------------------------
is_healthy() {
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time "$HEALTH_TIMEOUT_S" "$HEALTH_URL" 2>/dev/null) || code=000
  for c in $HEALTH_OK_CODES; do
    [ "$code" = "$c" ] && return 0
  done
  return 1
}

# ---- Kernel log snapshot ------------------------------------------------------
# Returns the current kernel-log snapshot (tail) on stdout.
kernel_snapshot() {
  local src="$KMSG_SOURCE" file
  case "$src" in
    auto)
      if command -v journalctl >/dev/null 2>&1 && journalctl -k -n 1 >/dev/null 2>&1; then
        journalctl -k -n "$SNAPSHOT_TAIL" -o short-monotonic 2>/dev/null | tail -n "$SNAPSHOT_TAIL"
      elif command -v dmesg >/dev/null 2>&1; then
        dmesg 2>/dev/null | tail -n "$SNAPSHOT_TAIL"
      fi
      ;;
    journal) journalctl -k -n "$SNAPSHOT_TAIL" -o short-monotonic 2>/dev/null | tail -n "$SNAPSHOT_TAIL" ;;
    dmesg)   dmesg 2>/dev/null | tail -n "$SNAPSHOT_TAIL" ;;
    file:*)  file="${src#file:}"; [ -r "$file" ] && tail -n "$SNAPSHOT_TAIL" "$file" ;;
  esac
}

# Diff-style: lines in CURRENT that were not in PREV (content-based, order kept).
# An empty PREV means no baseline yet - every line is "new" w.r.t. nothing.
new_kernel_lines() {
  local cur="$1" prev="$2" line
  [ -n "$prev" ] || { printf '%s\n' "$cur"; return 0; }
  printf '%s\n' "$cur" | while IFS= read -r line; do
    case "$prev" in
      *"$line"*) : ;;
      *) printf '%s\n' "$line" ;;
    esac
  done
}

# ---- Recovery ----------------------------------------------------------------
capture_diagnostics() {
  local stamp_id out
  stamp_id="$(date -u +'%Y%m%dT%H%M%SZ')"
  mkdir -p "$DIAGNOSTICS_DIR"
  out="$DIAGNOSTICS_DIR/${stamp_id}.log"
  {
    printf 'captured_at=%s\n' "$(stamp)"
    printf 'container=%s\n' "$CONTAINER"
    printf 'health_url=%s\n' "$HEALTH_URL"
    printf 'trigger=%s\n' "$(cat "$FAULT_FILE" 2>/dev/null || printf 'health-only')"
    printf '\n== kernel snapshot ==\n'
    kernel_snapshot
    if command -v xpu-smi >/dev/null 2>&1; then
      printf '\n== xpu-smi ==\n'
      timeout 15 xpu-smi stats -d 0 2>&1 || true
    fi
    if command -v docker >/dev/null 2>&1; then
      printf '\n== container state ==\n'
      timeout 15 docker inspect "$CONTAINER" \
        --format 'status={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} started={{.State.StartedAt}} restarts={{.RestartCount}}' \
        2>&1 || true
      printf '\n== container logs ==\n'
      timeout 15 docker logs --tail 300 "$CONTAINER" 2>&1 || true
    fi
  } > "$out" 2>&1
  log "DIAGNOSTICS saved=${out}"
}

recover() {
  if [ "$RECOVERY_ATTEMPTS" -ge "$MAX_RECOVERY_ATTEMPTS" ]; then
    log "RECOVERY_SUPPRESSED attempts=${RECOVERY_ATTEMPTS} max=${MAX_RECOVERY_ATTEMPTS} - manual check required"
    return 0
  fi
  RECOVERY_ATTEMPTS=$((RECOVERY_ATTEMPTS + 1))
  save_incident_state
  capture_diagnostics
  log "RECOVERY run attempt=${RECOVERY_ATTEMPTS}/${MAX_RECOVERY_ATTEMPTS} cmd='$RECOVERY_CMD'"
  notify "Xe2 watchdog: wedge detected, restarting ${CONTAINER} (${HEALTH_URL})"
  timeout 60 bash -c "$RECOVERY_CMD" >/dev/null 2>&1 || log "RECOVERY_COMMAND_FAILED (health verification follows)"
  local waited=0
  while [ "$waited" -lt "$RECOVERY_TIMEOUT_S" ]; do
    if is_healthy; then
      log "RECOVERED container=${CONTAINER} after=${waited}s"
      notify "Xe2 watchdog: ${CONTAINER} recovered after ${waited}s"
      reset_incident
      return 0
    fi
    sleep 5
    waited=$((waited + 5))
  done
  log "RECOVERY_FAILED container=${CONTAINER} waited=${RECOVERY_TIMEOUT_S}s"
  notify "Xe2 watchdog: RECOVERY FAILED for ${CONTAINER} after ${RECOVERY_TIMEOUT_S}s - manual intervention"
  return 3
}

# ---- One scan pass -------------------------------------------------------------
run_once() {
  local cur new sigs state prev pending

  mkdir -p "$(dirname "$STATE_FILE")"
  STREAK="$(read_counter "$STREAK_FILE")"
  RECOVERY_ATTEMPTS="$(read_counter "$ATTEMPTS_FILE")"

  cur="$(kernel_snapshot)" || true
  # An empty snapshot is valid for file: sources (log not yet written) but
  # signals an unavailable source for journal/dmesg.
  if [ -z "$cur" ] && [ "${KMSG_SOURCE#file:}" = "$KMSG_SOURCE" ]; then
    log "KMSG_UNAVAILABLE source=${KMSG_SOURCE} (need root or adm/systemd-journal; set KMSG_SOURCE=dmesg or file:/path)"
    return 2
  fi

  # Kernel snapshot state is persisted across invocations, so one-shot runs
  # (systemd timer / cron) build on the previous run's baseline correctly.
  state="$STATE_FILE"
  if [ ! -f "$state" ]; then
    printf '%s\n' "$cur" > "$state"
    log "BOOTSTRAP state=${state} snapshot_seeded lines=$(printf '%s\n' "$cur" | wc -l)"
    return 0
  fi
  prev="$(cat "$state" 2>/dev/null || true)"
  new="$(new_kernel_lines "$cur" "$prev")"
  printf '%s\n' "$cur" > "$state"
  sigs="$(printf '%s\n' "$new" | grep -Ei "$SIGNATURES" || true)"
  if [ -n "$sigs" ]; then
    printf '%s\n' "$(printf '%s\n' "$sigs" | head -n1)" > "$FAULT_FILE"
  fi

  if is_healthy; then
    if [ "$STREAK" -ne 0 ] || [ "$RECOVERY_ATTEMPTS" -ne 0 ] || [ -e "$FAULT_FILE" ]; then
      [ "$STREAK" -ne 0 ] && log "HEALTH_OK restored"
      reset_incident
    fi
    return 0
  fi

  STREAK=$((STREAK + 1))
  save_incident_state
  log "HEALTH_DOWN streak=${STREAK} new_kernel_lines=$(printf '%s\n' "$new" | wc -l | tr -d ' ')"

  [ "$STREAK" -ge "$FAIL_STREAK" ] || return 0

  if [ "$TRIGGER_MODE" = "health" ]; then
    log "WEDGE trigger=health streak=${STREAK} (TRIGGER_MODE=health)"
    recover; return $?
  fi

  pending="$(cat "$FAULT_FILE" 2>/dev/null || true)"
  if [ -n "$pending" ]; then
    log "WEDGE trigger=kernel streak=${STREAK} first_match=${pending}"
    recover; return $?
  fi

  if [ "$TRIGGER_MODE" = "kernel" ]; then
    log "DEGRADED no_kernel_signature - manual check required"
    notify "Xe2 watchdog: ${CONTAINER} unhealthy (${HEALTH_URL}, streak ${STREAK}) but NO GPU engine-reset signature - not restarting, please check"
    return 0
  fi

  log "DEGRADED no_kernel_signature - waiting for signature or recovery"
  return 0
}

# ---- Offline self-test -----------------------------------------------------------
self_test() {
  local tmp kmsg rc=0 sport recovery_script
  tmp="$(mktemp -d)"
  kmsg="$tmp/kmsg.log"; : > "$kmsg"

  # Healthy-path server: any 200 works (directory listing is fine).
  sport=$(( 21000 + RANDOM % 1000 ))
  if command -v python3 >/dev/null 2>&1; then
    ( cd "$tmp" && exec python3 -m http.server "$sport" >/dev/null 2>&1 ) &
  elif command -v nc >/dev/null 2>&1; then
    ( while :; do printf 'HTTP/1.1 200 OK\r\n\r\nok' | nc -l "$sport" >/dev/null 2>&1 || break; done ) &
  else
    log "SELFTEST SKIP: need python3 or nc"; rm -rf "$tmp"; return 1
  fi
  sleep 1

  # 1) Healthy path: bootstrap pass, then pass 2 must be a silent no-op.
  HEALTH_URL="http://127.0.0.1:${sport}/" KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-ok" \
    RECOVERY_CMD="echo would-restart" "$SELF" > "$tmp/out-1.log" 2>&1
  HEALTH_URL="http://127.0.0.1:${sport}/" KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-ok" \
    RECOVERY_CMD="echo would-restart" "$SELF" > "$tmp/out-2.log" 2>&1
  if grep -q "BOOTSTRAP" "$tmp/out-1.log" \
     && ! grep -qE "WEDGE|DEGRADED|RECOVERY|HEALTH_DOWN" "$tmp/out-2.log"; then
    log "SELFTEST ok: healthy path no-op"
  else
    log "SELFTEST FAIL: healthy path (out-2 below)"; sed -n '1,20p' "$tmp/out-2.log"; rc=1
  fi
  pkill -f "http.server $sport" 2>/dev/null || true
  sleep 0.3

  # 2) Unrelated kernel lines must not satisfy the GPU signature check, even
  # after the health failure threshold is reached.
  : > "$kmsg"
  for i in 1 2 3 4; do
    [ "$i" -eq 2 ] && printf '%s\n' 'veth88b9e4a: renamed from eth0' >> "$kmsg"
    HEALTH_URL="http://127.0.0.1:1/health" HEALTH_TIMEOUT_S=1 FAIL_STREAK=3 \
      KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-unrelated" \
      DIAGNOSTICS_DIR="$tmp/diag-unrelated" RECOVERY_CMD="touch $tmp/should-not-exist" \
      "$SELF" >> "$tmp/unrelated.log" 2>&1
  done
  if [ ! -e "$tmp/should-not-exist" ] && ! grep -q 'WEDGE trigger=kernel' "$tmp/unrelated.log"; then
    log "SELFTEST ok: unrelated kernel line cannot trigger recovery"
  else
    log "SELFTEST FAIL: unrelated kernel line triggered recovery"
    sed -n '1,30p' "$tmp/unrelated.log"; rc=1
  fi

  # 3) A one-time GPU fault must remain pending until the third failed health
  # check, then trigger exactly one recovery and save diagnostics.
  sport=$(( 22000 + RANDOM % 1000 ))
  recovery_script="$tmp/recover.sh"
  printf '%s\n' '#!/usr/bin/env bash' \
    "touch '$tmp/recovered'" \
    "cd '$tmp'" \
    "python3 -m http.server '$sport' >'$tmp/recovery-http.log' 2>&1 &" \
    > "$recovery_script"
  chmod +x "$recovery_script"
  : > "$kmsg"
  HEALTH_URL="http://127.0.0.1:${sport}/" KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-wedge" \
    "$SELF" > "$tmp/wedge.log" 2>&1
  printf '%s\n' \
    'xe 0000:c7:00.0: [drm] Tile0: GT0: Fault response: Unsuccessful -ENOENT' >> "$kmsg"
  for i in 1 2 3; do
    HEALTH_URL="http://127.0.0.1:${sport}/" HEALTH_TIMEOUT_S=1 FAIL_STREAK=3 \
      RECOVERY_TIMEOUT_S=10 KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-wedge" \
      DIAGNOSTICS_DIR="$tmp/diag-wedge" RECOVERY_CMD="$recovery_script" \
      "$SELF" >> "$tmp/wedge.log" 2>&1
  done
  if [ -e "$tmp/recovered" ] \
     && [ "$(grep -c 'RECOVERY run' "$tmp/wedge.log")" -eq 1 ] \
     && [ "$(find "$tmp/diag-wedge" -type f 2>/dev/null | wc -l | tr -d ' ')" -eq 1 ]; then
    log "SELFTEST ok: pending GPU fault triggers one recovery at threshold"
  else
    log "SELFTEST FAIL: pending GPU fault recovery path"
    sed -n '1,50p' "$tmp/wedge.log"; rc=1
  fi
  pkill -f "http.server $sport" 2>/dev/null || true

  # 4) A failed recovery must stop at the configured attempt limit instead of
  # restarting forever and repeatedly interrupting model initialization.
  : > "$kmsg"
  HEALTH_URL="http://127.0.0.1:1/health" KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-limit" \
    "$SELF" > "$tmp/limit.log" 2>&1
  printf '%s\n' \
    'xe 0000:c7:00.0: [drm] Tile0: GT0: Engine reset: engine_class=ccs, logical_mask: 0x1' >> "$kmsg"
  for i in 1 2 3 4; do
    HEALTH_URL="http://127.0.0.1:1/health" HEALTH_TIMEOUT_S=1 FAIL_STREAK=3 \
      RECOVERY_TIMEOUT_S=1 MAX_RECOVERY_ATTEMPTS=1 KMSG_SOURCE="file:$kmsg" \
      STATE_FILE="$tmp/state-limit" DIAGNOSTICS_DIR="$tmp/diag-limit" \
      RECOVERY_CMD="touch $tmp/limited-attempt" \
      "$SELF" >> "$tmp/limit.log" 2>&1
  done
  if [ "$(grep -c 'RECOVERY run' "$tmp/limit.log")" -eq 1 ] \
     && grep -q 'RECOVERY_SUPPRESSED attempts=1 max=1' "$tmp/limit.log"; then
    log "SELFTEST ok: recovery attempts stop at the configured limit"
  else
    log "SELFTEST FAIL: recovery attempt limit"
    sed -n '1,60p' "$tmp/limit.log"; rc=1
  fi

  # The same limit must apply if an operator selects health-only recovery.
  HEALTH_URL="http://127.0.0.1:1/health" TRIGGER_MODE=health MAX_RECOVERY_ATTEMPTS=1 \
    KMSG_SOURCE="file:$kmsg" STATE_FILE="$tmp/state-limit" \
    RECOVERY_CMD="touch $tmp/health-should-not-restart" \
    "$SELF" > "$tmp/health-limit.log" 2>&1
  if [ ! -e "$tmp/health-should-not-restart" ] \
     && grep -q 'RECOVERY_SUPPRESSED' "$tmp/health-limit.log"; then
    log "SELFTEST ok: health-only mode honors the recovery limit"
  else
    log "SELFTEST FAIL: health-only mode ignored recovery limit"; rc=1
  fi

  rm -rf "$tmp"
  return $rc
}

# ---- Entrypoint ---------------------------------------------------------------
main() {
  case "${1:-}" in
    --loop)
      log "START mode=loop health=${HEALTH_URL} container=${CONTAINER} trigger=${TRIGGER_MODE} interval=${SCAN_INTERVAL_S}s"
      notify "Xe2 watchdog: ${CONTAINER} monitoring started (${HEALTH_URL})"
      while :; do
        run_once || { [ $? -eq 2 ] && { log "NO_KMSG_SOURCE - exiting"; return 2; }; }
        sleep "$SCAN_INTERVAL_S"
      done
      ;;
    --self-test)
      self_test
      ;;
    "")
      run_once
      ;;
    *)
      echo "usage: $0 [--loop|--self-test]" >&2
      return 2
      ;;
  esac
}

main "$@"
