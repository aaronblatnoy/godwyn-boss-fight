#!/usr/bin/env bash
set -euo pipefail

local_game_dir="/Users/aaron_7nh0yzm/godwyn-boss-fight/game/"
remote_game_dir="godwyn-ci/p0/game"

printf 'Syncing game/ to black-sky:~/%s/\n' "$remote_game_dir"
ssh black-sky "mkdir -p ~/$remote_game_dir"
rsync -a --delete "$local_game_dir" "black-sky:~/$remote_game_dir/"

printf 'Running headless import on black-sky\n'
ssh black-sky "cd ~/$remote_game_dir && ~/bin/godot --headless --path . --import"

printf 'Verifying Vulkan GPUs on black-sky\n'
ssh black-sky "env -u DISPLAY vulkaninfo 2>&1 | grep -i 'GPU'"

printf 'Running main-scene boot smoke on black-sky\n'
if ! boot_output=$(ssh black-sky "cd ~/$remote_game_dir && set +e; output=\$(timeout 30 ~/bin/godot --headless --path . --script res://tests/test_boot.gd 2>&1); status=\$?; set -e; printf '%s\\n' \"\$output\"; if [[ \$status -ne 0 ]]; then exit \"\$status\"; fi; printf '%s\\n' \"\$output\" | grep -Fq 'boot ok'"); then
	printf '%s\n' "$boot_output"
	printf 'FAIL headless_import: main scene did not print boot ok\n' >&2
	exit 1
fi

printf '%s\n' "$boot_output"
printf 'PASS headless_import\n'
