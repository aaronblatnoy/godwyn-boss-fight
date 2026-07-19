"""
PHASE 2 — real cloth sim on the cape/robe over the DoubleCombo mocap.

Run:
  blender --background models/godwyn_mocap.blend --python scripts/p2cloth_setup.py

Design (render path only — the game glb keeps its phys_ chains for Godot):
  * char1 stays intact (materials/UVs/weights untouched). We ADD:
      - vgroup "cape_sim"  = per-vert fraction of weight on cape/robe chain
                             rows >= 1 (0 at attachment, 1 deep in the cloth)
      - SurfaceDeform mod (vertex_group="cape_sim") after the Armature mod,
        bound to the cloth proxy -> cape verts follow the sim, body verts
        follow the armature, boundary blends smoothly.
  * CapeProxy: world-space (identity transform, meters) copy of the cape/robe
    verts, decimated, Armature mod + Cloth mod. Pin group = 1 - cape_sim,
    so attachment rows ride the rig and the rest simulates.
  * BodyCollider: world-space decimated copy of the non-cape verts,
    Armature mod + Collision mod. hide_render on both helpers.
  * Pre-roll: cloth cache starts at frame -20 (action holds the frame-1 pose
    before its first key) so the cloth settles before the combo starts.

Idempotent: deletes its own objects/vgroups/mods by name first.
"""
import bpy
import bmesh
import re
import time
from mathutils import Vector

PREROLL = -20
CAPE_RE = re.compile(r"^phys_(cape|robe)_.*_(\d+)$")
PROXY_TARGET_VERTS = 9000
COLLIDER_TARGET_VERTS = 6000

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
char = bpy.data.objects["char1"]
print(f"scene frames {scene.frame_start}-{scene.frame_end}")

