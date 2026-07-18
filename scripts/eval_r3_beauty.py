import bpy, os, math
from mathutils import Vector, Euler

HOME = os.path.expanduser("~")
BLEND = f"{HOME}/godwyn-boss-fight/models/godwyn_face.blend"
OUT = "/tmp/eval_r3"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
arm = bpy.data.objects.get("Armature")
char = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")
print("[eval] char", char, "arm", arm, "sword", sword)

# ---- EEVEE
eng = None
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = e; eng = e; break
    except Exception:
        pass
print("[eval] engine", eng)
ee = scn.eevee
for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_ssr", True),
                  ("use_gtao", True)):
    if hasattr(ee, attr):
        try: setattr(ee, attr, val)
        except Exception: pass
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 96

scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
try: scn.view_settings.look = "AgX - Punchy"
except Exception: pass

# ---- world
world = scn.world or bpy.data.worlds.new("W")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.16, 0.17, 0.22, 1.0)
    bg.inputs[1].default_value = 1.0

def clear_lights():
    for nm in ("Sun", "Fill", "Rim"):
        o = bpy.data.objects.get(nm)
        if o: bpy.data.objects.remove(o, do_unlink=True)

def add_lights(center):
    clear_lights()
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(52), 0, math.radians(-34))
    scn.collection.objects.link(sun)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'AREA'))
    fill.data.energy = 300; fill.data.size = 3.0
    fill.location = center + Vector((1.2, -2.2, 0.8))
    scn.collection.objects.link(fill)
    rim = bpy.data.objects.new("Rim", bpy.data.lights.new("Rim", 'AREA'))
    rim.data.energy = 400; rim.data.size = 2.0
    rim.location = center + Vector((-1.5, 2.0, 2.0))
    scn.collection.objects.link(rim)

def bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

cam = bpy.data.objects.get("EvalCam") or bpy.data.objects.new("EvalCam", bpy.data.cameras.new("EvalCam"))
if cam.name not in scn.collection.objects:
    scn.collection.objects.link(cam)
scn.camera = cam

def aim(frm, to):
    cam.location = frm
    cam.rotation_euler = (Vector(to) - Vector(frm)).to_track_quat('-Z', 'Y').to_euler()

def render(name, res=(1000, 1250)):
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[eval] wrote", scn.render.filepath)

bmn, bmx = bbox(char)
ctr = (bmn + bmx) / 2
top = bmx.z
print("[eval] char bbox", tuple(round(c,2) for c in bmn), tuple(round(c,2) for c in bmx))

# (a) full body
add_lights(ctr)
cam.data.lens = 50
aim(Vector((0.0, -6.2, top*0.55)), Vector((0, 0, top*0.5)))
render("a_full_body")

# (c) face close
head_c = Vector((0.0, -0.42, top - 0.35))
add_lights(head_c)
cam.data.lens = 85
aim(head_c + Vector((0.18, -1.15, 0.05)), head_c)
render("c_face_front", (1024, 1024))
aim(head_c + Vector((-0.7, -0.85, 0.05)), head_c)
render("c_face_34", (1024, 1024))

# (b) hand + sword close
if sword:
    smn, smx = bbox(sword)
    sc = (smn + smx) / 2
    lh = arm.matrix_world @ arm.data.bones["LeftHand"].head_local
    grip_c = lh
    add_lights(grip_c)
    cam.data.lens = 70
    aim(grip_c + Vector((0.9, -1.4, 0.2)), grip_c)
    render("b_hand_sword", (1024, 1024))
    # sword full so we can see the whole blade/object
    add_lights(sc)
    cam.data.lens = 40
    aim(Vector((1.4, -4.0, sc.z)), sc)
    render("b_sword_full", (1024, 1024))

# (d) posed deform test: raise right arm, turn spine
def setpose(bone, eul_deg):
    pb = arm.pose.bones.get(bone)
    if not pb:
        print("[eval] MISSING bone", bone); return
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = Euler([math.radians(a) for a in eul_deg], 'XYZ')

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
setpose("Spine", (0, 0, 25))
setpose("Spine01", (0, 0, 12))
setpose("RightArm", (0, -55, -35))
setpose("RightForeArm", (0, -50, 0))
setpose("RightHand", (0, -15, 0))
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

add_lights(ctr)
cam.data.lens = 50
aim(Vector((1.0, -6.2, top*0.55)), Vector((0, 0, top*0.5)))
render("d_posed_deform")
# closeup of the posed right shoulder/arm to check deformation
rs = arm.matrix_world @ arm.data.bones["RightArm"].head_local
add_lights(rs)
cam.data.lens = 70
aim(rs + Vector((1.6, -2.4, 0.3)), rs)
render("d_posed_arm_close", (1024, 1024))

print("[eval] DONE")
