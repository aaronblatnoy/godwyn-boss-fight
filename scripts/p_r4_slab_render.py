"""p_r4_slab_render.py — DIAGNOSTIC ONLY (never saves the blend).
Loads godwyn_sword.blend, deletes all char1 faces outside the z 1.40-2.00
slab, renders the slab from the grip camera + top-down, so the strand
cluster near the hand can be located in world space.
"""
import bpy
import bmesh
import math
import os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
OUT = "/tmp/sword_previews"
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_sword.blend"))
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
sword.hide_render = True
me = body.data
mwm = body.matrix_world
awm = arm.matrix_world
lh = awm @ arm.data.bones["LeftHand"].head_local

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
kill = [v for v in bm.verts if not (1.40 < (mwm @ v.co).z < 2.00)]
bmesh.ops.delete(bm, geom=kill, context='VERTS')
bm.to_mesh(me)
bm.free()
me.update()
print(f"[slab] kept {len(me.vertices)} verts in z 1.40-2.00")

# report vert clusters by rounded xy (5cm grid) so we can see where mass is
from collections import Counter
cnt = Counter()
for v in me.vertices:
    w = mwm @ v.co
    cnt[(round(w.x * 20) / 20, round(w.y * 20) / 20)] += 1
for (gx, gy), n in cnt.most_common(30):
    print(f"[slab] cell x={gx:+.2f} y={gy:+.2f} n={n}")

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
sun = bpy.data.objects.new("SlabSun", bpy.data.lights.new("SlabSun", 'SUN'))
sun.data.energy = 5.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("SlabCam", bpy.data.cameras.new("SlabCam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(frm, to):
    cam.location = Vector(frm)
    cam.rotation_euler = (Vector(to) - Vector(frm)).to_track_quat('-Z', 'Y').to_euler()

cam.data.lens = 60
aim(lh + Vector((0.55, -0.75, 0.30)), lh + Vector((0, 0, -0.08)))
scene.render.filepath = os.path.join(OUT, "slab_grip_cam.png")
bpy.ops.render.render(write_still=True)
cam.data.lens = 35
aim((0.2, -0.2, 4.5), (0.2, -0.2, 1.7))
scene.render.filepath = os.path.join(OUT, "slab_top.png")
bpy.ops.render.render(write_still=True)
print("[slab] DONE (blend NOT saved)")
