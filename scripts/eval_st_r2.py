"""
eval_st_r2.py — Round 2 UNCOMPROMISING evaluator renders + QA.

Loads models/godwyn_st_feet.blend (final of st_sword -> st_sword_albedo ->
st_feet chain). Prints structural QA (sword separate/bone-parented, toe yaw,
bone count, materials), then EEVEE renders:
  rest:  full front, full 3q, hand+sword x3, feet front/low3q/top
  posed: raise sword arm 70deg, spine turn 25deg, left leg step, mild phys
         chain swing -> full front, 3q, back (robe), hand closeup.
Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/eval_st_r2.py 2>&1
"""
import bpy
import os
import math
from mathutils import Vector, Matrix

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_st_feet.blend")
OUT = "/tmp/eval_st_r2"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]

# ── STRUCTURAL QA ──────────────────────────────────────────────────────────
sword = bpy.data.objects.get("Godwyn_Sword")
if sword is None:
    print("[QA] FAIL: no Godwyn_Sword object")
else:
    print(f"[QA] sword: verts={len(sword.data.vertices)} "
          f"parent={sword.parent.name if sword.parent else None} "
          f"parent_type={sword.parent_type} parent_bone={sword.parent_bone} "
          f"mods={[m.type for m in sword.modifiers]}")
n_bones = len(arm.data.bones)
n_phys = sum(1 for b in arm.data.bones if b.name.startswith("phys_"))
print(f"[QA] bones={n_bones} phys={n_phys} char1_vgroups={len(char1.vertex_groups)}")
print(f"[QA] materials char1={[m.name for m in char1.data.materials]} "
      f"sword={[m.name for m in sword.data.materials] if sword else []}")
imgs = [(i.name, i.size[0]) for i in bpy.data.images if i.size[0]]
print(f"[QA] images={imgs}")

bpy.context.view_layer.update()
mw = arm.matrix_world
for tb in ("LeftToeBase", "RightToeBase"):
    pb = arm.pose.bones.get(tb)
    if pb:
        d = (mw @ pb.tail) - (mw @ pb.head)
        ang = math.degrees(math.atan2(abs(d.x), -d.y))  # 0 = dead forward (-Y)
        print(f"[QA] {tb}: dir=({d.x:.3f},{d.y:.3f},{d.z:.3f}) out-angle={ang:.1f} deg")
for fb in ("LeftFoot", "RightFoot"):
    pb = arm.pose.bones.get(fb)
    if pb:
        print(f"[QA] {fb} pose rot: {tuple(round(math.degrees(a),1) for a in pb.rotation_euler)} mode={pb.rotation_mode}")

pbs = arm.pose.bones
rh = mw @ pbs["RightHand"].head

# ── RENDER SETUP ───────────────────────────────────────────────────────────
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except Exception:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("Wv")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
scene.world = world
sun = bpy.data.objects.new("SunE", bpy.data.lights.new("SunE", 'SUN'))
sun.data.energy = 4.0
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("FillE", bpy.data.lights.new("FillE", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("CamE", bpy.data.cameras.new("CamE"))
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

# ── REST RENDERS ───────────────────────────────────────────────────────────
shoot("e_full_front.png", Vector((0, 0, 1.6)), 8.0, 5, 0, 35)
shoot("e_full_3q.png", Vector((0, 0, 1.6)), 8.0, 8, -40, 35)
shoot("e_hand_a.png", rh, 1.2, 10, -60, 55)
shoot("e_hand_b.png", rh, 1.2, -10, -140, 55)
shoot("e_hand_wide.png", rh + Vector((0, -0.2, -0.4)), 2.4, 5, -50, 40)
feet_c = Vector((0.0, -0.30, 0.12))
shoot("e_feet_front.png", feet_c, 2.2, 8, 0, 55)
shoot("e_feet_low3q.png", feet_c, 2.4, 4, -35, 55)
shoot("e_feet_top.png", Vector((0.0, -0.35, 0.05)), 2.6, 70, 0, 45)

# ── DEFORM TEST POSE ───────────────────────────────────────────────────────
def rot_world(name, axis, deg):
    bpy.context.view_layer.update()
    pb = pbs[name]
    M = pb.matrix.copy()  # armature space (~world; mw is identity-ish)
    head = M.to_translation()
    ax = (mw.inverted().to_3x3() @ Vector(axis)).normalized()
    R = Matrix.Rotation(math.radians(deg), 4, ax)
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ M

rot_world("RightArm", (1, 0, 0), -70)      # raise sword arm forward-up
rot_world("RightForeArm", (1, 0, 0), -15)
rot_world("Spine01", (0, 0, 1), 25)        # spine turn
rot_world("LeftUpLeg", (1, 0, 0), -30)     # leg step forward
rot_world("LeftLeg", (1, 0, 0), 20)        # knee bend
# mild swing on phys chain roots (robe/cape flow via chains)
roots = [b.name for b in arm.data.bones
         if b.name.startswith("phys_") and
         (b.parent is None or not b.parent.name.startswith("phys_"))]
print(f"[QA] phys roots={len(roots)}")
for rn in roots:
    try:
        rot_world(rn, (1, 0, 0), 12)
    except Exception as e:
        print(f"  phys swing skip {rn}: {e}")
bpy.context.view_layer.update()

rh2 = mw @ pbs["RightHand"].head
shoot("e_pose_front.png", Vector((0, 0, 1.5)), 8.5, 5, 0, 35)
shoot("e_pose_3q.png", Vector((0, 0, 1.5)), 8.5, 8, -45, 35)
shoot("e_pose_back.png", Vector((0, 0, 1.4)), 8.5, 8, 175, 35)
shoot("e_pose_hand.png", rh2, 1.4, 5, -60, 50)
shoot("e_pose_legs.png", Vector((0.0, -0.15, 0.6)), 3.5, 5, -30, 45)
print("EVAL_ST_R2 DONE")
