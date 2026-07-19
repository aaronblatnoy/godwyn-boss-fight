"""
eval_st_r1b.py — UNCOMPROMISING evaluator renders, round 1 (post st_sword+st_feet).

Loads models/godwyn_st_feet.blend and renders (EEVEE):
  A. full body front + 3/4
  B. hand+sword close-ups (front / side / 3q)
  C. feet shots (front / low 3q / top-down)
  D. posed DEFORM TEST: raise sword arm overhead, turn spine, left-leg step
     -> full + robe/back shot to check phys chains flow & skinning integrity.
Also prints numeric QA: toe yaw angles, sword-to-fist distance, sword/hand
clipping probe (min dist between sword grip band and fist verts), material
check (GodwynGameMat images, gold/blue nodes).

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/eval_st_r1b.py 2>&1
"""
import bpy
import os
import math
from mathutils import Vector, Matrix, kdtree

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_st_feet.blend")
OUT = "/tmp/eval_st_r1b"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]
sword = bpy.data.objects.get("Godwyn_Sword")
print(f"[SCENE] armature={arm.name} bones={len(arm.data.bones)} "
      f"phys={sum(1 for b in arm.data.bones if b.name.startswith('phys_'))} "
      f"sword={'YES' if sword else 'MISSING'} "
      f"sword_parent={getattr(sword,'parent_bone',None) if sword else None}")

# ── NUMERIC QA ─────────────────────────────────────────────────────────────
pbs = arm.pose.bones

def toe_yaw(side):
    pb = pbs[side + "ToeBase"]
    d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
    return math.degrees(math.atan2(d.x, -d.y))

print(f"[TOE YAW] Left={toe_yaw('Left'):+.1f} deg  Right={toe_yaw('Right'):+.1f} deg "
      f"(+ = toward +X; splay-out is +L / -R)")

# fist center from evaluated mesh (RightHand-weighted verts near bone head)
dg = bpy.context.evaluated_depsgraph_get()
ev = char1.evaluated_get(dg)
ev_me = ev.to_mesh()
vgi = char1.vertex_groups.find("RightHand")
head_w = arm.matrix_world @ pbs["RightHand"].head
fist_pts = []
for v, vev in zip(char1.data.vertices, ev_me.vertices):
    for g in v.groups:
        if g.group == vgi and g.weight > 0.5:
            w = ev.matrix_world @ vev.co
            if (w - head_w).length < 0.30:
                fist_pts.append(w.copy())
            break
ev.to_mesh_clear()
fist_c = sum(fist_pts, Vector()) / len(fist_pts)
print(f"[FIST] n={len(fist_pts)} center={tuple(round(x,3) for x in fist_c)}")

sw_ws = [sword.matrix_world @ v.co for v in sword.data.vertices]
sw_c = sum(sw_ws, Vector()) / len(sw_ws)
# grip band = sword verts within 0.20 of fist center
kd = kdtree.KDTree(len(fist_pts))
for i, p in enumerate(fist_pts):
    kd.insert(p, i)
kd.balance()
near = [(w, kd.find(w)[2]) for w in sw_ws if (w - fist_c).length < 0.35]
if near:
    dmin = min(d for _, d in near)
    n_inside = sum(1 for _, d in near if d < 0.005)
    print(f"[GRIP QA] sword verts within 0.35 of fist: {len(near)}, "
          f"min dist to fist skin: {dmin*1000:.1f} mm, verts <5mm from skin: {n_inside}")
else:
    print("[GRIP QA] NO sword verts within 0.35 of the fist — sword not in hand!")
d_hilt = (fist_c - sw_c)
print(f"[SWORD] center={tuple(round(x,3) for x in sw_c)} "
      f"fist->swordcenter={tuple(round(x,3) for x in d_hilt)} |d|={d_hilt.length:.3f}")
for axn, i in (("X",0),("Y",1),("Z",2)):
    vals = [w[i] for w in sw_ws]
    print(f"[SWORD WORLD] {axn}: [{min(vals):.3f}, {max(vals):.3f}]")

