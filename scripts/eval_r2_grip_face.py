# eval_r2_grip_face.py — Round 2 beauty eval of the sword-grip + face fix.
# Opens models/godwyn_face.blend (final asset: sword fix + face fix baked in).
# Renders EEVEE: (a) full body, (b) hand+sword close, (c) face close, (d) posed deform.
import bpy, os, math
from mathutils import Vector, Euler

HOME = os.path.expanduser("~")
BLEND = f"{HOME}/godwyn-boss-fight/models/godwyn_face.blend"
OUT = "/tmp"

bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
meshes = [o for o in scn.objects if o.type == "MESH"]
char = max((o for o in meshes if len(o.vertex_groups) > 0), key=lambda o: len(o.data.vertices))
arm = next(o for o in scn.objects if o.type == "ARMATURE")
sword = next((o for o in meshes if "sword" in o.name.lower()), None)
print("[eval] char", char.name, "arm", arm.name, "sword", sword.name if sword else None)
print("[eval] all meshes:", [o.name for o in meshes])

eng = None
for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = e; eng = e; break
    except Exception:
        pass
assert eng
print("[eval] engine", eng)
ee = scn.eevee
for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_ssr", True),
                  ("use_gtao", True), ("use_bloom", True)):
    if hasattr(ee, attr):
        try: setattr(ee, attr, val)
        except Exception: pass
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 128

scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
try: scn.view_settings.look = "AgX - Punchy"
except Exception: pass

def bbox_of(obj, use_eval=False):
    o = obj
    if use_eval:
        dg = bpy.context.evaluated_depsgraph_get()
        o = obj.evaluated_get(dg)
        pts = [obj.matrix_world @ Vector(c) for c in o.bound_box]
    else:
        pts = [obj.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

bb_min, bb_max = bbox_of(char)
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z
print("[eval] H", round(Hgt, 3), "center", tuple(round(v, 3) for v in center))

# world
w = bpy.data.worlds.new("EWorld")
scn.world = w; w.use_nodes = True
wnt = w.node_tree; wnt.nodes.clear()
wbg = wnt.nodes.new("ShaderNodeBackground")
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wbg.inputs["Color"].default_value = (0.012, 0.013, 0.018, 1.0)
wbg.inputs["Strength"].default_value = 0.4
wnt.links.new(wbg.outputs["Background"], wout.inputs["Surface"])

floormat = bpy.data.materials.new("EFloor")
floormat.use_nodes = True
bsdf = floormat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.015, 0.016, 0.02, 1.0)
bsdf.inputs["Roughness"].default_value = 0.14
bpy.ops.mesh.primitive_plane_add(size=Hgt * 12, location=(center.x, center.y, bb_min.z))
floor = bpy.context.active_object
floor.data.materials.append(floormat)

def area(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size = size; d.color = color; d.energy = power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

def relight(center, bb_max, Hgt):
    tgt = (center.x, center.y, center.z + 0.12 * Hgt)
    Hs = Hgt
    area("RKey", (center.x - 1.0*Hs, center.y - 1.3*Hs, bb_max.z + 0.5*Hs), tgt, 1.1*Hs, (1.0,0.78,0.45), 220.0*Hs*Hs)
    area("RRimC", (center.x + 1.2*Hs, center.y + 1.0*Hs, center.z + 0.5*Hs), tgt, 0.7*Hs, (0.45,0.60,1.0), 130.0*Hs*Hs)
    area("RRimW", (center.x - 1.0*Hs, center.y + 1.1*Hs, bb_max.z + 0.2*Hs), tgt, 0.7*Hs, (1.0,0.6,0.25), 120.0*Hs*Hs)
    area("RFill", (center.x + 1.2*Hs, center.y - 1.1*Hs, center.z), tgt, 1.6*Hs, (0.4,0.5,0.85), 26.0*Hs*Hs)
relight(center, bb_max, Hgt)

def shoot(name, focal, look, fit_h, yaw_deg, path, res=(1080,1350)):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    scn.render.resolution_x, scn.render.resolution_y = res
    cd = bpy.data.cameras.new(name)
    cd.lens = focal; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36.0
    cam = bpy.data.objects.new(name, cd)
    scn.collection.objects.link(cam)
    fov = 2 * math.atan(36.0 / (2 * focal))
    dist = (fit_h / 2 * 1.18) / math.tan(fov / 2)
    yaw = math.radians(yaw_deg)
    off = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * dist
    cam.location = look + off + Vector((0, 0, 0.03 * Hgt))
    direc = (look - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[eval] wrote", path)

# (a) full body
shoot("CFull", 50, Vector((center.x, center.y, center.z)), Hgt, 20.0, f"{OUT}/eval_a_full.png")

# (b) hand + sword close-up. Find right hand bone head world pos.
arm_eval = arm
rh = arm.data.bones.get("RightHand")
rh_head_w = arm.matrix_world @ rh.head_local if rh else center
print("[eval] RightHand head world", tuple(round(v,3) for v in rh_head_w))
handlook = Vector((rh_head_w.x, rh_head_w.y, rh_head_w.z))
shoot("CHand", 85, handlook, 0.42 * Hgt, 32.0, f"{OUT}/eval_b_hand.png", res=(1200,1200))

# (c) face close-up
head_b = arm.data.bones.get("Head")
head_w = arm.matrix_world @ head_b.head_local if head_b else Vector((center.x, center.y, bb_min.z + 0.92*Hgt))
facelook = Vector((head_w.x, head_w.y, bb_min.z + 0.94*Hgt))
shoot("CFace", 105, facelook, 0.22 * Hgt, 12.0, f"{OUT}/eval_c_face.png", res=(1200,1400))

# (d) posed deform test
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
pb = arm.pose.bones
def rot(bone, x=0, y=0, z=0):
    b = pb.get(bone)
    if not b:
        print("[eval] MISSING bone", bone); return
    b.rotation_mode = "XYZ"
    b.rotation_euler = Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ")
rot("RightArm", x=-95, y=-10, z=-55)
rot("RightForeArm", x=-75, y=0, z=-20)
rot("RightHand", x=-15, z=-10)
rot("Spine", z=22, x=-8)
rot("Spine01", z=14)
rot("Spine02", z=10)
rot("LeftArm", x=-30, z=40)
rot("LeftForeArm", x=-50)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

bb_min2, bb_max2 = bbox_of(char, use_eval=True)
center2 = (bb_min2 + bb_max2) / 2
Hgt2 = bb_max2.z - bb_min2.z
relight(center2, bb_max2, Hgt2)
shoot("CPose", 50, Vector((center2.x, center2.y, center2.z)), Hgt2, 26.0, f"{OUT}/eval_d_pose.png")
print("[eval] DONE")
