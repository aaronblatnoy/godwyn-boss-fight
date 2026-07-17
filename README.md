# Godwyn the Golden — Boss Fight

As much as we all love the Promised Consort boss fight, lets be real, it's not what any of us were hoping for. In fact, what we all wanted was to fight Godwyn the Golden, the Prince of Death himself. In this project, I attempt to use advanced tools (namely Claude Fable 5) to make this boss fight a reality. Stay tuned as I progress!

## Phase 1 Character Renders

Godwyn the Golden in his idealized prime — a demigod swordsman of peerless grace. All renders are GPU-accelerated via Cycles (OptiX/CUDA on 2x RTX 3060 Ti), produced headlessly from reproducible Blender scripts.

### Character Sheet (Multiple Views)

| Front | Three-Quarter Left | Three-Quarter Right |
|:---:|:---:|:---:|
| ![Front view](renders/character/front.png) | ![3Q Left](renders/character/3q_left.png) | ![3Q Right](renders/character/3q_right.png) |

| Back | Side | Face Close-up |
|:---:|:---:|:---:|
| ![Back view](renders/character/back.png) | ![Side view](renders/character/side.png) | ![Face](renders/character/face.png) |

### Weapon Detail

![Longsword](renders/character/sword.png)

Gold-hilted, blue-tinged blade with filigree crossguard — the mark of his grace.

### Moveset Action Poses

Seven signature poses from Phase 1 combat:

| Low Hang Guard | X Combo Hit 1 | X Combo Hit 2 |
|:---:|:---:|:---:|
| ![Low Hang Guard](renders/moveset/1_low_hang_guard.png) | ![X Combo 1](renders/moveset/2_x_combo_hit1.png) | ![X Combo 2](renders/moveset/3_x_combo_hit2.png) |

| Overhead Slam | Backhand Rotation | Jump Lunge |
|:---:|:---:|:---:|
| ![Overhead Slam](renders/moveset/4_overhead_slam.png) | ![Backhand](renders/moveset/5_backhand_rotation.png) | ![Jump Lunge](renders/moveset/6_jump_lunge.png) |

| Double Spin |
|:---:|
| ![Double Spin](renders/moveset/7_double_spin.png) |

## Rigged + Textured Game Asset (Phase 3)

`models/godwyn_game.glb` is the **rigged + de-clayed game-ready asset** — a glTF 2.0 export produced by `scripts/export_game_glb.py` from the baked gameasset pipeline (`scripts/bake_gameasset.py`). It carries the full armature with skinned weights, and three baked PBR textures (baseColor, metallic, roughness) embedded directly in the GLB. Verified headlessly on export:

| Property | Value |
|---|---|
| File size | ~19.4 MB |
| Bones | 24 (full body armature) |
| Meshes | 2 (skinned character + helper) |
| Materials | 1 (GodwynGameMat — Principled BSDF) |
| Textures | 3 baked PNGs embedded (albedo / metallic / roughness) |
| Rig | Skinned, rest-pose bind, +Y up (glTF 2.0) |
| De-clayed | Yes — baked from procedural PBR, no clay shading |

### Game Asset Turnaround

| Front | Three-Quarter | Side |
|:---:|:---:|:---:|
| ![Front](renders/game/game_front.png) | ![3Q](renders/game/game_3q.png) | ![Side](renders/game/game_side.png) |

## Animatable Game Asset (Phase 1 pipeline)

`models/godwyn_phase1.glb` is the Godot-4-ready export — a fully animatable glTF 2.0 asset verified by `scripts/07_export_glb.py`:

| Property | Value |
|---|---|
| File size | 74.9 MB |
| Armatures | 1 (`Godwyn_Armature`, 30 bones) |
| Meshes | 8 (body, armor, tabard, hair, sword, eyes, void crack + extras) |
| Blendshapes | 7 `Expr_*` shape keys (face expressions, Godot-ready) |
| Materials | 7 (6 with baseColor + normal maps, 1 eye material) |
| Textures | 18 baked PNGs (basecolor / metalRoughness / normal per mesh) |
| Rig | Skinned, rest-pose bind, +Y up (glTF 2.0 convention) |

The blue cloth is exported as `Godwyn_Tabard` — an integrated hanging front tabard/surcoat panel (waist-to-floor) with gold laurel embroidery, skinned to pelvis/spine/thigh/shin bones for natural cloth deformation. This is NOT a back cape — it is woven into the armor ensemble as per the SPEC.

The `.blend` keeps its procedural Cycles beauty materials intact; the `.glb` ships baked texture maps baked by `03b_bake_maps.py` so surface detail (pores, weave, gold wear, hair streaks) survives the glTF export.

## How to Regenerate

All renders are generated deterministically from Python scripts via Blender's headless mode. To regenerate the full asset suite:

```bash
ssh mossad "cd ~/godwyn-boss-fight && bash scripts/build_all.sh"
```

This runs all phases (0–7) sequentially:
- **Phase 0:** Environment check, GPU device enumeration (OptiX gate)
- **Phase 1:** Base humanoid mesh via MPFB2 (anatomical 19 158-vert human)
- **Phase 2:** Armor, robe, hair, longsword on the MPFB2 body
- **Phase 3:** Procedural materials (skin SSS + inner glow, gold, robe, blade, hair, void)
- **Phase 4:** Armature (30 bones), dark-fantasy lighting rig, 8 cameras
- **Phase 4b:** Macro form-check renders (raking light clay views)
- **Phase 4c:** GPU bake procedural detail → PNG maps + export base GLB
- **Phase 5:** Character sheet renders (7 views, 2K portrait)
- **Phase 6:** Moveset pose renders (7 action stills, 2K cinematic)
- **Phase 7:** Final animatable GLB export + verification gate (Godot-ready)

Outputs:
- `models/godwyn_phase1.blend` — complete rigged model (procedural beauty mats)
- `models/godwyn_phase1.glb` — animatable Godot-4-ready export (baked textures)
- `models/textures/` — 18 baked PNG maps (source for the GLB)
- `renders/character/*.png` — character sheet (2K portrait, 2048×2560)
- `renders/moveset/*.png` — pose stills (2K cinematic, 1440×2560)

For details on the build process, see `blender-build-plan.txt`.

## Credits

Visual inspiration: fan art by **Enzo Spag** and **@DOUJ**  
Built with: Blender 5.1.2 (Cycles GPU / OptiX), Claude Fable 5  
Specification: SPEC.txt, boss-fight.txt
