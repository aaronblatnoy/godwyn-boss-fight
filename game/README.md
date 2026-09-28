# Godwyn Boss Fight

This directory is the Godot `res://` root for the Godwyn boss-fight project. Phase 0 is a logic-only bootstrap: it contains the project contract, a minimal boot scene, sourced tunables, and headless tests. It intentionally contains no arena art, shaders, particles, lighting design, or custom materials.

## Local editing

For future human editing, open `game/project.godot` in the Godot 4 editor on the Mac. Do not open or run the Godot GUI on black-sky.

All imports, builds, scene smoke checks, and automated tests must run headlessly on black-sky over SSH, as required by the headless-only invariant in `CLAUDE.md`. Never invoke Godot locally on the Mac for automated work.

From the repository root, run the full reusable CI entrypoint with:

```bash
bash scripts/godot/ci.sh
bash scripts/godot/ci.sh p0
```

The optional CI label defaults to `p0`. CI synchronizes `game/` with `rsync --delete`, imports it on black-sky, discovers every `game/tests/*.gd` file, and runs each as a headless `SceneTree` script with a timeout.

The three server-toolchain scripts have separate responsibilities:

- `scripts/godot/install_godot.sh` is piped over SSH and runs entirely on black-sky. It verifies the exact Godot 4.7.2 binary, installs `vulkan-tools` when needed, requires both RTX 3060 Ti GPUs in bare-headless `vulkaninfo` output, and idempotently installs the matching Linux export templates.
- `scripts/godot/headless_import.sh` is a Phase 0 boot-smoke helper run on the Mac. It synchronizes to `~/godwyn-ci/p0/game/`, performs a headless import, runs `main.tscn`, and requires the `boot ok` marker.
- `scripts/godot/ci.sh` is the one true test entrypoint for Phase 0 and all later phases. Later phases add tests and rerun the same command.

To verify the server binary directly:

```bash
ssh black-sky "~/bin/godot --headless --version"
ssh black-sky "bash -s" < scripts/godot/install_godot.sh
```

## Framework Evaluation

Phase 0 framework-evaluation scorecard, timeboxed on 2026-09-27 against the five bars in SPEC Section 1:

