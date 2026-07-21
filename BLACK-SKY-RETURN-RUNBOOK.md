# Black-sky-Return Runbook

When the render server (`black-sky`) is back up, run these in order. Everything below
needs the server (Blender/GPU); it was prepped while black-sky was down.

## 0. Verify the server
```
ssh black-sky "cd ~/godwyn-boss-fight && git pull && nvidia-smi | head -20 && blender --version"
```

## 1. Resume the FACE + SWORD fix  (was paused mid-run)
Separates the fused sword into its own object with a natural grip parented to the hand
bone, and reshapes the face narrower/more masculine toward `body-concepts/god_C.png`.
```
Workflow({ scriptPath: '/Users/aaron_7nh0yzm/godwyn-boss-fight/godwyn-facesword-workflow.js',
           resumeFromRunId: 'wf_a4f2f603-c3c' })
```
Output: updated `models/godwyn_game.glb` (separate Godwyn_Sword, reshaped face).
Honest risk: the face reshape may not fully reach the concept — the workflow will say so.

## 2. Run the MOVEMENT-QUALITY pass  (the "it moves badly" fix)
Cleans the auto-rig skin weights (kills joint pinching) and puts the floor robe/cape/hair
on physics bone chains so they FLOW instead of stretching with the legs. Depends on #1.
```
Workflow({ scriptPath: '/Users/aaron_7nh0yzm/godwyn-boss-fight/godwyn-movement-workflow.js' })
```
Output: `models/godwyn_game.glb` that deforms cleanly when animated.

## 3. FINAL animations  (make him actually move like Godwyn)
The skeleton is Mixamo-standard on purpose → retarget professional Mixamo mocap for
locomotion + the moveset attacks. This likely needs a few **Mixamo FBX clips** supplied
(Adobe login) — a manual step. Plan this after #2 confirms clean deformation.

## 4. Then: build the actual GAME (Godot)
- Install Godot on the server, execute `lifecycle/pending/plans/godot-combat-foundation-plan.txt`.
- Tune to `elden-ring-combat-reference.md` (remember the 30fps→60fps doubling).
- Target the P10 greybox vertical slice first (capsule player vs capsule Godwyn), then
  swap in `models/godwyn_game.glb`.

## Open design decisions (resolve before/while building combat)
- Lock-on distance: 15m (authentic) vs 25m (current SPEC).
- Phase-2 HP: reset to 3000 (current design) vs continuous bar (ER default).

## Current best asset
`models/godwyn_game.glb` — rigged + de-clay PBR baked in. #1 and #2 improve it in place.
