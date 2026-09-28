#!/usr/bin/env bash
# Usage: bash scripts/godot/run_native.sh
#        bash scripts/godot/run_native.sh <label> [quit-after-frames]
# Syncs game/ and boots main.tscn headlessly on black-sky. The complete output
# is also saved under ~/godwyn-ci/<label>/logs/ for manual debugging.
# Set GODWYN_PROFILE_FRAMES to a positive integer to opt into a bounded
# Performance-monitor sample at the end of the same run.
set -euo pipefail

run_label="${1:-p10-native}"
quit_after_frames="${2:-600}"
profile_frames="${GODWYN_PROFILE_FRAMES:-}"
profile_frames_arg="${profile_frames:-0}"
local_game_dir="/Users/aaron_7nh0yzm/godwyn-boss-fight/game/"

if [[ ! "$run_label" =~ ^[A-Za-z0-9._-]+$ ]]; then
	printf 'FAIL native run: invalid label %q\n' "$run_label" >&2
	exit 1
fi
if [[ ! "$quit_after_frames" =~ ^[1-9][0-9]*$ ]]; then
	printf 'FAIL native run: quit-after-frames must be a positive integer\n' >&2
	exit 1
fi
if [[ -n "$profile_frames" ]]; then
	if [[ ! "$profile_frames" =~ ^[1-9][0-9]*$ ]]; then
		printf 'FAIL native run: GODWYN_PROFILE_FRAMES must be a positive integer\n' >&2
		exit 1
	fi
	if (( profile_frames > quit_after_frames )); then
		printf 'FAIL native run: GODWYN_PROFILE_FRAMES cannot exceed quit-after-frames\n' >&2
		exit 1
	fi
fi

remote_run_dir="godwyn-ci/$run_label"
remote_game_dir="$remote_run_dir/game"

printf 'Native-run label: %s\n' "$run_label"
printf 'Syncing game/ to black-sky:~/%s/\n' "$remote_game_dir"
ssh black-sky "mkdir -p ~/$remote_game_dir ~/$remote_run_dir/logs"
rsync -a --delete --exclude=.DS_Store --exclude='._*' \
	"$local_game_dir" "black-sky:~/$remote_game_dir/"

printf 'Booting main.tscn headlessly on black-sky for %s frames\n' "$quit_after_frames"
ssh black-sky "bash -s" -- "$remote_run_dir" "$quit_after_frames" "$profile_frames_arg" <<'REMOTE_RUN'
set -euo pipefail

remote_run_dir="$1"
quit_after_frames="$2"
profile_frames="$3"
remote_game_dir="$HOME/$remote_run_dir/game"
log_dir="$HOME/$remote_run_dir/logs"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="$log_dir/native-$timestamp.log"

mkdir -p "$log_dir"
cd "$remote_game_dir"
printf 'Log: %s\n' "$log_file"
# Headless-import the project first so global class_name types (GameManager,
# BossBase, etc.) resolve when this label directory has never been imported
# before -- without this, scripts referencing those types fail to parse.
"$HOME/bin/godot" --headless --path . --import >/dev/null 2>&1 || true
if [[ "$profile_frames" == "0" ]]; then
	"$HOME/bin/godot" --headless --path . --quit-after "$quit_after_frames" 2>&1 | tee "$log_file"
	exit 0
fi

profile_script="$remote_game_dir/.phase10_profile_runner.gd"
trap 'rm -f "$profile_script"' EXIT
cat > "$profile_script" <<'GDSCRIPT'
extends SceneTree


var _process_min := INF
var _process_max := 0.0
var _process_total := 0.0
var _physics_min := INF
var _physics_max := 0.0
var _physics_total := 0.0
var _fps_min := INF
var _fps_max := 0.0
var _fps_total := 0.0


func _initialize() -> void:
	call_deferred("_run_profile")


func _run_profile() -> void:
	var total_frames := int(OS.get_environment("GODWYN_QUIT_AFTER_FRAMES"))
	var sample_frames := int(OS.get_environment("GODWYN_PROFILE_FRAMES"))
	var warmup_frames := total_frames - sample_frames
	var packed_scene := load("res://scenes/main.tscn") as PackedScene
	if packed_scene == null:
		printerr("PHASE10_PROFILE_FAIL main.tscn did not load")
		quit(1)
		return
	var instance := packed_scene.instantiate()
	if instance == null:
		printerr("PHASE10_PROFILE_FAIL main.tscn did not instantiate")
		quit(1)
		return
	root.add_child(instance)

	for _frame: int in warmup_frames:
		await process_frame
	for _frame: int in sample_frames:
		await process_frame
		_record_sample()

	print("PHASE10_PROFILE device=%s vendor=%s headless=true warmup_frames=%d sample_frames=%d" % [
		RenderingServer.get_video_adapter_name(),
		RenderingServer.get_video_adapter_vendor(),
		warmup_frames,
		sample_frames,
	])
	print("PHASE10_PROFILE process_ms min=%.6f avg=%.6f max=%.6f" % [
		_process_min * 1000.0,
		(_process_total / sample_frames) * 1000.0,
		_process_max * 1000.0,
	])
	print("PHASE10_PROFILE physics_ms min=%.6f avg=%.6f max=%.6f" % [
		_physics_min * 1000.0,
		(_physics_total / sample_frames) * 1000.0,
		_physics_max * 1000.0,
	])
	print("PHASE10_PROFILE fps min=%.3f avg=%.3f max=%.3f" % [
		_fps_min,
		_fps_total / sample_frames,
		_fps_max,
	])
	quit(0)


func _record_sample() -> void:
	var process_time := Performance.get_monitor(Performance.TIME_PROCESS)
	var physics_time := Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)
	var fps := Performance.get_monitor(Performance.TIME_FPS)
	_process_min = minf(_process_min, process_time)
	_process_max = maxf(_process_max, process_time)
	_process_total += process_time
	_physics_min = minf(_physics_min, physics_time)
	_physics_max = maxf(_physics_max, physics_time)
	_physics_total += physics_time
	_fps_min = minf(_fps_min, fps)
	_fps_max = maxf(_fps_max, fps)
	_fps_total += fps
GDSCRIPT

printf 'Profiling final %s of %s headless frames via Godot Performance monitors\n' "$profile_frames" "$quit_after_frames"
GODWYN_QUIT_AFTER_FRAMES="$quit_after_frames" GODWYN_PROFILE_FRAMES="$profile_frames" \
	"$HOME/bin/godot" --headless --path . --script "$profile_script" 2>&1 | tee "$log_file"
REMOTE_RUN
