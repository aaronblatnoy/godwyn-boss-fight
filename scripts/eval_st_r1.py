"""
eval_st_r1.py — UNCOMPROMISING evaluator round 1 for st_sword + st_feet.

Opens models/godwyn_st_feet.blend and:
  A. Diagnostics: sword object separate? parent? bone count? materials?
     toe yaw angles, sword-vs-hand proximity/clipping probe.
  B. Static EEVEE renders: full body (front + 3/4), hand+sword close-ups,
     feet shots.
  C. Deform test pose: raise sword arm, turn spine, left-leg step, gentle
     sweep of phys_* robe/cape chains -> renders (front, 3/4, back).

Headless: blender --background --python ~/godwyn-boss-fight/scripts/eval_st_r1.py 2>&1
"""
import bpy
import os
import math
from mathutils import Vector, Matrix, kdtree

REPO = os.path.expanduser("~/godwyn-boss-fight")
OUT = "/tmp/eval_st_r1"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_st_feet.blend"))

scn = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")

print("=== A. DIAGNOSTICS ===")
print(f"objects: {[o.name + ':' + o.type for o in bpy.data.objects]}")
nb = len(arm.data.bones)
nphys = sum(1 for b in arm.data.bones if b.name.startswith("phys_"))
print(f"bones={nb} phys={nphys} char1_vgroups={len(char1.vertex_groups)}")
if sword:
    print(f"sword: verts={len(sword.data.vertices)} parent={sword.parent.name if sword.parent else None} "
          f"parent_type={sword.parent_type} parent_bone={getattr(sword, 'parent_bone', '')}")
    print(f"sword mods={[m.type for m in sword.modifiers]} vgroups={len(sword.vertex_groups)}")
    bb = [sword.matrix_world @ Vector(c) for c in sword.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    print(f"sword world bbox lo={tuple(round(v,2) for v in lo)} hi={tuple(round(v,2) for v in hi)}")
else:
    print("!!! NO Godwyn_Sword OBJECT")

for m in bpy.data.materials:
    if m.users:
        print(f"material: {m.name}")

pbs = arm.pose.bones
for side in ("Left", "Right"):
    pb = pbs[side + "ToeBase"]
    d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
    print(f"[{side}] toe yaw {math.degrees(math.atan2(d.x, -d.y)):+.1f} deg out-from-forward (char faces -Y)")

# hand-vs-sword proximity: evaluated char1 verts near RightHand vs sword verts
hand_head = arm.matrix_world @ pbs["RightHand"].head
hand_tail = arm.matrix_world @ pbs["RightHand"].tail
print(f"RightHand head={tuple(round(v,3) for v in hand_head)} tail={tuple(round(v,3) for v in hand_tail)}")
if sword:
    ev_char = char1.evaluated_get(dg())
    hand_pts = [char1.matrix_world @ v.co for v in ev_char.data.vertices
                if (char1.matrix_world @ v.co - hand_head).length < 0.28]
    kd = kdtree.KDTree(len(hand_pts))
    for i, p in enumerate(hand_pts):
        kd.insert(p, i)
    kd.balance()
    dists = []
    for v in sword.data.vertices:
        w = sword.matrix_world @ v.co
        if (w - hand_head).length < 0.45:
            hit = kd.find(w)
            if hit[0] is not None:
                dists.append(hit[2])
    if dists:
        dists.sort()
        print(f"sword-verts near hand: n={len(dists)} min_dist_to_hand_skin={dists[0]*1000:.1f}mm "
              f"p5={dists[len(dists)//20]*1000:.1f}mm")
    else:
        print("!!! no sword verts within 0.45m of RightHand — sword not in hand?")

# ---------- render setup ----------
eng = None
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = e
        eng = e
        break
    except Exception:
        pass
print(f"engine={eng}")
scn.render.resolution_x = 1024
scn.render.resolution_y = 1280
scn.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("Wv")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.04, 0.04, 0.05, 1)
scn.world = world
for nm, en, col, rot in (("Key", 5.0, (1.0, 0.93, 0.72), (50, 0, 35)),
                         ("Fill", 1.8, (0.7, 0.8, 1.0), (55, 0, -130)),
                         ("Rim", 2.5, (1.0, 0.85, 0.5), (20, 0, 180))):
    li = bpy.data.objects.new(nm, bpy.data.lights.new(nm, 'SUN'))
    li.data.energy = en
    li.data.color = col
    li.rotation_euler = tuple(math.radians(a) for a in rot)
    scn.collection.objects.link(li)
