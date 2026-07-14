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

## How to Regenerate

All renders are generated deterministically from Python scripts via Blender's headless mode. To regenerate the asset suite:

```bash
ssh mossad "cd ~/godwyn-boss-fight && bash scripts/build_all.sh"
```

This runs all phases (0–6) sequentially:
- **Phase 0:** Environment check, GPU device enumeration
- **Phase 1:** Base humanoid mesh (3.2m, 1.4x proportions)
- **Phase 2:** Details (armor, robe, hair, longsword)
- **Phase 3:** Materials and shaders (emissive skin, metallic armor, void backdrop)
- **Phase 4:** Armature, lighting rig, cameras, save .blend
- **Phase 5:** Character sheet renders (7 views)
- **Phase 6:** Moveset pose renders (7 action stills)

Outputs:
- `models/godwyn_phase1.blend` — complete 3D model (regenerable from scripts)
- `renders/character/*.png` — character sheet (2K portrait, ~2048×2560)
- `renders/moveset/*.png` — pose stills (2K, ~1920×2560)

For details on the build process, see `blender-build-plan.txt`.

## Credits

Visual inspiration: fan art by **Enzo Spag** and **@DOUJ**  
Built with: Blender 4.x (Cycles GPU), Claude Fable 5  
Specification: SPEC.txt, boss-fight.txt
