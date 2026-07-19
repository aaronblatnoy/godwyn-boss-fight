#!/usr/bin/env bash
# =============================================================================
# vlm_describe_swarm.sh — concurrent video-describe pool through the gateway
# =============================================================================
# Part of the godwyn-vlm-critic child workflow (Phase 4).
# Fires N describe-tasks CONCURRENTLY at the llm-server GATEWAY :8000
# (OpenAI /v1/chat/completions with video_url base64 data URI + aspect prompt).
# Base64-encodes the video ONCE and reuses across all tasks in the wave.
# Outputs one JSONL line per task; timeout/error -> abstain line (never blocks).
#
# INVARIANT INV-GW: ALL requests go through the GATEWAY (:8000). vLLM (:8001)
# is NEVER called directly from this script.
# INVARIANT INV-6: the video never leaves the box. This script runs ON black-sky.
#
# Usage:
#   vlm_describe_swarm.sh \
#     --tasks    <tasks_file>    # tab-separated: id<TAB>aspect_prompt, one per line
#     --video    <video.mp4>     # full path to the WIP animation mp4
#     --gateway  <URL>           # e.g. http://black-sky:8000  (NO trailing slash)
#     --model    <model_name>    # e.g. Qwen2.5-VL-3B-AWQ (the VL model on vLLM)
#     [--out     <output.jsonl>] # default: stdout
#     [--width   <N>]            # SWARM_WIDTH — max concurrent requests (default 4)
#     [--timeout <secs>]         # per-task timeout in seconds (default 60)
#     [--max-tokens <N>]         # max_tokens per describe call (default 200)
#
# Output: one JSON line per task (in input order), appended to --out or stdout:
#   {"id":"...", "aspect":"...", "description":"...", "abstained":false, "latency_ms":1234}
#   {"id":"...", "aspect":"...", "description":null,  "abstained":true,  "latency_ms":1234}
#
# OQ-2 NOTE ON CONCURRENCY:
#   Video-describe is token-heavy (each frame expands the KV cache significantly).
#   On a single RTX 3060 Ti (8GB VRAM) with Qwen2.5-VL-3B-AWQ, sustained
#   concurrent video-describe throughput is ~2-4 requests before KV pressure
#   causes OOM or severe latency spikes. Default SWARM_WIDTH=4 is conservative.
#   Recommended vLLM launch flag: --max-num-seqs 4 (or 2 for longer clips).
#   To tune: raise --width and watch `nvidia-smi`; drop when VRAM exceeds ~85%.
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
TASKS_FILE=""
VIDEO_PATH=""
GATEWAY_URL=""
MODEL_NAME=""
OUT_FILE=""
SWARM_WIDTH=4
TASK_TIMEOUT=60
MAX_TOKENS=200

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tasks)      TASKS_FILE="$2";   shift 2 ;;
    --video)      VIDEO_PATH="$2";   shift 2 ;;
    --gateway)    GATEWAY_URL="$2";  shift 2 ;;
    --model)      MODEL_NAME="$2";   shift 2 ;;
    --out)        OUT_FILE="$2";     shift 2 ;;
    --width)      SWARM_WIDTH="$2";  shift 2 ;;
    --timeout)    TASK_TIMEOUT="$2"; shift 2 ;;
    --max-tokens) MAX_TOKENS="$2";   shift 2 ;;
    *) echo "ERROR: Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
if [[ -z "$TASKS_FILE" || -z "$VIDEO_PATH" || -z "$GATEWAY_URL" || -z "$MODEL_NAME" ]]; then
  echo "ERROR: --tasks, --video, --gateway, and --model are all required." >&2
  exit 1
fi
if [[ ! -f "$TASKS_FILE" ]]; then
  echo "ERROR: tasks file not found: $TASKS_FILE" >&2; exit 1
fi
if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "ERROR: video file not found: $VIDEO_PATH" >&2; exit 1
fi

# Guard: never target vLLM directly (INV-GW)
if echo "$GATEWAY_URL" | grep -qE ':8001'; then
  echo "ERROR: INV-GW violated — GATEWAY_URL must not target vLLM:8001 directly." >&2
  echo "       Use the gateway URL, e.g. http://black-sky:8000" >&2
  exit 1
fi

ENDPOINT="${GATEWAY_URL%/}/v1/chat/completions"

# ---------------------------------------------------------------------------
# Setup: tmpdir for inter-process communication
# ---------------------------------------------------------------------------
TMPDIR_SWARM="$(mktemp -d /tmp/vlm_swarm_XXXXXX)"
trap 'rm -rf "$TMPDIR_SWARM"' EXIT

