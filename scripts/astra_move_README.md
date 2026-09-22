# Godwyn move authoring

Blender 5.2.1, local Metal / EEVEE only. Run from the repository root:

```
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_idle_guard_build.py
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_audit.py -- idle_guard
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_grip.py -- idle_guard render
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_loop_verify.py -- idle_guard
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_render.py -- idle_guard preview
python3 scripts/astra_move_package.py idle_guard preview
# Inspect the preview sheet, then:
/opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_move_render.py -- idle_guard
python3 scripts/astra_move_package.py idle_guard
```

Substitute each move name in turn. Builders share `astra_move_common.py`; package generation uses the already installed ffmpeg/ffprobe and Python standard library. Blender supplies NumPy. No downloads or installs.

`models/astra_move_character_base.blend` freezes the character input across the set. If absent, the first builder copies `models/astra_character_v2_prechar2.blend` to that move-owned path. Builders always reopen the frozen base, clear its action, and save only their own derived model. They do not accumulate pose edits across reruns. Original character/X-slash/cinematography files remain read-only.

The actual 121-bone rig is baked at quarter frames. Foot/robe clearance correction is measured on deformed vertices; chain locations are used only for cloth gathering, not limb stretching. All numerical results live beside the films. `<name>_samples.json` contains the full quarter-frame transforms; `<name>_metrics.json`, `<name>_contacts.json`, and `<name>_video_verification.json` expose the underlying checks.

Cyclic actions include a duplicate endpoint in the blend and Cycles modifiers. Their MP4 omits that duplicate frame. `loop_period_frames` and `cycle_root_displacement` are saved on the scene; locomotion repeats with the documented root offset.

The stable pre-char2 character is used directly. The current mutable character file and its face/hair additions are never loaded.

The grip audit verifies rigid RightHand-only skinning on every sword vertex, quarter-frame hilt transforms and evaluated closed-finger geometry at every integer frame. Close-ups are retained under `<name>/grip/`. The derived-only static grasp repair is in `astra_move_grip_fix.py`; it never modifies the frozen input.

For attacks, run `python3 scripts/astra_move_attack_verify.py <name>` after the skeleton and grip audits. A fast pre-bake authoring probe is available with `-- --probe` after a build-script command. `physics_audit.md` records the actual visual review and defect dispositions; generating numbers alone does not complete a move.

Additional offline checks: `python3 scripts/astra_move_balance_sensitivity.py <name>` tests 2/4/6% sword mass, and `python3 scripts/astra_move_secondary_audit.py <name>` measures cape lag against its upper-spine attachment. Run `python3 scripts/astra_move_verify_deliverables.py` after all four audit sections are complete to check the frozen-source hashes, required files, grip tolerances and encoded frame counts.
