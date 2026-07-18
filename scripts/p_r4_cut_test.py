"""p_r4_cut_test.py — DIAGNOSTIC ONLY (never saves).
Tests two cut predicates on godwyn_sword.blend and renders the grip camera
after each, to see which one removes the visible strand curtain.
  A: the fix_sword palm-cut predicate (as shipped)
  B: brutal cylinder: hdist<0.45 of LeftHand, z 1.30-2.02, no protections
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
OUT = "/tmp/sword_previews"
MODE = os.environ.get("CUT_MODE", "A")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_sword.blend"))
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
me = body.data
mwm = body.matrix_world
awm = arm.matrix_world
lh = awm @ arm.data.bones["LeftHand"].head_local
lf = awm @ arm.data.bones["LeftForeArm"].head_local
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
grip_top = max(c.z for c in sw_pts)
tip = min(sw_pts, key=lambda c: c.z)
top = max(sw_pts, key=lambda c: c.z)
axis_d = (top - tip).normalized()

def seg_d(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - a - ab * t).length

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
kill = []
CUT_Z = grip_top - 0.26
for bv in bm.verts:
    w = mwm @ bv.co
    if MODE == "A":
        if not (grip_top - 0.95 < w.z < CUT_Z):
            continue
        if math.hypot(w.x - lh.x, w.y - lh.y) > 0.32:
            continue
        if seg_d(w, lf, lh) < 0.10:
            continue
    else:
        if not (1.30 < w.z < 2.02):
            continue
        if math.hypot(w.x - lh.x, w.y - lh.y) > 0.45:
            continue
    kill.append(bv)
print(f"[cuttest] MODE={MODE} grip_top={grip_top:.3f} CUT_Z={CUT_Z:.3f} "
      f"lh={tuple(round(c,3) for c in lh)} lf={tuple(round(c,3) for c in lf)} "
      f"killing {len(kill)} verts")
bmesh.ops.delete(bm, geom=kill, context='VERTS')
bm.to_mesh(me)
bm.free()
me.update()

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
sun = bpy.data.objects.new("CtSun", bpy.data.lights.new("CtSun", 'SUN'))
sun.data.energy = 5.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("CtCam", bpy.data.cameras.new("CtCam"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 60
cam.location = lh + Vector((0.55, -0.75, 0.30))
cam.rotation_euler = ((lh + Vector((0, 0, -0.08))) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(OUT, f"cuttest_{MODE}.png")
bpy.ops.render.render(write_still=True)
print(f"[cuttest] rendered {scene.render.filepath} (blend NOT saved)")
