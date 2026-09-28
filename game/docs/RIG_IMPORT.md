# Phase 11 Godwyn Rig Import

The production binary is `godwyn_v3.glb`, sourced from
`models/astra_character_v3.glb`. It is deliberately absent from the Mac game
tree and Git. The canonical staged copy lives only at
`black-sky:~/godwyn-boss-fight/game/assets/godwyn/godwyn_v3.glb`; `ci.sh`
copies it into each black-sky CI workspace before headless import.

The imported Meshy asset contains one 24-bone skeleton and the baked
`Combat_Stance` clip. Its authored mesh bounds are 3.186094 m high, so
`godwyn_phase1.tscn` applies a uniform 0.991812 scale for a 3.16 m standing
height. `GodwynVisual` starts `Combat_Stance` and owns visual playback only.
The sword remains the separately named `Godwyn_Sword` mesh in the imported
rig and follows its existing hand/skinning relationship.

The visual wrapper adds a low-alpha Phase 1 gold-emission overlay using the
SPEC color/strength and a shadow-casting 12 m OmniLight. It adds no crown,
dark markings, or deathroot and does not alter the imported geometry.

## Animation call-track contract

`BossBase` keeps its existing combat-only `AnimationPlayer`. `AttackLibrary`
builds one-second placeholder clips whose method tracks call
`BossHitbox.activate_window(window)` and `BossHitbox.deactivate()` at each
`AttackData.active_windows` normalized start/end. The imported rig's visual
player runs alongside it and never owns damage. When a real attack clip is
added, its duration may replace the placeholder duration, but the same
normalized windows must be projected onto that duration and the hitbox calls
must remain on the combat player.

| AttackData / placeholder clip | Normalized hitbox windows |
|---|---|
| `x_combo` | 0.15–0.30, 0.50–0.65 |
| `jump_lunge` | 0.55–0.78 |
| `the_pause` | none |
| `dragons_memory` | 0.00–1.00 |
| `radiant_sequence` | 0.18–0.32, 0.48–0.62 |
| `sacred_cleave` | 0.38–0.56, 0.60–0.88 |
| `horizontal_sweep` | 0.20–0.45 |
| `overhead_slam` | 0.50–0.78 |
| `backhand_rotation` | 0.15–0.40 |
| `branch_a_double_spin` | 0.10–0.25, 0.55–0.72 |
| `branch_b_half_spin_overhead` | 0.55–0.78 |
| `branch_c_full_half_overhead` | 0.08–0.20, 0.35–0.48, 0.72–0.90 |
| `flow_into_x` | 0.18–0.40 |
| `jump_lunge_connect` | 0.20–0.40 |
| `jump_thrust` | 0.55–0.80 |
| `straight_stab_quiet` | 0.20–0.38 |

The Phase 1.5 lightning resources with empty `animation_clip` fields retain
their subsystem timing and are outside this visual-rig seam.

No LOD bypass is enabled: black-sky imports the full asset in CI so the actual
300k-triangle-class production payload remains covered.