mat = bpy.data.materials.get("GodwynGameMat")
if mat:
    imgs = [n.image.name for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
    print(f"[MAT] GodwynGameMat images={imgs}")
else:
    print("[MAT] GodwynGameMat MISSING")
print(f"[MATS] all={[m.name for m in bpy.data.materials]}")
print(f"[SWORD MATS] {[m.name for m in sword.data.materials] if sword else None}")

# ── RENDER SETUP (EEVEE) ───────────────────────────────────────────────────
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, target, dist, elev, azim, lens=50):
    cam.data.lens = lens
    el, a = math.radians(elev), math.radians(azim)
    off = Vector((dist * math.cos(el) * math.sin(a),
                  -dist * math.cos(el) * math.cos(a),
                  dist * math.sin(el)))
    cam.location = target + off
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")


# A. full body
shoot("a_full_front.png", Vector((0, 0, 1.6)), 8.0, 5, 0, 35)
shoot("a_full_3q.png", Vector((0, 0, 1.6)), 8.0, 8, -40, 35)
shoot("a_full_side.png", Vector((0, 0, 1.6)), 8.0, 5, -90, 35)

# B. hand + sword
shoot("b_hand_front.png", fist_c, 1.1, 10, -60, 55)
shoot("b_hand_side.png", fist_c, 1.1, -15, -140, 55)
shoot("b_hand_close.png", fist_c, 0.6, 5, -100, 70)
shoot("b_sword_3q.png", fist_c + Vector((-0.2, -0.3, -0.5)), 2.8, 8, -55, 40)

# C. feet
feet_c = Vector((0.0, -0.30, 0.12))
shoot("c_feet_front.png", feet_c, 2.2, 8, 0, 55)
shoot("c_feet_low3q.png", feet_c, 2.4, 4, -35, 55)
shoot("c_feet_top.png", Vector((0.0, -0.35, 0.05)), 2.6, 70, 0, 45)

# D. DEFORM TEST — raise sword arm, turn spine, left-leg step
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

def rot_bone_world(pb, axis, deg):
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    Aw = arm.matrix_world
    Mw = Aw @ pb.matrix
    T = Matrix.Translation(Mw.translation.copy())
    pb.matrix = Aw.inverted() @ (T @ R @ T.inverted() @ Mw)
    bpy.context.view_layer.update()

rot_bone_world(pbs["RightArm"], (1, 0, 0), 70)      # raise sword arm overhead-ish
rot_bone_world(pbs["RightForeArm"], (1, 0, 0), 15)
rot_bone_world(pbs["Spine01"], (0, 0, 1), 20)       # turn spine
rot_bone_world(pbs["LeftUpLeg"], (1, 0, 0), -35)    # left leg step forward
rot_bone_world(pbs["LeftLeg"], (1, 0, 0), 25)       # knee bend
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

shoot("d_pose_front.png", Vector((0, 0, 1.5)), 8.0, 8, -20, 35)
shoot("d_pose_3q.png", Vector((0, 0, 1.5)), 8.0, 10, -55, 35)
shoot("d_pose_back.png", Vector((0, 0, 1.4)), 8.0, 8, 160, 35)   # robe/cape chains
# posed hand: did the sword ride with the raised hand?
dg = bpy.context.evaluated_depsgraph_get()
head_w2 = arm.matrix_world @ pbs["RightHand"].head
print(f"[POSED] RightHand head={tuple(round(x,3) for x in head_w2)}")
sw_ws2 = [sword.matrix_world @ v.co for v in sword.data.vertices]
sw_c2 = sum(sw_ws2, Vector()) / len(sw_ws2)
print(f"[POSED] sword center={tuple(round(x,3) for x in sw_c2)} "
      f"dist to hand={ (sw_c2-head_w2).length :.3f}")
shoot("d_pose_hand.png", head_w2, 1.3, 10, -70, 55)
print("EVAL_ST_R1B DONE")
