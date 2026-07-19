"""
PHASE 2 — round-3 tune: prune unpinned islands, soften collisions, rebake.

Run:
  blender --background models/godwyn_mocap.blend --python scripts/p2cloth_tune.py
"""
import bpy
import bmesh
import time

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
collider = bpy.data.objects["BodyCollider"]
char = bpy.data.objects["char1"]
arm = next(o for o in scene.objects if o.type == "ARMATURE")
PREROLL = -20

# ── island analysis on the proxy; drop islands with no pinned verts ──
me = proxy.data
pin_idx = proxy.vertex_groups["pin"].index
pinw = [0.0] * len(me.vertices)
for v in me.vertices:
    for ge in v.groups:
        if ge.group == pin_idx:
            pinw[v.index] = ge.weight

# union-find over edges
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
islands = defaultdict(list)
for i in range(len(me.vertices)):
    islands[find(i)].append(i)
print(f"proxy islands: {len(islands)}")
doom = set()
for root, verts in sorted(islands.items(), key=lambda kv: -len(kv[1])):
    mp = max(pinw[i] for i in verts)
    anchored = sum(1 for i in verts if pinw[i] > 0.5)
    print(f"  island {len(verts)} verts, max_pin={mp:.2f}, anchored={anchored}")
    if anchored < 3:
        doom.update(verts)
if doom:
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in doom], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    print(f"pruned {len(doom)} unanchored verts -> {len(me.vertices)} remain")

# ── shrink the collider inside the body (it was inflated by remesh) ──
if "Shrink" not in [m.name for m in collider.modifiers]:
    disp = collider.modifiers.new("Shrink", 'DISPLACE')
    disp.direction = 'NORMAL'
    disp.mid_level = 0.0
    disp.strength = -0.035
    # order: Shrink BEFORE Armature (operates on rest mesh normals)
    collider.modifiers.move(collider.modifiers.find("Shrink"), 0)
print("collider stack:", [m.name for m in collider.modifiers])
collider.collision.thickness_outer = 0.004
collider.collision.thickness_inner = 0.005
collider.collision.damping = 0.9

# ── cloth params ─────────────────────────────────────────────────
cl = proxy.modifiers["Cloth"]
cset = cl.settings
cset.quality = 12
ccol = cl.collision_settings
ccol.distance_min = 0.004
ccol.collision_quality = 3

# ── re-bind SD (proxy topology changed) ──────────────────────────
sd = char.modifiers["CapeSD"]
scene.frame_set(PREROLL)
cl.show_viewport = False
cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
with bpy.context.temp_override(object=char, active_object=char,
                               selected_objects=[char]):
    if sd.is_bound:
        bpy.ops.object.surfacedeform_bind(modifier="CapeSD")   # unbind
    bpy.ops.object.surfacedeform_bind(modifier="CapeSD")       # bind
assert sd.is_bound, "SD re-bind failed"
print("SD re-bound")
cl.show_viewport = True
cl.show_render = True

# ── rebake ───────────────────────────────────────────────────────
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED", bpy.data.filepath)
print("P2CLOTH TUNE DONE")
