"""
st_probe_swordsrc.py — is the visible planted sword Godwyn_Sword, or fused
geometry still inside char1?  Hide Godwyn_Sword + Gauntlet, re-render, and
count char1 verts inside the visible sword region. Also dump Godwyn_Sword
LOCAL bbox + cross-section profile so we can find the hilt end.
"""
import bpy, os, math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO, "models", "godwyn_game.glb")
OUT = "/tmp/st_probe"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

char1 = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
gaunt = bpy.data.objects["Godwyn_Gauntlet"]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

# count char1 verts in the visible sword region (left-side plant column)
n = 0
zmin, zmax = 99, -99
for v in char1.data.vertices:
    w = char1.matrix_world @ v.co
    if 0.40 < w.x < 0.85 and -1.0 < w.y < -0.35 and -0.1 < w.z < 2.2:
        n += 1
        zmin, zmax = min(zmin, w.z), max(zmax, w.z)
print(f"[CHAR1 SWORD-REGION] verts in plant column: {n}  z=[{zmin:.2f},{zmax:.2f}]")

# Godwyn_Sword local bbox + profile along long axis
me = sword.data
los = [v.co for v in me.vertices]
mins = Vector((min(c[i] for c in los) for i in range(3)))
maxs = Vector((max(c[i] for c in los) for i in range(3)))
dims = maxs - mins
print(f"[SWORD LOCAL] bbox min={tuple(round(x,3) for x in mins)} max={tuple(round(x,3) for x in maxs)} dims={tuple(round(x,3) for x in dims)}")
axis = max(range(3), key=lambda i: dims[i])
print(f"  long axis = {'XYZ'[axis]}  length={dims[axis]:.3f}")
# 20-bin cross-section width profile
bins = 20
prof = [[0.0, 0] for _ in range(bins)]
other = [i for i in range(3) if i != axis]
import collections
binpts = collections.defaultdict(list)
for co in los:
    t = (co[axis] - mins[axis]) / dims[axis]
    b = min(bins - 1, int(t * bins))
    binpts[b].append(co)
for b in range(bins):
    pts = binpts.get(b, [])
    if not pts:
        print(f"  bin {b:02d}: empty"); continue
    w0 = max(p[other[0]] for p in pts) - min(p[other[0]] for p in pts)
    w1 = max(p[other[1]] for p in pts) - min(p[other[1]] for p in pts)
    print(f"  bin {b:02d} t={b/bins:.2f}: n={len(pts):4d} w{('XYZ'[other[0]])}={w0:.3f} w{('XYZ'[other[1]])}={w1:.3f}")

# renders with sword/gauntlet hidden
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam); scene.camera = cam

def shoot(name, target, dist, elev_deg, azim_deg, lens=50):
    cam.data.lens = lens
    el, az = math.radians(elev_deg), math.radians(azim_deg)
    off = Vector((dist*math.cos(el)*math.sin(az), -dist*math.cos(el)*math.cos(az), dist*math.sin(el)))
    cam.location = target + off
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")

sword.hide_render = True
gaunt.hide_render = True
shoot("noSword_full.png", Vector((0, 0, 1.6)), 7.0, 5, 0, 35)
lh = arm.matrix_world @ arm.pose.bones["LeftHand"].head
shoot("noSword_lhand.png", lh, 1.5, 5, 40, 50)
print("DONE")
