"""
RE-OUTFIT Phase 4 critic (round 1) — beauty + face + deform-test renders.

Opens models/godwyn_phase1.blend (judgement pass: NOTHING is saved), asserts a
GPU (OptiX/CUDA) device is enabled (CPU fallback = hard failure), then renders:

  1. renders/wip/ro_c1_full.png        — full-body beauty (Cam_Full/Cam_Sheet)
  2. renders/wip/ro_c1_face.png        — face close-up (Cam_Face)
  3. renders/wip/ro_c1_back.png        — back 3/4 (cape + rear plate check)
  4. renders/wip/ro_c1_deform.png      — DEFORM TEST: arm raise + forearm curl
       + spine twist + finger grip + Expr blendshape 0.7
  5. renders/wip/ro_c1_deform_face.png — driven expression close-up

Also prints an ANIM AUDIT (one armature, every armor mesh skinned/parented,
shape keys intact, no sim modifiers) and a SKIN-COVERAGE listing of meshes.

Run:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p_reoutfit_critic_r1.py
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
_FULL_CANDIDATES = ["Cam_Full", "Cam_Sheet", "Cam_ThreeQuarter_L", "Cam_Front"]
_BACK_CANDIDATES = ["Cam_Back", "Cam_ThreeQuarter_R", "Cam_ThreeQuarter_L"]
_DEFORM_CANDIDATES = ["Cam_ThreeQuarter_L", "Cam_Full", "Cam_Front"]


def _pick(cands, allow_none=False):
    for name in cands:
        if name in bpy.data.objects:
            return name
    if allow_none:
        return None
    cams = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    raise AssertionError(f"FATAL: no camera among {cands}; present: {cams}")


def _pose_rotate(arm, bone, axis, deg):
    pb = arm.pose.bones.get(bone)
    if pb is None:
        print(f"[ro c1] WARN: bone {bone} missing")
        return
    pb.rotation_mode = "AXIS_ANGLE"
    pb.rotation_axis_angle = (math.radians(deg), *axis)


def anim_audit():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    print(f"[ro c1] ARMATURES ({len(arms)}): {[a.name for a in arms]}")
    assert len(arms) == 1, "FATAL: expected exactly ONE armature"
    arm = arms[0]
    _ENV = ("VoidCrack", "Void", "Env", "Ground", "Floor")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and not any(t in o.name for t in _ENV)]
    print(f"[ro c1] CHARACTER MESHES ({len(meshes)}):")
    for m in sorted(meshes, key=lambda o: o.name):
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
        nverts = len(m.data.vertices)
        print(f"[ro c1]  {m.name}: verts={nverts} skinned={skinned} "
              f"bone_parent={bone_par} mods={mods} sim={bad}")
        assert not bad, f"FATAL: un-riggable sim modifier on {m.name}"
        assert skinned or bone_par is not None, (
            f"FATAL: {m.name} not attached to armature")
    body = bpy.data.objects.get("Godwyn_Body")
    assert body is not None and body.data.shape_keys, (
        "FATAL: Godwyn_Body shape keys missing")
    keys = [k.name for k in body.data.shape_keys.key_blocks]
    print(f"[ro c1] SHAPE KEYS ({len(keys)}): {keys}")
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            dm = getattr(mat.cycles, "displacement_method", None)
            if dm in ("DISPLACEMENT", "BOTH"):
                print(f"[ro c1]  NOTE: material {mat.name} geometry "
                      f"displacement method={dm} (render-only allowed)")
    return arm, body


def main():
    scene = bpy.context.scene
    dev_type = G.enable_gpu(prefer_optix=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpus = [d for d in prefs.devices if d.use and d.type in ("OPTIX", "CUDA")]
    assert dev_type in ("OPTIX", "CUDA") and gpus, "FATAL: no GPU enabled"
    print(f"[ro c1] GPU OK: {dev_type} — " + ", ".join(d.name for d in gpus))

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
        print(f"[ro c1] rendering {cam} -> {out}")
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out) and os.path.getsize(out) > 1024, (
            f"FATAL: render missing: {out}")
        print(f"[ro c1] wrote {out} ({os.path.getsize(out)//1024} KB)")

    full_cam = _pick(_FULL_CANDIDATES)
    shoot(full_cam, "ro_c1_full.png", 1280, 1600)
    shoot("Cam_Face", "ro_c1_face.png", 1280, 1280)
    back_cam = _pick(_BACK_CANDIDATES, allow_none=True)
    if back_cam:
        shoot(back_cam, "ro_c1_back.png", 1280, 1600)

    # --- deform test: pose + blendshape ------------------------------------
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    _pose_rotate(arm, "upper_arm.R", (0, 1, 0), 55.0)
    _pose_rotate(arm, "forearm.R", (1, 0, 0), -50.0)
    _pose_rotate(arm, "spine.01", (0, 0, 1), 15.0)
    _pose_rotate(arm, "thigh.L", (1, 0, 0), -30.0)
    _pose_rotate(arm, "shin.L", (1, 0, 0), 45.0)
    _pose_rotate(arm, "head", (0, 0, 1), -10.0)
    grip = [b.name for b in arm.pose.bones
            if b.name.endswith(".R") and any(
                t in b.name.lower() for t in
                ("finger", "thumb", "index", "middle", "ring", "pinky"))]
    for bn in grip:
        _pose_rotate(arm, bn, (1, 0, 0), 40.0)
    if not grip and "hand.R" in arm.pose.bones:
        _pose_rotate(arm, "hand.R", (1, 0, 0), 35.0)
    print(f"[ro c1] grip bones curled: {len(grip)}")
    bpy.ops.object.mode_set(mode="OBJECT")
    kb = body.data.shape_keys.key_blocks.get("Expr_BrowSorrow")
    if kb is None:
        others = [k for k in body.data.shape_keys.key_blocks
                  if k.name != "Basis"]
        assert others, "FATAL: no non-Basis blendshapes"
        kb = others[0]
    kb.value = 0.7
    bpy.context.view_layer.update()

    basis = body.data.shape_keys.key_blocks["Basis"]
    moved, mx = 0, 0.0
    for i, v in enumerate(kb.data):
        d = (v.co - basis.data[i].co).length
        if d > 1e-6:
            moved += 1
            mx = max(mx, d)
    print(f"[ro c1] blendshape '{kb.name}': {moved} verts moved, "
          f"max delta {mx*1000:.2f} mm")
    assert moved > 0, "FATAL: blendshape has zero vertex deltas"

    shoot(_pick(_DEFORM_CANDIDATES), "ro_c1_deform.png", 1280, 1600)
    shoot("Cam_Face", "ro_c1_deform_face.png", 1280, 1280)
    print("[ro c1] critic renders complete (scene NOT saved).")


if __name__ == "__main__":
    main()