- [Third-Person-Controller--SoulsLIke-Godot4](https://github.com/catprisbrey/Third-Person-Controller--SoulsLIke-Godot4): lock-on FAIL (the published feature list does not identify one); genuine i-frames FAIL (roll animation is listed, but hurtbox/invulnerability timing is not); stamina FAIL (not listed); animation-driven combat PASS (AnimationTree and combo attacks are central); active Godot-4 maintenance FAIL (the repository calls itself an early/outdated port).
- [Cat's Godot 4 Modular Souls-Like Template](https://github.com/catprisbrey/Cats-Godot4-Modular-Souls-like-Template): lock-on PASS (enemy targeting); genuine i-frames FAIL (dodge rolling is present, but no genuine hurtbox-disable window is documented); stamina FAIL (not documented in the published feature list); animation-driven combat PASS (animation libraries, nested AnimationTrees, and root motion); active Godot-4 maintenance FAIL (the repository says this codebase is pending wholesale replacement).
- [RIFT Game Jam Template](https://github.com/Ayush-Mohanty/Rift-GameJam-Template): lock-on FAIL (not documented); genuine i-frames FAIL (not documented); stamina FAIL (not documented); animation-driven combat FAIL (cutscene AnimationPlayer use does not establish animation-keyed combat hitboxes); Godot-4 compatibility PASS, active maintenance UNPROVEN.

Scorecard conclusion: none clears all five bars. Phase 0 therefore records the plan Assumption A2 decision to build the combat foundation from scratch with `CharacterBody3D`, `AnimationPlayer`, and `AnimationTree`; no third-party framework is vendored.

## Rendering baseline

`project.godot` selects Forward+ and a documented 2x MSAA baseline; SPEC Section 13 gives no MSAA count, so this is explicitly marked for later tuning rather than represented as a SPEC value. `scenes/main.tscn` carries the otherwise empty Phase 0 `WorldEnvironment`: bloom threshold maps to `glow_hdr_threshold = 0.85`, intensity maps to `glow_intensity = 0.6`, and the non-1:1 radius value `3.0` maps to Godot's third glow level (`glow_levels/3 = 1.0`) with all other level weights zero. Saturation, contrast, and brightness use the corresponding `adjustment_*` properties at 0.8, 1.1, and 0.95.

## Frozen collision layers

| Layer | Name |
|---:|---|
| 1 | `world` |
| 2 | `player_body` |
| 3 | `boss_body` |
| 4 | `player_hurtbox` |
| 5 | `player_hitbox` |
| 6 | `environment` |
| 7 | `boss_hurtbox` |
| 8 | `boss_hitbox` |
| 9 | `lockon_target` |

Combat in later phases must use animation-driven `Area3D` hitbox and hurtbox events on these dedicated layers. Physics-body collisions are not combat hit detection.

## Frozen input actions

The action names are:

`move_fwd`, `move_back`, `move_left`, `move_right`, `sprint`, `roll`, `light_attack`, `heavy_attack`, `use_flask`, `lock_on`, `target_left`, `target_right`, `interact`, `pause`.

Keyboard and mouse defaults are functional, with matching gamepad inputs where applicable. `target_left` is Q and `target_right` is E.

## Tunables

Phase-wide numeric configuration lives in `scripts/systems/tunables.gd`. Every numeric field carries a source comment naming `SPEC.txt` or `elden-ring-combat-reference.md`. In this file, only the reference's exact roll stamina cost overrides a SPEC placeholder; lock-on remains exactly at SPEC's 25 m acquisition and 35 m break distances because camera behavior is not in plan Assumption A6's reference-document override list. Approximate SPEC numbers are labeled as approximate, and approximate or unknown reference values do not override exact SPEC values. Do not add guessed values: later phases extend this resource only when an authoritative source provides the number.

## How to run

For interactive editing, open `game/project.godot` in the Godot 4 editor on the Mac. The assembled `main.tscn` creates the Void, player, camera, Godwyn logic capsule, lock-on marker, and combat UI through `game_manager.gd`.

From the repository root, run all automated tests headlessly on black-sky with a descriptive label:

```bash
bash scripts/godot/ci.sh p10
```

To sync and boot the assembled main scene headlessly for manual inspection of runtime prints, including `boot ok`, use:

```bash
bash scripts/godot/run_native.sh p10-native
bash scripts/godot/run_native.sh p10-native 900
```

The optional second argument is the number of frames before the headless process exits. Logs are retained under `~/godwyn-ci/<label>/logs/` on black-sky. Never run the Godot GUI on the server; black-sky is headless-only.

## Controls

| Input action | Default keyboard/mouse control | Behavior |
|---|---|---|
| `move_fwd`, `move_back`, `move_left`, `move_right` | W, S, A, D | Move relative to the camera; strafe while locked on. |
| `sprint` | Left Shift | Sprint while moving and not locked on. |
| `roll` | Space | Mid-roll dodge with the authored hurtbox-disabled i-frame window. |
| `light_attack` | Left mouse button | Perform or buffer a light attack. |
| `heavy_attack` | Right mouse button | Perform a heavy attack. |
| `use_flask` | R | Consume a flask and heal when the drink completes. |
| `lock_on` | Middle mouse button | Toggle lock-on to a valid layer-9 target. |
| `target_left`, `target_right` | Q, E | Cycle left or right among valid lock-on targets. |
| `interact` | F | Reserved interaction action. |
| `pause` | Escape | Reserved pause action. |

## Layer map

| Layer | Name | Current occupants / role |
|---:|---|---|
| 1 | `world` | Void floor and invisible arena boundary. |
| 2 | `player_body` | Player `CharacterBody3D`. |
| 3 | `boss_body` | Reserved boss physics-body layer. |
| 4 | `player_hurtbox` | Player `Hurtbox` `Area3D`. |
| 5 | `player_hitbox` | Player weapon `Hitbox` `Area3D`. |
| 6 | `environment` | Reserved environment collision layer. |
| 7 | `boss_hurtbox` | Godwyn runtime `BossHurtbox` `Area3D`. |
| 8 | `boss_hitbox` | Godwyn runtime `BossHitbox` `Area3D`. |
| 9 | `lockon_target` | Godwyn's direct-child `LockOnMarker` `Area3D`; the camera's acquisition area masks this layer. |

Combat damage remains exclusively on the dedicated hitbox/hurtbox `Area3D` pairs. Body and world collision do not resolve combat hits.

## Known gaps

This Phase 10 checkpoint is intentionally logic-only. The player and Godwyn are capsule placeholders on the flat grey Void floor; there is no arena visual pass, lighting design, fog, particle work, or gameplay material work. The Phase 1.5 lightning layer is not added to the default vertical-slice assembly, although its isolated subsystem and tests remain in the project.

Godwyn still uses runtime placeholder attack clips and has no production rig or real animation set. Phase 11 replaces only the visual capsule with the real mesh while preserving the combat code and node contracts. Existing sourced-code comments identify remaining SPEC placeholders, including the boss capsule radius and per-move attack timing, geometry, damage, poise, and continuation values where the design documents do not provide exact numbers.

The Phase 10 automated-smoke verdict, prioritized tuning deltas, and a real captured black-sky frame-time profile are tracked in [`docs/PHASE10_FEEL_CHECKPOINT.md`](docs/PHASE10_FEEL_CHECKPOINT.md).
