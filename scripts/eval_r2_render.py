# eval_r2_render.py — evaluator renders from the BAKED gameasset (round 2).
#   (a) EEVEE beauty shot with a reflective dark-fantasy environment
#   (b) POSED DEFORM TEST — real-bone-name sword-swing pose
# Reads models/godwyn_gameasset.blend, does NOT rebake.
# Writes /tmp/eval_r2_beauty.png and /tmp/eval_r2_deform.png

import bpy, os, math
from mathutils import Vector, Euler

HOME = os.path.expanduser("~")
BLEND = f"{HOME}/godwyn-boss-fight/models/godwyn_gameasset.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
char = next(o for o in scn.objects if o.type == "MESH" and len(o.vertex_groups) > 0)
arm = next(o for o in scn.objects if o.type == "ARMATURE")
print(f"[e] char={char.name} arm={arm.name} bones={len(arm.data.bones)} mats={[m.name for m in char.data.materials]}")

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = eng; print(f"[e] engine={eng}"); break
    except Exception:
        continue
for attr in ("use_raytracing",):
    try:
        setattr(scn.eevee, attr, True)
    except Exception:
        pass
try:
    scn.eevee.use_ssr = True; scn.eevee.use_ssr_refraction = True
except Exception:
    pass

scn.render.image_settings.file_format = "PNG"
scn.render.resolution_x, scn.render.resolution_y = 1080, 1350
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"

def bbox(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi

bb_min, bb_max = bbox(char)
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z
print(f"[e] H={Hgt:.3f} center={tuple(round(v,3) for v in center)}")

# reflective dark-fantasy world
w = bpy.data.worlds.get("ER2World") or bpy.data.worlds.new("ER2World")
scn.world = w; w.use_nodes = True; wnt = w.node_tree; wnt.nodes.clear()
tc = wnt.nodes.new("ShaderNodeTexCoord")
grad = wnt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type = "SPHERICAL"
mapn = wnt.nodes.new("ShaderNodeMapping")
ramp = wnt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.004, 0.006, 0.012, 1.0)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.05, 0.09, 0.14, 1.0)
bg = wnt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = 0.6
wout = wnt.nodes.new("ShaderNodeOutputWorld")
wnt.links.new(tc.outputs["Generated"], mapn.inputs["Vector"])
wnt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
wnt.links.new(grad.outputs["Color"], ramp.inputs["Fac"])
wnt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

# reflective wet-stone floor
old = bpy.data.objects.get("ER2Floor")
if old: bpy.data.objects.remove(old, do_unlink=True)
bpy.ops.mesh.primitive_plane_add(size=Hgt*12, location=(center.x, center.y, bb_min.z))
floor = bpy.context.active_object; floor.name = "ER2Floor"
fm = bpy.data.materials.new("ER2FloorMat"); fm.use_nodes = True
b = fm.node_tree.nodes.get("Principled BSDF")
b.inputs["Base Color"].default_value = (0.01, 0.012, 0.02, 1.0)
b.inputs["Roughness"].default_value = 0.12
floor.data.materials.append(fm)

def area(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA"); d.size = size; d.color = color; d.energy = power
    o = bpy.data.objects.new(name, d); scn.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target)-Vector(loc)).normalized().to_track_quat("-Z","Y").to_euler()
    return o

tgt = (center.x, center.y, center.z + 0.1*Hgt); Hs = Hgt
area("ER2Key",  (center.x-1.1*Hs, center.y-1.2*Hs, bb_max.z+0.5*Hs), tgt, 1.0*Hs, (1.0,0.80,0.50), 200.0*Hs*Hs)
area("ER2RimC", (center.x+1.2*Hs, center.y+1.0*Hs, center.z+0.5*Hs), tgt, 0.6*Hs, (0.55,0.70,1.0), 120.0*Hs*Hs)
area("ER2RimG", (center.x-0.9*Hs, center.y+1.1*Hs, bb_max.z+0.2*Hs), tgt, 0.6*Hs, (1.0,0.62,0.25), 150.0*Hs*Hs)
area("ER2Fill", (center.x+1.3*Hs, center.y-1.0*Hs, center.z), tgt, 1.4*Hs, (0.30,0.45,0.85), 30.0*Hs*Hs)

def cam(name, look, fit, focal=50, yaw=20.0, zoff=0.03):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name); cd.lens = focal; cd.sensor_fit="VERTICAL"; cd.sensor_height=36.0
    c = bpy.data.objects.new(name, cd); scn.collection.objects.link(c)
    fov = 2*math.atan(36.0/(2*focal)); dist = (fit/2*1.18)/math.tan(fov/2)
    y = math.radians(yaw); offv = Vector((math.sin(y), -math.cos(y), 0.0))*dist
    c.location = look + offv + Vector((0,0,zoff*Hgt))
    c.rotation_euler = (look-c.location).normalized().to_track_quat("-Z","Y").to_euler()
    scn.camera = c; return c

# (a) beauty
cam("ER2CamBeauty", Vector((center.x, center.y, center.z)), Hgt, focal=50, yaw=20.0)
scn.render.filepath = "/tmp/eval_r2_beauty.png"
print("[e] rendering beauty..."); bpy.ops.render.render(write_still=True)
print("[e] wrote /tmp/eval_r2_beauty.png")

# (b) posed deform test
bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
def pose_bone(name, rx=0, ry=0, rz=0):
    pb = arm.pose.bones.get(name)
    if pb is None: print(f"[e] WARN no bone {name}"); return
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")

pose_bone("Spine", rx=8, rz=-18)
pose_bone("Spine01", rx=6, rz=-12)
pose_bone("Spine02", rx=4, rz=-8)
pose_bone("RightShoulder", rz=-20, rx=-10)
pose_bone("RightArm", rx=-70, ry=20, rz=-40)
pose_bone("RightForeArm", rx=-55, rz=-25)
pose_bone("RightHand", rx=-15)
pose_bone("LeftShoulder", rz=12)
pose_bone("LeftArm", rx=35, ry=-20, rz=30)
pose_bone("LeftForeArm", rx=-50)
pose_bone("neck", rx=-6, rz=8)
pose_bone("Head", rz=10)
pose_bone("RightUpLeg", rx=-28)
pose_bone("RightLeg", rx=30)
pose_bone("RightFoot", rx=-10)
pose_bone("LeftUpLeg", rx=18)
pose_bone("LeftLeg", rx=-12)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

bb_min2, bb_max2 = bbox(char)
center2 = (bb_min2 + bb_max2)/2
Hgt2 = bb_max2.z - bb_min2.z
Wid2 = max(bb_max2.x-bb_min2.x, bb_max2.y-bb_min2.y)
fit = max(Hgt2, Wid2)
print(f"[e] posed bbox H={Hgt2:.3f} W={Wid2:.3f} center={tuple(round(v,3) for v in center2)}")
cam("ER2CamDeform", Vector((center2.x, center2.y, center2.z)), fit*1.06, focal=50, yaw=28.0, zoff=0.04)
scn.render.filepath = "/tmp/eval_r2_deform.png"
print("[e] rendering deform..."); bpy.ops.render.render(write_still=True)
print("[e] wrote /tmp/eval_r2_deform.png")
print("[e] DONE")
