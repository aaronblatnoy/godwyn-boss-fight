"""
PHASE 3 FIXER r4 — collider root-cause fix.

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r4.py

r1's collider rebuild (keep chain-weight < 0.6) swept most of the cape/robe
FABRIC verts into the static collider: the cloth grids were colliding with an
armature-driven copy of themselves -> permanent constraint fighting, jitter
that got WORSE with every damping increase. Fix:
  * collider keep = chain weight < 0.15 (true body only), finer voxel 0.04,
    target 9000 verts (less jagged), shrink -0.02, thickness_outer 0.015
  * self-collision back ON, moderate (dist 0.01, friction 10)
  * moderate damping (air 5, t/c/s 15, bend 10), quality 15
Rebake, save. (SD binds target the grids — no rebind needed.)
"""
import bpy
import bmesh
import re
import time
from mathutils.kdtree import KDTree

PREROLL = -45
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
char = bpy.data.objects["char1"]

old = bpy.data.objects.get("BodyCollider")
if old:
    bpy.data.objects.remove(old, do_unlink=True)

gi_cape = {gr.index for gr in char.vertex_groups if CHAIN_RE.match(gr.name)}
nv = len(char.data.vertices)
keep = [True] * nv
for v in char.data.vertices:
    w = sum(ge.weight for ge in v.groups if ge.group in gi_cape)
    keep[v.index] = w < 0.15
print(f"collider keeps {sum(keep)}/{nv} verts (chain weight < 0.15)")

MW = char.matrix_world.copy()
mesh = char.data.copy()
mesh.name = "BodyCollider"
coll = bpy.data.objects.new("BodyCollider", mesh)
scene.collection.objects.link(coll)
src_pts, src_w = [], []
for v in char.data.vertices:
    if not keep[v.index]:
        continue
    src_pts.append(MW @ v.co)
    src_w.append([(ge.group, ge.weight) for ge in v.groups if ge.weight > 0.001])
kd = KDTree(len(src_pts))
for i, p in enumerate(src_pts):
    kd.insert(p, i)
kd.balance()

bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]],
                 context='VERTS')
for v in bm.verts:
    v.co = MW @ v.co
bm.to_mesh(mesh)
bm.free()
mesh.materials.clear()
coll.matrix_world.identity()
bpy.context.view_layer.objects.active = coll
rm = coll.modifiers.new("Remesh", 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 0.04
bpy.ops.object.modifier_apply(modifier="Remesh")
ratio = min(1.0, 9000 / max(1, len(mesh.vertices)))
if ratio < 1.0:
    dec = coll.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier="Dec")
print(f"collider remeshed+decimated -> {len(mesh.vertices)} verts")

for gr in char.vertex_groups:
    coll.vertex_groups.new(name=gr.name)
vgs = {gr.index: gr for gr in coll.vertex_groups}
for v in mesh.vertices:
    _, si, _ = kd.find(v.co)
    for gi, w in src_w[si]:
        tgt = vgs.get(gi)
        if tgt:
            tgt.add([v.index], w, 'REPLACE')

disp = coll.modifiers.new("Shrink", 'DISPLACE')
disp.direction = 'NORMAL'
disp.mid_level = 0.0
disp.strength = -0.02
amod = coll.modifiers.new("Armature", 'ARMATURE')
amod.object = arm
coll.modifiers.new("Collision", 'COLLISION')
cs = coll.collision
cs.thickness_outer = 0.015
cs.thickness_inner = 0.01
cs.damping = 0.9
cs.cloth_friction = 10.0
coll.hide_render = True
print("collider stack:", [m.name for m in coll.modifiers])

for name in ("CapeGrid", "RobeGrid"):
    cl = bpy.data.objects[name].modifiers["Cloth"]
    cset = cl.settings
    cset.quality = 15
    cset.mass = 0.6
    cset.tension_stiffness = 40.0
    cset.compression_stiffness = 25.0
    cset.shear_stiffness = 30.0
    cset.bending_stiffness = 60.0
    cset.tension_damping = 15.0
    cset.compression_damping = 15.0
    cset.shear_damping = 15.0
    cset.bending_damping = 10.0
    cset.air_damping = 5.0
    ccol = cl.collision_settings
    ccol.collision_quality = 6
    ccol.distance_min = 0.008
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.01
    ccol.self_friction = 10.0
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R4 DONE")
