"""
Round 8 — turn the thin CLOSED remesh shell into a single-layer OPEN sheet.

The voxel shell of a thin garment has inner+outer surfaces millimetres apart
with bridging tris -> degenerate springs -> shattering. Delete every face
whose normal points toward the body (inner layer), keep the outer sheet,
prune unanchored islands, re-bind SD, rebake.
"""
import bpy
import bmesh
import time
from mathutils.kdtree import KDTree

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
char = bpy.data.objects["char1"]
PREROLL = -20

# body KDTree (non-cape/robe verts of char1, world space at rest)
import re
CAPE_RE = re.compile(r"^phys_(cape|robe)_")
cape_gi = {g.index for g in char.vertex_groups if CAPE_RE.match(g.name)}
MW = char.matrix_world.copy()
body_pts = []
for v in char.data.vertices:
    cw = sum(ge.weight for ge in v.groups if ge.group in cape_gi)
    tot = sum(ge.weight for ge in v.groups)
    if tot > 1e-6 and cw / tot < 0.2:
        body_pts.append(MW @ v.co)
kd = KDTree(len(body_pts))
for i, p in enumerate(body_pts):
    kd.insert(p, i)
kd.balance()
print(f"body ref points: {len(body_pts)}")

me = proxy.data
bm = bmesh.new()
bm.from_mesh(me)
bm.faces.ensure_lookup_table()
doom_f = []
for f in bm.faces:
    c = f.calc_center_median()
    p, _, _ = kd.find(c)
    d = c - p
    if d.length > 1e-9 and f.normal.dot(d) < 0.0:
        doom_f.append(f)
print(f"inner faces: {len(doom_f)}/{len(bm.faces)}")
bmesh.ops.delete(bm, geom=doom_f, context='FACES')
loose = [v for v in bm.verts if not v.link_faces]
bmesh.ops.delete(bm, geom=loose, context='VERTS')
bm.to_mesh(me)
bm.free()
print(f"outer sheet: {len(me.vertices)} verts {len(me.polygons)} faces")

# prune islands with <3 hard-pinned verts
pi = proxy.vertex_groups["pin"].index
pinw = [0.0] * len(me.vertices)
for v in me.vertices:
    for ge in v.groups:
        if ge.group == pi:
            pinw[v.index] = ge.weight
parent = list(range(len(me.vertices)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
for e in me.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b:
        parent[a] = b
from collections import defaultdict
isl = defaultdict(list)
for i in range(len(me.vertices)):
    isl[find(i)].append(i)
doom = set()
for verts in isl.values():
    if sum(1 for i in verts if pinw[i] > 0.5) < 3:
        doom.update(verts)
if doom:
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in doom], context='VERTS')
    bm.to_mesh(me)
    bm.free()
print(f"islands={len(isl)} pruned {len(doom)} -> {len(me.vertices)} verts")

# re-bind SD (topology changed)
cl = proxy.modifiers["Cloth"]
sd = char.modifiers["CapeSD"]
scene.frame_set(PREROLL)
cl.show_viewport = False
cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
with bpy.context.temp_override(object=char, active_object=char,
                               selected_objects=[char]):
    if sd.is_bound:
        bpy.ops.object.surfacedeform_bind(modifier="CapeSD")
    bpy.ops.object.surfacedeform_bind(modifier="CapeSD")
assert sd.is_bound, "SD re-bind failed"
print("SD re-bound")
cl.show_viewport = True
cl.show_render = True

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R8 DONE")
