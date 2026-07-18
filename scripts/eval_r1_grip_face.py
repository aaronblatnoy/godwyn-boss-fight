"""
eval_r1_grip_face.py — evaluator render: load godwyn_face.blend and produce
(a) full-body, (b) hand+sword close-up, (c) face close-up, (d) posed deform test.
EEVEE, headless. Writes to /tmp/eval_r1.
"""
import bpy, os, math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND_IN = os.path.join(REPO, "models", "godwyn_face.blend")
OUT = "/tmp/eval_r1"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")
print(f"[eval] arm={arm} body={body} sword={sword}")
assert arm and body, "missing Armature/char1"
me = body.data
print(f"[eval] body verts={len(me.vertices)} mats={[m.name for m in me.materials]} "
      f"uvs={len(me.uv_layers)} bones={len(arm.data.bones)} "
      f"sword={'OK verts='+str(len(sword.data.vertices)) if sword else 'MISSING'}")
if sword:
    print(f"[eval] sword parent={sword.parent} type={sword.parent_type} bone={sword.parent_bone} "
          f"mats={[m.name if m else None for m in sword.data.materials]} uvs={len(sword.data.uv_layers)}")

awm = arm.matrix_world
rh_head = awm @ arm.data.bones["RightHand"].head_local
head_j = awm @ arm.data.bones["Head"].head_local if "Head" in arm.data.bones else Vector((0,-0.4,2.85))
print(f"[eval] RightHand head world={tuple(round(c,3) for c in rh_head)} Head={tuple(round(c,3) for c in head_j)}")

# scene / lighting
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1200
scene.render.resolution_y = 1500
scene.render.film_transparent = False
world = scene.world or bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.16, 0.16, 0.19, 1.0)
    bg.inputs[1].default_value = 1.0
for nm in ("PrevSun","PrevFill","PrevCam","ESun","EFill","ECam"):
    ob = bpy.data.objects.get(nm)
    if ob: bpy.data.objects.remove(ob, do_unlink=True)
sun = bpy.data.objects.new("ESun", bpy.data.lights.new("ESun",'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(52), 0, math.radians(-35))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("EFill", bpy.data.lights.new("EFill",'AREA'))
fill.data.energy = 400; fill.data.size = 5.0
fill.location = Vector((1.5,-3.0,2.2))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("ECam", bpy.data.cameras.new("ECam"))
scene.collection.objects.link(cam); scene.camera = cam

def aim(frm,to):
    cam.location = frm
    cam.rotation_euler = (to-frm).to_track_quat('-Z','Y').to_euler()

def shot(name, frm, to, lens):
    cam.data.lens = lens
    aim(Vector(frm), Vector(to))
    scene.render.filepath = os.path.join(OUT, name+".png")
    bpy.ops.render.render(write_still=True)
    print(f"[eval] rendered {scene.render.filepath}")

# (a) full body
shot("a_full", (0,-4.6,1.6), (0,0,1.55), 42)
shot("a_full_34", (-2.8,-3.8,1.7), (-0.2,0,1.5), 40)
# (b) hand + sword close
gc = rh_head
shot("b_hand", (gc.x-0.45, gc.y-0.6, gc.z+0.1), (gc.x, gc.y, gc.z), 55)
shot("b_hand_side", (gc.x-0.75, gc.y+0.05, gc.z), (gc.x, gc.y, gc.z), 55)
# (c) face close
fc = Vector((0.0,-0.42,2.99))
shot("c_face", (fc.x, fc.y-0.95, fc.z+0.02), fc, 85)
shot("c_face_34", (fc.x-0.6, fc.y-0.78, fc.z+0.04), fc, 85)

# (d) posed deform test — raise right arm, turn spine
def pose(name, deg):
    if name not in arm.pose.bones:
        print(f"[eval] WARN no bone {name}"); return
    pb = arm.pose.bones[name]; pb.rotation_mode='XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in deg)
    print(f"[eval] posed {name} {deg}")
pose("RightArm", (0,0,-55))
pose("RightForeArm", (-40,0,0))
pose("Spine", (0,0,22))
if "Spine1" in arm.pose.bones: pose("Spine1", (0,0,12))
bpy.context.view_layer.update()
shot("d_posed_full", (0,-4.6,1.6), (0,0,1.55), 42)
shot("d_posed_hand", (gc.x-0.5, gc.y-0.7, gc.z+0.3), (gc.x, gc.y, gc.z+0.2), 50)
shot("d_posed_34", (-2.9,-3.6,1.8), (-0.2,0,1.5), 40)
print("[eval] DONE")
