"""
Round 9 — pin everything that starts embedded in / hugging the collider.

The sim exploded even in a static preroll: fitted-garment verts start INSIDE
the collider (armor plates protrude past the cloth sheet) and collision
response catapults them every step. Fix: signed-distance test at preroll —
any free vert closer than SAFE_DIST to (or inside) the collider gets hard
pinned. Only truly free-hanging cloth keeps simulating.
"""
import bpy
import time
from mathutils.bvhtree import BVHTree

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
collider = bpy.data.objects["BodyCollider"]
PREROLL = -20
SAFE_DIST = 0.02

cl = proxy.modifiers["Cloth"]
scene.frame_set(PREROLL)
cl.show_viewport = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

cev = collider.evaluated_get(dg)
cme = cev.to_mesh()
verts = [cev.matrix_world @ v.co for v in cme.vertices]
polys = [tuple(p.vertices) for p in cme.polygons]
bvh = BVHTree.FromPolygons(verts, polys)
cev.to_mesh_clear()

pev = proxy.evaluated_get(dg)
pos = [v.co.copy() for v in pev.data.vertices]
cl.show_viewport = True

vg = proxy.vertex_groups["pin"]
pi = vg.index
pinw = [0.0] * len(proxy.data.vertices)
for v in proxy.data.vertices:
    for ge in v.groups:
        if ge.group == pi:
            pinw[v.index] = ge.weight

newly = []
for i, p in enumerate(pos):
    if pinw[i] > 0.5:
        continue
    loc, nrm, _, dist = bvh.find_nearest(p)
    if loc is None:
        continue
    signed = (p - loc).dot(nrm)
    if signed < SAFE_DIST:
        newly.append(i)
vg.add(newly, 1.0, 'REPLACE')
free_left = sum(1 for i, w in enumerate(pinw)
                if w <= 0.5 and i not in set(newly))
print(f"newly pinned (embedded/hugging): {len(newly)}; free remaining: {free_left}")

ccol = cl.collision_settings
ccol.distance_min = 0.003

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R9 DONE")