cam = bpy.data.objects.new("EvalCam", bpy.data.cameras.new("EvalCam"))
scn.collection.objects.link(cam)
scn.camera = cam


def shoot(name, target, dist, elev, azim, lens=50):
    cam.data.lens = lens
    el, a = math.radians(elev), math.radians(azim)
    cam.location = Vector(target) + Vector((dist * math.cos(el) * math.sin(a),
                                            -dist * math.cos(el) * math.cos(a),
                                            dist * math.sin(el)))
    d = (Vector(target) - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scn.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {name}")


bb = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
zmax = max(v.z for v in bb)
mid = Vector((0, -0.2, zmax * 0.52))
print(f"char zmax={zmax:.2f}")

print("=== B. STATIC RENDERS ===")
shoot("01_full_front.png", mid, zmax * 1.9, 8, 0, 45)
shoot("02_full_3q.png", mid, zmax * 1.9, 8, 40, 45)
hand_t = (hand_head + hand_tail) / 2
shoot("03_hand_sword_a.png", hand_t, 1.0, 8, 25, 65)
shoot("04_hand_sword_b.png", hand_t, 1.0, 5, -50, 65)
if sword:
    sw_mid = (Vector((min(v.x for v in bb), 0, 0)) * 0)  # placeholder
    sbb = [sword.matrix_world @ Vector(c) for c in sword.bound_box]
    sw_c = sum(sbb, Vector()) / 8
    shoot("05_sword_full.png", sw_c, 2.6, 5, 30, 50)
shoot("06_feet_front.png", Vector((0, -0.42, 0.12)), 1.9, 6, 0, 60)
shoot("07_feet_3q.png", Vector((0, -0.38, 0.12)), 2.0, 10, 35, 55)

print("=== C. DEFORM TEST POSE ===")


def rot_world(name, axis, deg):
    pb = pbs.get(name)
    if pb is None:
        print(f"  !! missing bone {name}")
        return
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    head = arm.matrix_world @ pb.head
    M = Matrix.Translation(head) @ R @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ M @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()


# raise sword arm (char faces -Y; +X is char's left screen-right? keep world axes)
rot_world("RightShoulder", 'Y', -10)
rot_world("RightArm", 'X', -55)      # swing up-forward
rot_world("RightArm", 'Y', -20)
rot_world("RightForeArm", 'X', -25)
# spine turn
rot_world("Spine", 'Z', 18)
rot_world("Spine1", 'Z', 10)
rot_world("Neck", 'Z', -12)
# left leg step forward (-Y)
rot_world("LeftUpLeg", 'X', -30)
rot_world("LeftLeg", 'X', 20)
rot_world("RightUpLeg", 'X', 8)
# robe/cape phys chain sweep: gentle per-link backward+side sweep
n_swept = 0
for pb in pbs:
    if pb.name.startswith("phys_"):
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler.x += math.radians(6.0)
        pb.rotation_euler.y += math.radians(2.0)
        n_swept += 1
bpy.context.view_layer.update()
print(f"swept {n_swept} phys bones")

shoot("08_pose_front.png", mid, zmax * 1.9, 8, -15, 45)
shoot("09_pose_3q.png", mid, zmax * 1.9, 8, 45, 45)
shoot("10_pose_back.png", mid, zmax * 1.9, 8, 170, 45)
hh = arm.matrix_world @ pbs["RightHand"].head
shoot("11_pose_hand_sword.png", hh, 1.2, 12, 30, 60)
shoot("12_pose_legs.png", Vector((0, -0.35, zmax * 0.22)), 2.6, 6, 25, 50)

print("EVAL_ST_R1 DONE")
