# r1_beauty_and_deform.py — Round 1 beauty evaluator renders.
#   (a) EEVEE beauty shot in a reflective dark-fantasy environment.
#   (b) POSED DEFORM TEST — sword-swing pose using real bone names.
# Opens the baked models/godwyn_gameasset.blend, NEVER re-bakes.
import bpy, os, math
from mathutils import Vector, Euler

HOME = os.path.expanduser("~")
BLEND = f"{HOME}/godwyn-boss-fight/models/godwyn_gameasset.blend"
OUT = "/tmp"

bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
char = next(o for o in scn.objects if o.type == "MESH" and len(o.vertex_groups) > 0)
arm = next(o for o in scn.objects if o.type == "ARMATURE")

# ---------------- engine + color
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = eng
        break
    except Exception:
        continue
print("[r1] engine", scn.render.engine)
scn.render.resolution_x, scn.render.resolution_y = 1080, 1350
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"
# enable screen-space reflections / raytracing where available
try:
    scn.eevee.use_raytracing = True
except Exception:
    pass
try:
    scn.eevee.use_ssr = True
    scn.eevee.use_ssr_refraction = True
except Exception:
    pass

# ---------------- bbox
def bbox():
    pts = [char.matrix_world @ Vector(c) for c in char.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx
bb_min, bb_max = bbox()
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z
print("[r1] H", round(Hgt, 3), "center", tuple(round(v, 3) for v in center))

# ---------------- reflective dark-fantasy environment: gradient world + floor
w = bpy.data.worlds.new("R1World")
scn.world = w
w.use_nodes = True
wnt = w.node_tree
wnt.nodes.clear()
wbg = wnt.nodes.new("ShaderNodeBackground")
grad = wnt.nodes.new("ShaderNodeTexGradient")
gmap = wnt.nodes.new("ShaderNodeMapping")
gtex = wnt.nodes.new("ShaderNodeTexCoord")
cramp = wnt.nodes.new("ShaderNodeValToRGB")
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(gtex.outputs["Generated"], gmap.inputs["Vector"])
wnt.links.new(gmap.outputs["Vector"], grad.inputs["Vector"])
wnt.links.new(grad.outputs["Fac"], cramp.inputs["Fac"])
wnt.links.new(cramp.outputs["Color"], wbg.inputs["Color"])
wnt.links.new(wbg.outputs["Background"], wout.inputs["Surface"])
cramp.color_ramp.elements[0].color = (0.006, 0.008, 0.014, 1.0)
cramp.color_ramp.elements[1].color = (0.05, 0.045, 0.06, 1.0)
wbg.inputs["Strength"].default_value = 0.35

# reflective wet-stone floor
floormat = bpy.data.materials.new("R1Floor")
floormat.use_nodes = True
fnt = floormat.node_tree
bsdf = fnt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.015, 0.016, 0.02, 1.0)
bsdf.inputs["Roughness"].default_value = 0.12
bsdf.inputs["Metallic"].default_value = 0.0
bpy.ops.mesh.primitive_plane_add(size=Hgt * 12, location=(center.x, center.y, bb_min.z))
floor = bpy.context.active_object
floor.data.materials.append(floormat)

# ---------------- dramatic lighting (gold key + cool rim + accent)
def area(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size = size; d.color = color; d.energy = power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    return o

tgt = (center.x, center.y, center.z + 0.12 * Hgt)
Hs = Hgt
area("RKey", (center.x - 1.0 * Hs, center.y - 1.3 * Hs, bb_max.z + 0.5 * Hs), tgt,
     1.1 * Hs, (1.0, 0.78, 0.45), 220.0 * Hs * Hs)
area("RRimC", (center.x + 1.2 * Hs, center.y + 1.0 * Hs, center.z + 0.5 * Hs), tgt,
     0.7 * Hs, (0.45, 0.60, 1.0), 130.0 * Hs * Hs)
area("RRimW", (center.x - 1.0 * Hs, center.y + 1.1 * Hs, bb_max.z + 0.2 * Hs), tgt,
     0.7 * Hs, (1.0, 0.6, 0.25), 120.0 * Hs * Hs)
area("RFill", (center.x + 1.2 * Hs, center.y - 1.1 * Hs, center.z), tgt,
     1.6 * Hs, (0.4, 0.5, 0.85), 26.0 * Hs * Hs)

# ---------------- camera helper
def shoot(name, focal, look_z, fit_h, yaw_deg, path):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal; cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36.0
    cam = bpy.data.objects.new(name, cd)
    scn.collection.objects.link(cam)
    look = Vector((center.x, center.y, look_z))
    fov = 2 * math.atan(36.0 / (2 * focal))
    dist = (fit_h / 2 * 1.18) / math.tan(fov / 2)
    yaw = math.radians(yaw_deg)
    off = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * dist
    cam.location = look + off + Vector((0, 0, 0.05 * Hgt))
    direc = (look - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[r1] wrote", path)

# ================= (a) BEAUTY SHOT (rest pose)
shoot("RCamBeauty", 50, center.z, Hgt, 22.0, f"{OUT}/r1_beauty.png")
shoot("RCamBust", 85, bb_min.z + 0.82 * Hgt, 0.45 * Hgt, 20.0, f"{OUT}/r1_bust.png")

# ================= (b) POSED DEFORM TEST
# apply a sword-swing / step pose using the real bone names
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
pb = arm.pose.bones

def rot(bone, x=0, y=0, z=0):
    b = pb.get(bone)
    if not b:
        print("[r1] MISSING bone", bone); return
    b.rotation_mode = "XYZ"
    b.rotation_euler = Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ")

# right arm raised into a diagonal sword swing (big shoulder + elbow)
rot("RightArm", x=-95, y=-10, z=-55)
rot("RightForeArm", x=-75, y=0, z=-20)
rot("RightHand", x=-15, z=-10)
rot("RightShoulder", z=-18)
# left arm counter-balance out
rot("LeftArm", x=-30, z=40)
rot("LeftForeArm", x=-50)
# spine torqued into the swing
rot("Spine", z=22, x=-8)
rot("Spine01", z=14)
rot("Spine02", z=10)
rot("neck", z=-14, x=6)
rot("Head", z=-10)
# a stepping stance
rot("RightUpLeg", x=28, z=-6)
rot("RightLeg", x=-40)
rot("LeftUpLeg", x=-24, z=8)
rot("LeftLeg", x=18)
rot("LeftFoot", x=15)

bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# re-fit bbox to the posed mesh
depsgraph = bpy.context.evaluated_depsgraph_get()
char_eval = char.evaluated_get(depsgraph)
pts = [char.matrix_world @ Vector(c) for c in char_eval.bound_box]
bb_min, bb_max = (Vector((min(p[i] for p in pts) for i in range(3))),
                  Vector((max(p[i] for p in pts) for i in range(3))))
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z

shoot("RCamPose", 50, center.z, Hgt, 28.0, f"{OUT}/r1_pose_deform.png")
# tighter shot on the right shoulder/arm to inspect joint deformation
shoot("RCamJoint", 80, bb_min.z + 0.72 * Hgt, 0.5 * Hgt, 40.0, f"{OUT}/r1_pose_joint.png")
print("[r1] DONE")
