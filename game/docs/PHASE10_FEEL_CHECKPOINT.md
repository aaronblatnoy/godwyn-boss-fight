# Phase 10 Feel Checkpoint

Date: 2026-09-28

## Verdict

This is a logic/greybox checkpoint, not a human playtest. Arena visuals, shaders, and gameplay materials are explicitly outside this phase's user-directed scope. It would therefore be misleading to assign either a fun rating or an Elden Ring-faithfulness rating: the current verdict is automated-smoke-only, and the human feel verdict remains pending.

A passing `test_vertical_slice.gd` smoke proves that boss HP decreases through real player-hitbox damage, the player takes damage from a real boss hitbox outside a roll, a pinned roll takes zero damage while the actual player `Hurtbox` overlaps an active boss `Hitbox` during the authored disabled-hurtbox i-frame window, boss poise breaks into stagger, and the fight reaches a death or victory end state. It cannot judge game feel, animation timing quality, visual readability, or camera feel under real human input.

## Tuning deltas

These are the provisional numeric fields in `game/scripts/systems/tunables.gd`. PLACEHOLDER fields and values backed only by approximate/community reference data should move first when authoritative reference measurements or a human tuning pass become available. No replacement values are proposed here.

- Line 72, `light_attack_combo_max_hits`: plan-contract placeholder; SPEC and the reference do not choose the exact cap.
- Line 91, `boss_poise_regen_delay`: approximate community reference value; SPEC requires regeneration but supplies no delay.
- Line 92, `boss_poise_regen_rate`: approximate community reference value; SPEC requires regeneration but supplies no rate.
- Line 108, `lightning_horizontal_sweep_line_count`: placeholder; SPEC supplies no line count.
- Line 110, `lightning_horizontal_sweep_line_thickness`: placeholder; SPEC supplies no line thickness.
- Line 112, `lightning_horizontal_sweep_gap_width`: placeholder selected around the sourced roll distance; SPEC supplies no gap width.
- Line 114, `lightning_horizontal_sweep_duration`: placeholder; SPEC supplies no sweep duration.
- Line 117, `lightning_shrinking_circle_start_radius`: SPEC marks the value approximate.
- Line 118, `lightning_shrinking_circle_end_radius`: SPEC marks the value approximate.
- Line 119, `lightning_shrinking_circle_contraction_speed`: SPEC marks the value approximate.
- Line 120, `lightning_shrinking_circle_contraction_duration`: SPEC marks the value approximate.
- Line 122, `lightning_shrinking_circle_ring_thickness`: placeholder; SPEC supplies no ring thickness.
- Line 124, `lightning_shrinking_circle_ring_segment_count`: placeholder; SPEC supplies no segment count.
- Line 125, `lightning_dragons_charge_fire_line_width`: SPEC marks the value approximate.
- Line 127, `lightning_dragons_charge_shove_knockback`: placeholder; SPEC supplies no shove knockback.
- Line 129, `lightning_dragons_charge_shove_radius`: placeholder; SPEC supplies no shove radius.
- Line 131, `lightning_dragons_charge_step_back_distance`: placeholder; SPEC supplies no step-back distance.
- Line 133, `lightning_dragons_charge_step_back_duration`: placeholder; SPEC supplies no step-back duration.
- Line 135, `lightning_dragons_charge_emergence_duration`: placeholder; SPEC supplies no emergence duration.
- Line 137, `lightning_dragons_charge_duration`: placeholder constrained only by SPEC's qualitative run-not-dodge rule.
- Line 159, `camera_lockon_focus_target_weight`: placeholder interpretation of boss-upper-center framing.
- Line 161, `camera_lockon_player_screen_offset_ratio`: placeholder interpretation of player-lower-left framing.
- Line 181, `ui_player_flask_empty_alpha`: placeholder; SPEC supplies no empty-flask alpha.
- Line 183, `ui_player_secondary_bar_background_color`: placeholder; SPEC supplies no FP/stamina background color.
- Line 188, `ui_boss_hp_background_color`: placeholder reuse of the specified player-HP background.
- Line 194, `ui_boss_name_line_1_color`: placeholder interpretation of SPEC's qualitative white-with-gold-tint direction.
- Line 196, `ui_boss_name_line_2_italic_shear`: placeholder; SPEC supplies no numeric italic shear.
- Line 198, `ui_boss_name_line_2_glyph_spacing`: placeholder; SPEC supplies no exact glyph spacing.
- Line 200, `ui_dragon_hp_size`: placeholder; SPEC supplies no Dragon's Memory secondary-bar size.
- Line 202, `ui_dragon_hp_bottom_offset`: placeholder; SPEC supplies no Dragon's Memory secondary-bar offset.
- Line 204, `ui_dragon_hp_color`: placeholder; SPEC supplies no Dragon's Memory secondary-bar color.
- Line 206, `ui_dragon_hp_background_color`: placeholder; SPEC supplies no Dragon's Memory secondary-bar background.
- Line 209, `ui_death_text_size`: placeholder interpretation of SPEC's qualitative "large" size.
- Line 222, `boss_pursuit_speed`: placeholder interpretation of "closes distance gradually."
- Line 224, `boss_circle_speed`: placeholder interpretation of "circles the player slowly."
- Line 226, `boss_pause_counter_step_distance`: placeholder interpretation of "steps offline."

