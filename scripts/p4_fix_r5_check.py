"""
REFINEMENT Phase 4 fixer round 5 — verification renders (judgement pass).

Opens models/godwyn_phase1.blend (NOTHING is saved), asserts a GPU
(OptiX/CUDA) device (CPU fallback = hard failure), then renders:

  1. renders/wip/f_r5_full.png        — full-body beauty (ornament read @ 1280px)
  2. renders/wip/f_r5_face.png        — face close-up (eyes/brows/lips/skin)
  3. renders/wip/f_r5_torso.png       — cuirass emblem + arm harness detail
  4. renders/wip/f_r5_tabard.png      — tabard embroidery + fauld/tasset overlap
  5. renders/wip/f_r5_deform.png      — DEFORM TEST: natural guard-ish pose
       + Expr_BrowSorrow 0.7 (animatability proof)

Also prints the ANIM AUDIT (one armature, all meshes bound, shape keys).

Run:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p4_fix_r5_check.py
"""
import math
import os
import sys

import bpy
from mathutils import Vector

_REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
import lib_godwyn as G  # noqa: E402

_WIP = os.path.join(_REPO_ROOT, "renders", "wip")
os.makedirs(_WIP, exist_ok=True)

SAMPLES = 192
_FULL_CANDIDATES = ["Cam_Full", "Cam_Sheet", "Cam_ThreeQuarter_L", "Cam_Front"]
_DEFORM_CANDIDATES = ["Cam_ThreeQuarter_L", "Cam_Full", "Cam_Front"]


def _pick(cands):
    for name in cands:
        if name in bpy.data.objects:
            return name
    cams = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    raise AssertionError(f"FATAL: no camera among {cands}; present: {cams}")


def _pose_rotate(arm, bone, axis, deg):
    pb = arm.pose.bones.get(bone)
    if pb is None:
        print(f"[f r5] WARN: bone {bone} missing")
        return
    pb.rotation_mode = "AXIS_ANGLE"
    pb.rotation_axis_angle = (math.radians(deg), *axis)


def _detail_cam(name, loc, tgt, lens_mm=70):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens_mm
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    direction = Vector(tgt) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


def anim_audit():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    assert len(arms) == 1, f"FATAL: expected ONE armature, got {len(arms)}"
    arm = arms[0]
    _ENV = ("VoidCrack", "Void", "Env", "Ground", "Floor")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"
              and not any(t in o.name for t in _ENV)]
    for m in sorted(meshes, key=lambda o: o.name):
        skinned = any(mo.type == "ARMATURE" and mo.object == arm
                      for mo in m.modifiers)
        chain, bone_par = m, None
        while chain is not None:
            if chain.parent == arm:
                bone_par = chain.parent_bone or "(object)"
                break
            chain = chain.parent
        bad = [mo.type for mo in m.modifiers if mo.type in
               ("CLOTH", "SOFT_BODY", "OCEAN", "EXPLODE", "FLUID")]
        print(f"[f r5]  {m.name}: verts={len(m.data.vertices)} "
              f"skinned={skinned} bone_parent={bone_par} sim={bad}")
        assert not bad, f"FATAL: sim modifier on {m.name}"
        assert skinned or bone_par is not None, \
            f"FATAL: {m.name} not attached to armature"
        assert "cape" not in m.name.lower(), f"FATAL: cape mesh {m.name}"
    body = bpy.data.objects.get("Godwyn_Body")
    assert body is not None and body.data.shape_keys, \
        "FATAL: Godwyn_Body shape keys missing"
    keys = [k.name for k in body.data.shape_keys.key_blocks]
    print(f"[f r5] SHAPE KEYS ({len(keys)}): {keys}")
    return arm, body


def main():
    scene = bpy.context.scene
    dev_type = G.enable_gpu(prefer_optix=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpus = [d for d in prefs.devices if d.use and d.type in ("OPTIX", "CUDA")]
    assert dev_type in ("OPTIX", "CUDA") and gpus, "FATAL: no GPU enabled"
    print(f"[f r5] GPU OK: {dev_type} — " + ", ".join(d.name for d in gpus))

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
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out) and os.path.getsize(out) > 1024, \
            f"FATAL: render missing: {out}"
        print(f"[f r5] wrote {out} ({os.path.getsize(out)//1024} KB)")

    shoot(_pick(_FULL_CANDIDATES), "f_r5_full.png", 1280, 1600)
    shoot("Cam_Face", "f_r5_face.png", 1280, 1280)
    _detail_cam("Cam_F5_Torso", (-2.2, -3.0, 2.35), (0.0, 0.0, 2.15), 60)
    shoot("Cam_F5_Torso", "f_r5_torso.png", 1400, 1400)
    _detail_cam("Cam_F5_Tabard", (0.9, -4.2, 1.05), (0.0, 0.0, 0.85), 55)
    shoot("Cam_F5_Tabard", "f_r5_tabard.png", 1400, 1500)

    # deform test: mild natural pose + expression blendshape
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    _pose_rotate(arm, "upper_arm.R", (0, 1, 0), 45.0)
    _pose_rotate(arm, "forearm.R", (1, 0, 0), -40.0)
    _pose_rotate(arm, "spine.01", (0, 0, 1), 12.0)
    _pose_rotate(arm, "thigh.L", (1, 0, 0), -25.0)
    _pose_rotate(arm, "shin.L", (1, 0, 0), 35.0)
    _pose_rotate(arm, "head", (0, 0, 1), -8.0)
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
    moved = sum(1 for i, v in enumerate(kb.data)
                if (v.co - basis.data[i].co).length > 1e-6)
    print(f"[f r5] blendshape '{kb.name}': {moved} verts moved")
    assert moved > 0, "FATAL: blendshape has zero deltas"

    shoot(_pick(_DEFORM_CANDIDATES), "f_r5_deform.png", 1280, 1600)
    print("[f r5] fixer verification renders complete (scene NOT saved).")


if __name__ == "__main__":
    main()