if [[ -n "$OUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUT_FILE")"
  touch "$OUT_FILE"
fi

# ---------------------------------------------------------------------------
# Step 1: Base64-encode the video ONCE, write to a shared temp file.
#         Use Python for portability (macOS and Linux).
# ---------------------------------------------------------------------------
echo "[vlm_swarm] Encoding video (once): $VIDEO_PATH" >&2
VIDEO_DATA_URI_FILE="$TMPDIR_SWARM/video_data_uri.txt"

python3 - "$VIDEO_PATH" "$VIDEO_DATA_URI_FILE" << 'PYEOF'
import base64, sys
video_path = sys.argv[1]
out_path   = sys.argv[2]
with open(video_path, 'rb') as f:
    data = f.read()
b64 = base64.b64encode(data).decode('ascii')
uri = "data:video/mp4;base64," + b64
with open(out_path, 'w') as f:
    f.write(uri)
PYEOF

echo "[vlm_swarm] Video encoded ($(wc -c < "$VIDEO_DATA_URI_FILE") URI bytes)" >&2

# ---------------------------------------------------------------------------
# Step 2: Parse tasks file — write each task to a numbered file so
#         subprocesses can read them without array-export limitations.
# ---------------------------------------------------------------------------
TASK_COUNT=0
while IFS=$'\t' read -r task_id aspect_prompt; do
  [[ -z "$task_id" || "$task_id" == \#* ]] && continue
  # Write id and prompt to separate files indexed by task number
  printf '%s' "$task_id"      > "$TMPDIR_SWARM/task_id_${TASK_COUNT}"
  printf '%s' "$aspect_prompt" > "$TMPDIR_SWARM/task_prompt_${TASK_COUNT}"
  TASK_COUNT=$(( TASK_COUNT + 1 ))
done < "$TASKS_FILE"

if [[ "$TASK_COUNT" -eq 0 ]]; then
  echo "[vlm_swarm] WARNING: no tasks found in $TASKS_FILE" >&2
  exit 0
fi

echo "[vlm_swarm] Loaded $TASK_COUNT tasks from $TASKS_FILE" >&2
echo "[vlm_swarm] SWARM_WIDTH=$SWARM_WIDTH  TIMEOUT=${TASK_TIMEOUT}s  MODEL=$MODEL_NAME" >&2
echo "[vlm_swarm] ENDPOINT: $ENDPOINT" >&2

# ---------------------------------------------------------------------------
# Step 3: Worker — one subprocess per task.
#         Reads task_id/prompt from files in TMPDIR_SWARM.
#         Writes a JSONL line to result_<idx>.json.
#         On any error -> writes an abstain line (NEVER exits non-zero).
# ---------------------------------------------------------------------------
run_task() {
  local idx="$1"
  local task_id
  local aspect_prompt
  task_id="$(cat "$TMPDIR_SWARM/task_id_${idx}")"
  aspect_prompt="$(cat "$TMPDIR_SWARM/task_prompt_${idx}")"
  local result_file="$TMPDIR_SWARM/result_${idx}.json"
  local payload_file="$TMPDIR_SWARM/payload_${idx}.json"
  local curl_err_file="$TMPDIR_SWARM/curl_err_${idx}"

  # Millisecond timestamp via Python (portable; date +%s%3N is Linux-only)
  ms_now() { python3 -c "import time; print(int(time.time()*1000))"; }
  local start_ms
  start_ms=$(ms_now)

  # Write abstain helper
  write_abstain() {
    local lat
    lat=$(( $(ms_now) - start_ms ))
    python3 - "$task_id" "$aspect_prompt" "$lat" "$result_file" << 'PYEOF'
import json, sys
print(json.dumps({
    "id": sys.argv[1],
    "aspect": sys.argv[2],
    "description": None,
    "abstained": True,
    "latency_ms": int(sys.argv[3])
}), file=open(sys.argv[4],'w'))
PYEOF
  }

  # Build the JSON payload via Python (handles all special chars safely)
  python3 - "$MODEL_NAME" "$aspect_prompt" "$MAX_TOKENS" \
    "$VIDEO_DATA_URI_FILE" "$payload_file" << 'PYEOF'
import json, sys
model        = sys.argv[1]
aspect       = sys.argv[2]
max_tokens   = int(sys.argv[3])
video_uri    = open(sys.argv[4]).read().strip()
payload_path = sys.argv[5]

payload = {
    "model": model,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "video_url", "video_url": {"url": video_uri}},
            {"type": "text", "text": aspect}
        ]
    }],
    "max_tokens": max_tokens
}
with open(payload_path, 'w') as f:
    json.dump(payload, f)