Exact SPEC values retained in `tunables.gd` despite an approximate or unknown external reference, such as roll timing, flask duration, and stamina recovery, are not listed as tuning deltas because they remain sourced project decisions.

## Remaining SPEC placeholders

The project-level visual, animation, and Phase 1.5 omissions are summarized in the game README's [Known gaps](../README.md#known-gaps) section. In addition, `game/scripts/bosses/boss_base.gd` line 27 defines `BOSS_CAPSULE_RADIUS = 0.6` as an unsourced PLACEHOLDER. Phase 10's `game_manager.gd` consumes that constant for both the greybox capsule and lock-on marker geometry, so the capsule radius must be revisited when authoritative geometry arrives.

Per-move attack timing, geometry, damage, poise, and continuation gaps remain attached to their existing sourced-code comments and resource data; this report does not manufacture replacements.

## Frame-time profile

Status: CAPTURED

Run from the repository root on a machine with access to black-sky:

```bash
GODWYN_PROFILE_FRAMES=600 bash scripts/godot/run_native.sh p10-feel-profile 900
```

The first 300 frames are warmup; the final 600 frames are sampled from Godot's `Performance.TIME_PROCESS`, `Performance.TIME_PHYSICS_PROCESS`, and `Performance.TIME_FPS` monitors. The script prints the active adapter name/vendor and min/average/max summaries into both the terminal and `~/godwyn-ci/p10-feel-profile/logs/native-<UTC timestamp>.log`.

Captured on: `2026-09-28` (UTC), via `bash scripts/godot/run_native.sh p10-feel-profile 900` with `GODWYN_PROFILE_FRAMES=600`, black-sky, Godot 4.7.2.stable.official.

Active device: empty (`RenderingServer.get_video_adapter_name()` / `get_video_adapter_vendor()` both report empty strings). Godot's `--headless` mode does not initialize a video adapter at all -- there is no swapchain, no windowed surface, and no GPU rasterization path active during this measurement. This is a CPU-side engine-loop timing sample only; it says nothing about either RTX 3060 Ti's real rendering performance, which can only be measured with an actual display surface, explicitly forbidden by CLAUDE.md's headless-only invariant. Report this limitation plainly rather than implying a GPU frame-time result.

Verbatim profile output (real capture, `boot ok` confirmed main.tscn loaded and GameManager finished vertical-slice assembly before sampling began):

```text
boot ok
PHASE10_PROFILE device= vendor= headless=true warmup_frames=300 sample_frames=600
PHASE10_PROFILE process_ms min=0.114000 avg=0.169672 max=0.261000
PHASE10_PROFILE physics_ms min=0.631000 avg=0.747607 max=0.909000
PHASE10_PROFILE fps min=144.000 avg=144.860 max=145.000
```

Interpretation: `process_ms` (game-logic Node._process cost) and `physics_ms` (Node._physics_process cost, where all combat/AI/locomotion logic runs) both stay well under a single 60 Hz frame budget (16.6 ms), averaging 0.17 ms and 0.75 ms respectively with a worst-case sample of 0.91 ms. The reported `fps` (144-145) reflects an uncapped headless engine loop rather than a real display refresh rate; it is not the same figure a played, windowed session would show, but the very low process/physics costs indicate the current greybox scene (one player, one boss capsule, no animation-driven meshes yet, no particles/shaders) is far from any CPU-bound bottleneck at this stage. This measurement will need to be repeated once Phase 11's real rig and any Phase 1.5 lightning-layer visuals are active, and again with an actual windowed/rendered session once headless-only is not required for a specific investigation.

Black-sky has two installed RTX 3060 Ti devices; this single headless process reports only whatever adapter Godot's headless backend selects (here, none at all) and does not aggregate or split the sample across both GPUs.
