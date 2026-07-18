"""
eval_fixer_r2.py — fixer round-2 verification: load godwyn_face.blend, render
the SAME shots as eval_r1 (full/hand/face + posed deform test) to /tmp/eval_r2,
and print a quantitative TEAR METRIC (posed edge stretch vs rest).
"""
import bpy, os, math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND_IN = os.path.join(REPO, "models", "godwyn_face.blend")
OUT = "/tmp/eval_r2"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")
assert arm and body, "missing Armature/char1"
me = body.data
print(f"[eval2] body verts={len(me.vertices)} mats={[m.name for m in me.materials]} "
      f"uvs={len(me.uv_layers)} bones={len(arm.data.bones)} "
      f"sword={'OK verts='+str(len(sword.data.vertices)) if sword else 'MISSING'}")
if sword:
    print(f"[eval2] sword parent_bone={sword.parent_bone}")

awm = arm.matrix_world
rh_head = awm @ arm.data.bones["RightHand"].head_local

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1200
scene.render.resolution_y = 1500
world = scene.world or bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.24, 0.26, 0.32, 1.0)
    bg.inputs[1].default_value = 1.3
for nm in ("PrevSun", "PrevFill", "PrevRim", "PrevCam", "ESun", "EFill", "ECam"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
sun = bpy.data.objects.new("ESun", bpy.data.lights.new("ESun", 'SUN'))
sun.data.energy = 5.5
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(52), 0, math.radians(-35))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("EFill", bpy.data.lights.new("EFill", 'AREA'))
fill.data.energy = 500
fill.data.size = 5.0
fill.location = Vector((1.5, -3.0, 2.2))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("ECam", bpy.data.cameras.new("ECam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(frm, to):
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat('-Z', 'Y').to_euler()

def shot(name, frm, to, lens):
    cam.data.lens = lens
    aim(Vector(frm), Vector(to))
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print(f"[eval2] rendered {scene.render.filepath}")

gc = rh_head
shot("a_full", (0, -4.6, 1.6), (0, 0, 1.55), 42)
shot("a_full_34", (-2.8, -3.8, 1.7), (-0.2, 0, 1.5), 40)
shot("b_hand", (gc.x - 0.45, gc.y - 0.6, gc.z + 0.1), (gc.x, gc.y, gc.z), 55)
shot("b_hand_side", (gc.x - 0.75, gc.y + 0.05, gc.z), (gc.x, gc.y, gc.z), 55)
fc = Vector((0.0, -0.42, 2.99))
shot("c_face", (fc.x, fc.y - 0.95, fc.z + 0.02), fc, 85)
shot("c_face_34", (fc.x - 0.6, fc.y - 0.78, fc.z + 0.04), fc, 85)

# rest edge lengths BEFORE posing
rest_len = {}
for e in me.edges:
    a, b = e.vertices
    rest_len[e.index] = (me.vertices[a].co - me.vertices[b].co).length

def pose(name, deg):
    if name not in arm.pose.bones:
        print(f"[eval2] WARN no bone {name}")
        return
    pb = arm.pose.bones[name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in deg)
    print(f"[eval2] posed {name} {deg}")

pose("RightArm", (0, 0, -55))
pose("RightForeArm", (-40, 0, 0))
pose("Spine", (0, 0, 22))
bpy.context.view_layer.update()

# tear metric on the DEFORMED mesh
dg = bpy.context.evaluated_depsgraph_get()
me_ev = body.evaluated_get(dg).to_mesh()
n3 = n10 = 0
worst = 0.0
for e in me_ev.edges:
    a, b = e.vertices
    r = rest_len.get(e.index)
    if not r or r < 1e-6:
        continue
    s = (me_ev.vertices[a].co - me_ev.vertices[b].co).length / r
    worst = max(worst, s)
    if s > 3.0:
        n3 += 1
    if s > 10.0:
        n10 += 1
print(f"[eval2] TEAR METRIC: edges={len(me_ev.edges)} stretch>3x={n3} "
      f">10x={n10} worst={worst:.1f}x")
body.evaluated_get(dg).to_mesh_clear()

shot("d_posed_full", (0, -4.6, 1.6), (0, 0, 1.55), 42)
shot("d_posed_hand", (gc.x - 0.5, gc.y - 0.7, gc.z + 0.3), (gc.x, gc.y, gc.z + 0.2), 50)
shot("d_posed_34", (-2.9, -3.6, 1.8), (-0.2, 0, 1.5), 40)
print("[eval2] DONE")
