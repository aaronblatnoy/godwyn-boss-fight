"""
p2_face_probe.py — Phase 2 probe: open godwyn_sword.blend, report head/face
geometry (bounds, landmarks), render baseline EEVEE face close-ups.
Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/p2_face_probe.py 2>&1
"""
import bpy, os, math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_sword.blend")
OUT = "/tmp/face_previews"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = bpy.data.objects.get("Armature")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
body = max(meshes, key=lambda o: len(o.data.vertices))
print(f"[probe] objects: {[(o.name,o.type) for o in bpy.data.objects]}")
print(f"[probe] body={body.name} verts={len(body.data.vertices)} "
      f"vgroups={len(body.vertex_groups)} "
      f"shapekeys={body.data.shape_keys.key_blocks.keys() if body.data.shape_keys else None}")
print(f"[probe] bones={len(arm.data.bones)}")

awm = arm.matrix_world
head_b = arm.data.bones.get("Head")
neck_b = arm.data.bones.get("Neck")
print(f"[probe] Head bone head_local={tuple(head_b.head_local) if head_b else None}")
head_w = awm @ head_b.head_local if head_b else None
neck_w = awm @ neck_b.head_local if neck_b else None
print(f"[probe] Head joint world={tuple(round(c,4) for c in head_w)}")
if neck_w: print(f"[probe] Neck joint world={tuple(round(c,4) for c in neck_w)}")

mwm = body.matrix_world
me = body.data
hz = head_w.z
head_verts = [(v.index, mwm @ v.co) for v in me.vertices if (mwm @ v.co).z >= hz - 0.02]
hx = [c.x for _, c in head_verts]; hy = [c.y for _, c in head_verts]; hzz = [c.z for _, c in head_verts]
print(f"[probe] verts above Head joint z-0.02 ({hz-0.02:.3f}): {len(head_verts)}")
print(f"[probe] head bounds X {min(hx):.4f}..{max(hx):.4f}  Y {min(hy):.4f}..{max(hy):.4f}  Z {min(hzz):.4f}..{max(hzz):.4f}")

# Head vertex-group weighted verts
vg = body.vertex_groups.get("Head")
if vg:
    gi = vg.index
    wv = []
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.5:
                wv.append(mwm @ v.co); break
    if wv:
        xs=[c.x for c in wv]; ys=[c.y for c in wv]; zs=[c.z for c in wv]
        print(f"[probe] Head-VG(>0.5) verts={len(wv)} bounds X {min(xs):.4f}..{max(xs):.4f} "
              f"Y {min(ys):.4f}..{max(ys):.4f} Z {min(zs):.4f}..{max(zs):.4f}")

# z-slice profile of head widths (find chin/jaw/cheek/forehead)
zmin, zmax = min(hzz), max(hzz)
n = 14
for i in range(n):
    z0 = zmin + (zmax - zmin) * i / n
    z1 = zmin + (zmax - zmin) * (i + 1) / n
    sl = [c for _, c in head_verts if z0 <= c.z < z1]
    if sl:
        xs=[c.x for c in sl]; ys=[c.y for c in sl]
        print(f"[probe] slice z {z0:.3f}-{z1:.3f}: n={len(sl)} width_x={max(xs)-min(xs):.4f} "
              f"depth_y={max(ys)-min(ys):.4f} ymin={min(ys):.4f}")

# ── EEVEE baseline renders ──
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
world = scene.world or bpy.data.worlds.new("PrevWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.18, 0.18, 0.20, 1.0)
    bg.inputs[1].default_value = 1.0
for nm in ("PrevSun","PrevKey","PrevFill","PrevCam"):
    ob = bpy.data.objects.get(nm)
    if ob: bpy.data.objects.remove(ob, do_unlink=True)
sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun",'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(55), 0, math.radians(-30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("PrevFill", bpy.data.lights.new("PrevFill",'AREA'))
fill.data.energy = 120; fill.data.size = 2.0
face_c = Vector(((min(hx)+max(hx))/2, min(hy), (zmin+zmax)/2 + 0.05))
fill.location = face_c + Vector((0.3, -0.9, 0.2))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(frm, to):
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat('-Z','Y').to_euler()

shots = [
    ("face_front", face_c + Vector((0, -0.85, 0.02)), 85),
    ("face_34",    face_c + Vector((-0.55, -0.65, 0.05)), 85),
    ("face_side",  face_c + Vector((-0.85, 0.0, 0.02)), 85),
]
for name, frm, lens in shots:
    cam.data.lens = lens
    aim(frm, face_c)
    scene.render.filepath = os.path.join(OUT, f"base_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[probe] rendered {scene.render.filepath}")
print("[probe] DONE")