PYEOF

  if [[ ! -f "$payload_file" ]]; then
    echo "[vlm_swarm] task=$task_id ABSTAIN (payload build failed)" >&2
    write_abstain; return 0
  fi

  # Fire the request
  local http_response=""
  http_response=$(curl -s \
    --max-time "$TASK_TIMEOUT" \
    -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    --data-binary "@$payload_file" \
    2>"$curl_err_file") || true

  local end_ms lat_ms
  end_ms=$(ms_now)
  lat_ms=$(( end_ms - start_ms ))

  if [[ -z "$http_response" ]]; then
    local curl_err_msg
    curl_err_msg=$(head -1 "$curl_err_file" 2>/dev/null || true)
    echo "[vlm_swarm] task=$task_id ABSTAIN (curl error: $curl_err_msg)" >&2
    write_abstain; return 0
  fi

  # Parse the OpenAI-compatible response
  local description
  description=$(python3 - "$http_response" << 'PYEOF' 2>/dev/null || true
import json, sys
try:
    r = json.loads(sys.argv[1])
    choices = r.get("choices", [])
    if not choices:
        sys.exit(1)
    content = choices[0].get("message", {}).get("content", "")
    if not content or not content.strip():
        sys.exit(2)
    print(content.strip())
except Exception:
    sys.exit(3)
PYEOF
  )

  if [[ -z "$description" ]]; then
    local resp_snip
    resp_snip=$(echo "$http_response" | head -c 200)
    echo "[vlm_swarm] task=$task_id ABSTAIN (empty/parse error; resp: $resp_snip)" >&2
    write_abstain; return 0
  fi

  echo "[vlm_swarm] task=$task_id OK (${lat_ms}ms)" >&2

  # Write the success result line
  python3 - "$task_id" "$aspect_prompt" "$description" "$lat_ms" "$result_file" << 'PYEOF'
import json, sys
print(json.dumps({
    "id": sys.argv[1],
    "aspect": sys.argv[2],
    "description": sys.argv[3],
    "abstained": False,
    "latency_ms": int(sys.argv[4])
}), file=open(sys.argv[5], 'w'))
PYEOF

  # Cleanup per-task temps
  rm -f "$payload_file" "$curl_err_file"
}

export -f run_task
export TMPDIR_SWARM MODEL_NAME MAX_TOKENS VIDEO_DATA_URI_FILE ENDPOINT TASK_TIMEOUT

# ---------------------------------------------------------------------------
# Step 4: Semaphore-based concurrent dispatch (SWARM_WIDTH at a time)
# ---------------------------------------------------------------------------
echo "[vlm_swarm] Dispatching $TASK_COUNT tasks (width=$SWARM_WIDTH) ..." >&2

declare -a PIDS=()

for (( i=0; i<TASK_COUNT; i++ )); do
  # Throttle: wait until active count drops below SWARM_WIDTH
  while [[ "${#PIDS[@]}" -ge "$SWARM_WIDTH" ]]; do
    new_pids=()
    found_done=0
    for p in "${PIDS[@]}"; do
      if ! kill -0 "$p" 2>/dev/null; then
        wait "$p" 2>/dev/null || true
        found_done=1
      else
        new_pids+=("$p")
      fi
    done
    PIDS=("${new_pids[@]+"${new_pids[@]}"}")
    [[ "$found_done" -eq 0 ]] && sleep 0.05
  done

  # Spawn worker in a subshell (inherits exports)
  ( run_task "$i" ) &
  PIDS+=($!)
done

# Drain remaining workers
for p in "${PIDS[@]+"${PIDS[@]}"}"; do
  wait "$p" 2>/dev/null || true
done

echo "[vlm_swarm] All workers complete. Collecting results in order ..." >&2

# ---------------------------------------------------------------------------
# Step 5: Collect results IN INPUT ORDER and write to output
# ---------------------------------------------------------------------------
ABSTAIN_COUNT=0
OK_COUNT=0

for (( i=0; i<TASK_COUNT; i++ )); do
  result_file="$TMPDIR_SWARM/result_${i}.json"

  if [[ -f "$result_file" ]]; then
    line=$(cat "$result_file")
    if [[ -n "$OUT_FILE" ]]; then
      echo "$line" >> "$OUT_FILE"
    else
      echo "$line"
    fi
    if python3 -c "import sys,json; d=json.load(open('$result_file')); exit(0 if d.get('abstained') else 1)" 2>/dev/null; then
      ABSTAIN_COUNT=$(( ABSTAIN_COUNT + 1 ))
    else
      OK_COUNT=$(( OK_COUNT + 1 ))
    fi
  else
    # Worker crashed before writing the result file — emit a safe abstain
    local_id="$(cat "$TMPDIR_SWARM/task_id_${i}" 2>/dev/null || echo "unknown_${i}")"
    local_aspect="$(cat "$TMPDIR_SWARM/task_prompt_${i}" 2>/dev/null || echo "")"
    fallback=$(python3 - "$local_id" "$local_aspect" << 'PYEOF'
import json, sys
print(json.dumps({
    "id": sys.argv[1],
    "aspect": sys.argv[2],
    "description": None,
    "abstained": True,
    "latency_ms": 0
}))
PYEOF
    )
    if [[ -n "$OUT_FILE" ]]; then
      echo "$fallback" >> "$OUT_FILE"
    else
      echo "$fallback"
    fi
    ABSTAIN_COUNT=$(( ABSTAIN_COUNT + 1 ))
    echo "[vlm_swarm] task=$local_id ABSTAIN (worker crash, no result file)" >&2
  fi
done

echo "[vlm_swarm] Done. OK=$OK_COUNT  ABSTAIN=$ABSTAIN_COUNT  TOTAL=$TASK_COUNT" >&2
[[ -n "$OUT_FILE" ]] && echo "[vlm_swarm] Output: $OUT_FILE" >&2

exit 0
