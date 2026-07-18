"""
eval_r6_render.py — Round 6 beauty eval renders (EEVEE) of godwyn_face.blend.
Shots: (a) full body, (b) hand+sword close-up, (c) face close-up,
       (d) posed deform test (raise sword arm via RightArm/RightForeArm, turn Spine).
Outputs to /tmp/eval_r6/.
"""
import bpy, os, math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_face.blend")
OUT = "/tmp/eval_r6"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")
print(f"[eval] body={'ok' if body else 'MISS'} arm={'ok' if arm else 'MISS'} "
      f"sword={'ok' if sword else 'MISS'}")

scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
scene.render.film_transparent = False

world = scene.world or bpy.data.worlds.new("W")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.22, 0.24, 0.30, 1.0)
    bg.inputs[1].default_value = 1.2

for nm in ("ESun", "EFill", "ECam"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
sun = bpy.data.objects.new("ESun", bpy.data.lights.new("ESun", 'SUN'))
sun.data.energy = 4.5
sun.rotation_euler = (math.radians(58), 0, math.radians(-35))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("EFill", bpy.data.lights.new("EFill", 'AREA'))
fill.data.energy = 400
fill.data.size = 3.0
fill.location = Vector((1.2, -2.4, 2.6))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("ECam", bpy.data.cameras.new("ECam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(frm, to, lens):
    cam.data.lens = lens
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat('-Z', 'Y').to_euler()

def render(name):
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[eval] wrote", scene.render.filepath)

# find head / hand locations from mesh bounds
face_c = Vector((0.0, -0.40, 2.99))

# (a) full body
aim(Vector((0, -5.2, 1.6)), Vector((0, 0, 1.55)), 42)
render("a_full")

# (b) hand + sword close-up. Sword planted at LEFT side (viewer). Locate sword.
if sword:
    pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
    gx = sum(p.x for p in pts)/len(pts)
    # grip is near the top of the sword cluster
    top = max(p.z for p in pts)
    grip = Vector((gx, -0.55, top - 0.30))
    aim(grip + Vector((0.0, -1.4, 0.15)), grip, 70)
    render("b_hand_sword")
else:
    render("b_hand_sword")

# (c) face close-up
aim(face_c + Vector((0, -0.95, 0.02)), face_c, 85)
render("c_face")

# (d) posed deform test: raise sword arm + turn spine
def setrot(bone, deg):
    pb = arm.pose.bones.get(bone)
    if not pb:
        print("[eval] missing bone", bone); return
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in deg)

# clear any pose first
for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = (0, 0, 0)
setrot("RightArm", (0, 0, -50))
setrot("RightForeArm", (0, 0, -35))
setrot("Spine", (0, 0, 22))
bpy.context.view_layer.update()
aim(Vector((0, -5.2, 1.6)), Vector((0, 0, 1.55)), 42)
render("d_posed")

print("[eval] DONE")