# ── idempotent cleanup ───────────────────────────────────────────
for name in ("CapeProxy", "BodyCollider"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
for m in list(char.modifiers):
    if m.name == "CapeSD":
        char.modifiers.remove(m)
if "cape_sim" in char.vertex_groups:
    char.vertex_groups.remove(char.vertex_groups["cape_sim"])

# ── per-vertex cape fractions on char1 ───────────────────────────
gi_row = {}    # group index -> chain row (cape/robe only)
for g in char.vertex_groups:
    m = CAPE_RE.match(g.name)
    if m:
        gi_row[g.index] = int(m.group(2))

me = char.data
n = len(me.vertices)
cape_all = [0.0] * n   # total cape/robe weight
cape_sim = [0.0] * n   # cape/robe weight on rows >= 1, / total weight
for v in me.vertices:
    tot = 0.0
    ca = 0.0
    cf = 0.0
    for ge in v.groups:
        tot += ge.weight
        if ge.group in gi_row:
            ca += ge.weight
            if gi_row[ge.group] >= 1:
                cf += ge.weight
    cape_all[v.index] = ca
    if tot > 1e-6:
        cape_sim[v.index] = min(1.0, cf / tot)

n_cape = sum(1 for w in cape_all if w > 0.01)
n_free = sum(1 for w in cape_sim if w > 0.5)
print(f"cape/robe verts (any weight): {n_cape}/{n}; free-sim (>0.5): {n_free}")

vg = char.vertex_groups.new(name="cape_sim")
for i, w in enumerate(cape_sim):
    if w > 0.0:
        vg.add([i], w, 'REPLACE')

# ── helper: world-space CLEAN proxy of part of char1 ─────────────
# Decimating the raw render mesh gave sliver-triangle soup that exploded the
# sim. Instead: extract -> VOXEL REMESH (clean manifold shell that merges the
# robe's layers) -> decimate -> KDTree weight transfer from the source verts.
MW = char.matrix_world.copy()
from mathutils.kdtree import KDTree

def make_partial(name, keep_mask, extra_weights=None, target_verts=8000,
                 voxel=0.05):
    mesh = char.data.copy()
    mesh.name = name
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    # source data for the post-remesh weight transfer (orig kept verts)
    src_pts = []
    src_w = []       # list of (group_index, weight) tuples per kept vert
    extra_names = list(extra_weights.keys()) if extra_weights else []
    for v in char.data.vertices:
        if not keep_mask[v.index]:
            continue
        src_pts.append(MW @ v.co)
        gw = [(ge.group, ge.weight) for ge in v.groups if ge.weight > 0.001]
        if extra_weights:
            for k, gname in enumerate(extra_names):
                w = extra_weights[gname][v.index]
                if w > 0.001:
                    gw.append((10000 + k, w))   # sentinel idx for extras
        src_w.append(gw)
    kd = KDTree(len(src_pts))
    for i, p in enumerate(src_pts):
        kd.insert(p, i)
    kd.balance()
    # cut the mesh down + bake world transform (identity object, meters)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    doomed = [v for v in bm.verts if not keep_mask[v.index]]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    for v in bm.verts:
        v.co = MW @ v.co
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.clear()
    obj.matrix_world.identity()
    print(f"{name}: {len(mesh.vertices)} verts after extract")
    bpy.context.view_layer.objects.active = obj
    rm = obj.modifiers.new("Remesh", 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    bpy.ops.object.modifier_apply(modifier="Remesh")
    print(f"{name}: remeshed({voxel}) to {len(mesh.vertices)} verts")
    ratio = min(1.0, target_verts / max(1, len(mesh.vertices)))
    if ratio < 1.0:
        dec = obj.modifiers.new("Dec", 'DECIMATE')
        dec.ratio = ratio
        bpy.ops.object.modifier_apply(modifier="Dec")
        print(f"{name}: decimated to {len(mesh.vertices)} verts")
    # SurfaceDeform refuses concave (remesh quad) polys -> all tris
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    print(f"{name}: triangulated -> {len(mesh.polygons)} tris")
    # weight transfer: nearest source vert
    for g in char.vertex_groups:            # same order -> same indices
        obj.vertex_groups.new(name=g.name)
    extra_vgs = {10000 + k: obj.vertex_groups.new(name=gname)
                 for k, gname in enumerate(extra_names)}
    vgs = {g.index: g for g in obj.vertex_groups}
    for v in mesh.vertices:
        _, si, _ = kd.find(v.co)
        for gi, w in src_w[si]:
            tgt = extra_vgs.get(gi) or vgs.get(gi)
            if tgt:
                tgt.add([v.index], w, 'REPLACE')
    amod = obj.modifiers.new("Armature", 'ARMATURE')
    amod.object = arm
    obj.hide_render = True
    return obj

t0 = time.time()
keep_cape = [w > 0.01 for w in cape_all]
pin = [max(0.0, 1.0 - w) for w in cape_sim]
proxy = make_partial("CapeProxy", keep_cape,
                     extra_weights={"pin": pin, "cape_sim": cape_sim},
                     target_verts=PROXY_TARGET_VERTS)

keep_body = [w < 0.35 for w in cape_all]
collider = make_partial("BodyCollider", keep_body,
                        target_verts=COLLIDER_TARGET_VERTS)
print(f"proxies built in {time.time()-t0:.1f}s")

# ── collider physics ─────────────────────────────────────────────
col = collider.modifiers.new("Collision", 'COLLISION')
cs = collider.collision
cs.thickness_outer = 0.008
cs.thickness_inner = 0.01
cs.damping = 0.8
cs.cloth_friction = 8.0

# ── cloth on the proxy ───────────────────────────────────────────
cl = proxy.modifiers.new("Cloth", 'CLOTH')
cset = cl.settings
cset.vertex_group_mass = "pin"          # pin group
cset.quality = 10
cset.time_scale = 1.0
cset.mass = 0.7                          # heavy regal cloth
cset.tension_stiffness = 35.0
cset.compression_stiffness = 20.0
cset.shear_stiffness = 20.0
cset.bending_stiffness = 8.0             # thick fabric, resists folding
cset.tension_damping = 8.0
cset.compression_damping = 8.0
cset.shear_damping = 8.0
cset.bending_damping = 1.0
cset.air_damping = 1.4
ccol = cl.collision_settings
ccol.collision_quality = 3
ccol.distance_min = 0.006
ccol.use_self_collision = False          # iterate: enable if interpenetration
cache = cl.point_cache
cache.frame_start = PREROLL
cache.frame_end = scene.frame_end
print("cloth configured")

# ── SurfaceDeform on char1 (after the Armature modifier) ─────────
scene.frame_set(PREROLL)                  # action holds frame-1 pose here
sd = char.modifiers.new("CapeSD", 'SURFACE_DEFORM')
sd.target = proxy
sd.vertex_group = "cape_sim"
sd.falloff = 4.0
# keep stack order: Armature, CapeSD
ai = char.modifiers.find("Armature")
si = char.modifiers.find("CapeSD")
if si < ai:
    char.modifiers.move(si, ai)
print("char1 stack:", [m.name for m in char.modifiers])

cl.show_viewport = False                  # bind against armature-only proxy
cl.show_render = False
bpy.context.view_layer.objects.active = char
char.select_set(True)
bpy.context.view_layer.update()
t0 = time.time()
with bpy.context.temp_override(object=char, active_object=char,
                               selected_objects=[char]):
    bpy.ops.object.surfacedeform_bind(modifier="CapeSD")
assert sd.is_bound, "SurfaceDeform bind FAILED"
print(f"SurfaceDeform bound in {time.time()-t0:.1f}s")
cl.show_viewport = True
cl.show_render = True

# ── bake ─────────────────────────────────────────────────────────
old_start = scene.frame_start
scene.frame_start = PREROLL
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"cloth baked frames {PREROLL}-{scene.frame_end} "
      f"in {time.time()-t0:.1f}s")
scene.frame_start = old_start

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f"SAVED {bpy.data.filepath}")
print("P2CLOTH SETUP DONE")
