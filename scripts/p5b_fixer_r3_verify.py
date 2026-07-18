"""
Phase 5 critic (DETAIL+ANIM pass, round 3) — beauty + deform-test renders.

Opens models/godwyn_phase1.blend (judgement pass: NOTHING is saved), asserts a
GPU (OptiX/CUDA) device is enabled (CPU fallback = hard failure), then renders:

  1. renders/wip/p5b_fx3_full.png   — full-body beauty (Cam_Full fallback chain)
  2. renders/wip/p5b_fx3_face.png   — face close-up (Cam_Face)
  3. renders/wip/p5b_fx3_deform.png — DEFORM TEST: bent arm + elbow crook +
       torso twist + Expr_BrowSorrow blendshape driven to 0.7, rendered from
       Cam_ThreeQuarter_L (fallback: full cam).

Also prints an ANIM AUDIT: armature count, meshes skinned/parented, shape key
list, whether any un-riggable geometry-level displacement/sim modifiers exist.

Run:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p5b_critic_r3.py
"""
import math
import os
import sys

import bpy

_REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
import lib_godwyn as G  # noqa: E402

_WIP = os.path.join(_REPO_ROOT, "renders", "wip")
os.makedirs(_WIP, exist_ok=True)

SAMPLES = 256
_FULL_CANDIDATES = ["Cam_Full", "Cam_ThreeQuarter_L", "Cam_Front"]
_DEFORM_CANDIDATES = ["Cam_ThreeQuarter_L", "Cam_Full", "Cam_Front"]


def _pick(cands):
    for name in cands:
        if name in bpy.data.objects:
            return name
    cams = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    raise AssertionError(f"FATAL: no camera among {cands}; present: {cams}")


def _pose_rotate(arm, bone, axis, deg):
    pb = arm.pose.bones[bone]
    pb.rotation_mode = "AXIS_ANGLE"
    pb.rotation_axis_angle = (math.radians(deg), *axis)


def anim_audit():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    print(f"[p5b fx3] ARMATURES ({len(arms)}): {[a.name for a in arms]}")
    assert len(arms) == 1, "FATAL: expected exactly ONE armature"
    arm = arms[0]
    _ENV = ("VoidCrack", "Void", "Env", "Ground", "Floor")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and not any(t in o.name for t in _ENV)]
    for m in meshes:
        mods = [mo.type for mo in m.modifiers]
        skinned = any(mo.type == "ARMATURE" and mo.object == arm
                      for mo in m.modifiers)
        chain = m
        bone_par = None
        while chain is not None:
            if chain.parent == arm:
                bone_par = chain.parent_bone or "(object)"
                break
            chain = chain.parent
        bad = [t for t in mods if t in
               ("CLOTH", "SOFT_BODY", "OCEAN", "EXPLODE", "FLUID")]
        print(f"[p5b fx3]  mesh {m.name}: skinned={skinned} "
              f"parent_chain_to_arm={bone_par} mods={mods} sim_mods={bad}")
        assert not bad, f"FATAL: un-riggable sim modifier on {m.name}"
        assert skinned or bone_par is not None, (
            f"FATAL: {m.name} not attached to armature")
    body = bpy.data.objects.get("Godwyn_Body")
    assert body is not None and body.data.shape_keys, (
        "FATAL: Godwyn_Body shape keys missing")
    keys = [k.name for k in body.data.shape_keys.key_blocks]
    print(f"[p5b fx3] SHAPE KEYS ({len(keys)}): {keys}")
    # displacement audit: TRUE displacement (geometry) vs bump-only
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            dm = getattr(mat.cycles, "displacement_method", None)
            if dm == "DISPLACEMENT" or dm == "BOTH":
                print(f"[p5b fx3]  NOTE: material {mat.name} uses geometry "
                      f"displacement method={dm} (beauty-only allowed)")
    return arm, body


def main():
    scene = bpy.context.scene
    dev_type = G.enable_gpu(prefer_optix=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpus = [d for d in prefs.devices if d.use and d.type in ("OPTIX", "CUDA")]
    assert dev_type in ("OPTIX", "CUDA") and gpus, "FATAL: no GPU enabled"
    print(f"[p5b fx3] GPU OK: {dev_type} — " + ", ".join(d.name for d in gpus))

    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except TypeError:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    arm, body = anim_audit()

    def shoot(cam, out_name, rx, ry):
        scene.camera = bpy.data.objects[cam]
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        scene.render.resolution_percentage = 100
        out = os.path.join(_WIP, out_name)
        scene.render.filepath = out
        print(f"[p5b fx3] rendering {cam} -> {out}")
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out) and os.path.getsize(out) > 1024, (
            f"FATAL: render missing: {out}")
        print(f"[p5b fx3] wrote {out} ({os.path.getsize(out)//1024} KB)")

    full_cam = _pick(_FULL_CANDIDATES)
    shoot(full_cam, "p5b_fx3_full.png", 1280, 1600)
    shoot("Cam_Face", "p5b_fx3_face.png", 1280, 1280)

    # --- deform test: pose + blendshape ------------------------------------
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    _pose_rotate(arm, "upper_arm.R", (0, 1, 0), 55.0)
    _pose_rotate(arm, "forearm.R", (1, 0, 0), -50.0)
    _pose_rotate(arm, "spine.01", (0, 0, 1), 15.0)
    _pose_rotate(arm, "head", (0, 0, 1), -10.0)
    # gripping hand: curl every finger bone on the right (sword) hand
    grip = [b.name for b in arm.pose.bones
            if b.name.endswith(".R") and any(
                t in b.name.lower() for t in
                ("finger", "thumb", "f_index", "f_middle", "f_ring",
                 "f_pinky", "index", "middle", "ring", "pinky"))]
    for bn in grip:
        _pose_rotate(arm, bn, (1, 0, 0), 40.0)
    if not grip and "hand.R" in arm.pose.bones:
        _pose_rotate(arm, "hand.R", (1, 0, 0), 35.0)
    print(f"[p5b fx3] grip bones curled: {len(grip)} -> {grip[:6]}")
    bpy.ops.object.mode_set(mode="OBJECT")
    kb = body.data.shape_keys.key_blocks.get("Expr_BrowSorrow")
    if kb is None:
        others = [k for k in body.data.shape_keys.key_blocks
                  if k.name != "Basis"]
        assert others, "FATAL: no non-Basis blendshapes"
        kb = others[0]
    kb.value = 0.7
    print(f"[p5b fx3] deform pose applied; blendshape '{kb.name}'=0.7")
    bpy.context.view_layer.update()

    # quantitative blendshape probe: max vertex delta vs Basis
    basis = body.data.shape_keys.key_blocks["Basis"]
    moved = 0
    mx = 0.0
    for i, v in enumerate(kb.data):
        d = (v.co - basis.data[i].co).length
        if d > 1e-6:
            moved += 1
            mx = max(mx, d)
    print(f"[p5b fx3] blendshape '{kb.name}': {moved} verts moved, "
          f"max delta {mx*1000:.2f} mm (x0.7 driven at render)")
    assert moved > 0, "FATAL: blendshape has zero vertex deltas"

    shoot(_pick(_DEFORM_CANDIDATES), "p5b_fx3_deform.png", 1280, 1600)
    # face close-up of the DRIVEN expression so the blendshape is judgeable
    shoot("Cam_Face", "p5b_fx3_deform_face.png", 1280, 1280)
    print("[p5b fx3] critic renders complete (scene NOT saved).")


if __name__ == "__main__":
    main()
