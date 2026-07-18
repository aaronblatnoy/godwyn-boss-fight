"""
p1_macro_check.py — MACRO DEFINITION form check (clay, raking light).

Loads models/godwyn_phase1.blend, temporarily overrides Godwyn_Body with a
matte clay material, hides armor/robe/sword (form check only — nothing is
saved), and renders:
  - p1_check_face.png   : tight 3/4 face closeup, hard raking key
  - p1_check_torso.png  : bare torso 3/4, raking key
  - p1_check_full.png   : full body front, raking key

READ these renders and critique: still a pill? soft face? If yes, adjust
GODWYN_DETAIL_TARGETS in 01_base_human.py and rebuild. Does NOT save the
.blend (pure inspection; INV-6 safe).

Usage:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p1_macro_check.py
"""
import bpy
import os
import sys
import math
import mathutils

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import lib_godwyn as G

WIP = os.path.expanduser("~/godwyn-boss-fight/renders/wip")


def main():
    gpu = G.enable_gpu()
    print(f"[p1_check] GPU backend: {gpu}")
    scene = bpy.context.scene

    body = bpy.data.objects["Godwyn_Body"]
    eyes = bpy.data.objects.get("Godwyn_Eyes")
    hair = bpy.data.objects.get("Godwyn_Hair")

    # verify blendshapes survived the pipeline (animatability gate)
    sk = body.data.shape_keys
    n_expr = 0 if sk is None else sum(
        1 for k in sk.key_blocks if k.name.startswith("Expr_"))
    print(f"[p1_check] expression blendshapes on Godwyn_Body: {n_expr}")
    assert n_expr >= 7, "FATAL: expression blendshapes missing"
    assert body.find_armature() is not None, "FATAL: body not skinned"

    # clay override (render-only; file not saved)
    clay = bpy.data.materials.new("_Mat_MacroCheckClay")
    clay.use_nodes = True
    p = clay.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (0.72, 0.68, 0.62, 1.0)
    p.inputs["Roughness"].default_value = 0.9
    body.data.materials.clear()
    body.data.materials.append(clay)

    # hide costume for the form read
    for name in ("Godwyn_Armor", "Godwyn_Robe", "Godwyn_Cape", "Godwyn_Sword",
                 "Godwyn_VoidCrack"):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_render = True
    if hair:
        hair.hide_render = True   # skull/face form check — hair occludes

    # kill existing lights; hard raking key + dim fill
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT":
            ob.hide_render = True

    def light(name, energy, size, loc):
        li = bpy.data.lights.new(name, "AREA")
        li.energy = energy
        li.size = size
        ob = bpy.data.objects.new(name, li)
        ob.location = loc
        scene.collection.objects.link(ob)
        d = mathutils.Vector((0, 0, 2.6)) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return ob

    light("_CheckKey", 700, 0.5, (3.4, -1.0, 3.2))     # hard raking from R
    light("_CheckFill", 40, 4.0, (-3.0, -3.5, 2.0))    # faint fill

    cam_data = bpy.data.cameras.new("_CheckCam")
    cam_data.lens = 100
    cam = bpy.data.objects.new("_CheckCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    # head centre from live geometry (top of body minus half a head)
    mw = body.matrix_world
    zmax = max((mw @ v.co).z for v in body.data.vertices)
    head_z = zmax - 0.17

    shots = [
        ("p1_check_face",  (0.60, -1.35, head_z), (0, 0.0, head_z - 0.04),
         1280, 1280, 85),
        ("p1_check_torso", (1.6, -3.2, 2.3), (0, 0, 2.15), 1280, 1280, 85),
        ("p1_check_full",  (0.9, -8.2, 1.7), (0, 0, 1.62), 900, 1500, 85),
    ]
    for name, loc, tgt, rx, ry, lens in shots:
        cam_data.lens = lens
        cam.location = loc
        d = mathutils.Vector(tgt) - mathutils.Vector(loc)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        G.configure_cycles(scene, samples=96, resolution_x=rx,
                           resolution_y=ry, use_denoiser=True)
        assert scene.cycles.device == "GPU", "INV-2 violated"
        out = os.path.join(WIP, name + ".png")
        G.render_to_path(out, scene)
        print(f"[p1_check] OK {out}")

    print("[p1_check] form-check renders complete (nothing saved)")


main()
