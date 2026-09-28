#!/usr/bin/env bash
set -euo pipefail

ci_label="${1:-p0}"
local_game_dir="/Users/aaron_7nh0yzm/godwyn-boss-fight/game/"

if [[ ! "$ci_label" =~ ^[A-Za-z0-9._-]+$ ]]; then
	printf 'FAIL ci: invalid CI label %q\n' "$ci_label" >&2
	exit 1
fi

remote_game_dir="godwyn-ci/$ci_label/game"

printf 'CI label: %s\n' "$ci_label"
printf 'Syncing game/ to black-sky:~/%s/\n' "$remote_game_dir"
ssh black-sky "mkdir -p ~/$remote_game_dir"
rsync -a --delete --exclude=.DS_Store --exclude='._*' \
	"$local_game_dir" "black-sky:~/$remote_game_dir/"

printf 'Running headless import on black-sky\n'
if ! ssh black-sky "cd ~/$remote_game_dir && ~/bin/godot --headless --path . --import"; then
	printf 'FAIL ci: headless import failed\n' >&2
	exit 1
fi

ssh black-sky "bash -s" -- "$remote_game_dir" <<'REMOTE_TESTS'
set -u

remote_game_dir="$1"
cd "$HOME/$remote_game_dir" || {
	printf 'FAIL ci: cannot enter %s\n' "$HOME/$remote_game_dir"
	exit 1
}

mapfile -d '' test_files < <(find tests -type f -name '*.gd' -not -name '._*' -print0 | sort -z)
failures=()

for test_file in "${test_files[@]}"; do
	printf 'RUN %s\n' "$test_file"
	set +e
	test_output=$(timeout 30 "$HOME/bin/godot" --headless --path . --script "res://$test_file" 2>&1)
	test_status=$?
	set -e
	printf '%s\n' "$test_output"

	if [[ $test_status -eq 124 ]]; then
		failures+=("$test_file (timeout)")
	elif [[ $test_status -ne 0 ]]; then
		failures+=("$test_file (exit $test_status)")
	elif grep -Eq '^FAIL([ :]|$)' <<<"$test_output"; then
		failures+=("$test_file (reported FAIL)")
	fi
done

if (( ${#failures[@]} > 0 )); then
	printf 'TEST FAILURES (%d):\n' "${#failures[@]}"
	printf '  %s\n' "${failures[@]}"
	exit 1
fi

printf 'ALL TESTS PASSED (%d)\n' "${#test_files[@]}"
exit 0
REMOTE_TESTS
