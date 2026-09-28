#!/usr/bin/env bash
set -euo pipefail

# Run this script on black-sky via SSH. It never invokes Godot, Vulkan tools,
# the package manager, or downloads on the caller's machine.

godot_bin="$HOME/bin/godot"
expected_version="4.7.2"
template_tag="4.7.2.stable"
template_dir="$HOME/.local/share/godot/export_templates/$template_tag"
template_url="https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_export_templates.tpz"

fail() {
	printf 'FAIL %s\n' "$1" >&2
	exit 1
}

if [[ ! -x "$godot_bin" ]]; then
	fail "Godot binary is not executable at $godot_bin"
fi
if ! version_output=$("$godot_bin" --headless --version 2>&1); then
	printf '%s\n' "$version_output" >&2
	fail "Godot binary version check"
fi
if [[ ! "$version_output" =~ ^4\.[0-9]+ ]] || [[ "$version_output" != "$expected_version"* ]]; then
	fail "expected Godot $expected_version, got $version_output"
fi
printf 'PASS Godot binary version: %s\n' "$version_output"

if ! command -v vulkaninfo >/dev/null 2>&1; then
	printf 'Installing vulkan-tools on black-sky\n'
	if ! sudo pacman -S --needed --noconfirm vulkan-tools; then
		fail "vulkan-tools installation"
	fi
fi
if ! vulkaninfo_output=$(env -u DISPLAY vulkaninfo 2>&1); then
	printf '%s\n' "$vulkaninfo_output" >&2
	fail "vulkaninfo execution"
fi
gpu_lines=$(printf '%s\n' "$vulkaninfo_output" | grep -i 'GPU' || true)
if [[ -z "$gpu_lines" ]]; then
	fail "vulkaninfo did not report any GPU line"
fi
rtx_3060_ti_lines=$(printf '%s\n' "$gpu_lines" | grep -Fic 'NVIDIA GeForce RTX 3060 Ti' || true)
if (( rtx_3060_ti_lines < 2 )); then
	printf '%s\n' "$gpu_lines" >&2
	fail "vulkaninfo did not report both NVIDIA GeForce RTX 3060 Ti GPUs"
fi
printf 'PASS Vulkan GPU lines:\n'
printf '%s\n' "$gpu_lines"

templates_ready=false
if [[ -s "$template_dir/linux_debug.x86_64" \
	&& -s "$template_dir/linux_release.x86_64" \
	&& -f "$template_dir/version.txt" ]] \
	&& grep -Fxq "$template_tag" "$template_dir/version.txt"; then
	templates_ready=true
fi

if [[ "$templates_ready" != true ]]; then
	if ! command -v curl >/dev/null 2>&1; then
		fail "curl is required to download Godot export templates"
	fi
	if ! command -v unzip >/dev/null 2>&1; then
		printf 'Installing unzip on black-sky\n'
		if ! sudo pacman -S --needed --noconfirm unzip; then
			fail "unzip installation"
		fi
	fi

	staging_dir=$(mktemp -d)
	trap 'rm -rf -- "$staging_dir"' EXIT
	template_archive="$staging_dir/export_templates.tpz"
	printf 'Downloading Godot %s export templates\n' "$expected_version"
	if ! curl -fL --connect-timeout 30 --max-time 900 --retry 2 -o "$template_archive" "$template_url"; then
		fail "Godot export-template download"
	fi
	if ! unzip -q "$template_archive" -d "$staging_dir/unpacked"; then
		fail "Godot export-template extraction"
	fi
	staged_templates="$staging_dir/unpacked/templates"
	if [[ ! -s "$staged_templates/linux_debug.x86_64" || ! -s "$staged_templates/linux_release.x86_64" ]]; then
		fail "downloaded archive lacks matching Linux debug/release templates"
	fi
	rm -rf -- "$template_dir"
	mkdir -p "$template_dir"
	cp -a "$staged_templates/." "$template_dir/"
fi

template_file_count=$(find "$template_dir" -type f -print | wc -l)
template_size_bytes=$(du -sb "$template_dir" | awk '{print $1}')
if (( template_file_count == 0 )); then
	fail "export-template directory is empty: $template_dir"
fi
if [[ ! -s "$template_dir/linux_debug.x86_64" || ! -s "$template_dir/linux_release.x86_64" ]]; then
	fail "Linux export templates are missing from $template_dir"
fi
if [[ ! -f "$template_dir/version.txt" ]] || ! grep -Fxq "$template_tag" "$template_dir/version.txt"; then
	fail "export-template version marker does not match $template_tag"
fi
printf 'PASS export templates: %s\n' "$template_dir"
printf 'EXPORT TEMPLATE FILE COUNT: %d\n' "$template_file_count"
printf 'EXPORT TEMPLATE SIZE BYTES: %s\n' "$template_size_bytes"
