"""
Round 10 — REBUILD: cloth grids generated from the phys chain lattice.

The remesh-proxy approach kept shattering (thin shells, ragged sheets,
embedded verts). The phys_ chains are an authored cloth lattice: build clean
quad grids from chain-bone rest positions (cape = 3-chain sheet, robe =
8-chain closed skirt), weight each grid vert 100% to its chain-row bone so
the pre-cloth state matches the rig exactly (same abstraction Godot uses at
runtime), pin rows 0-1, simulate, and SurfaceDeform char1's cape/robe verts
onto the baked grids.
"""
import bpy
import bmesh
import re
import time
from collections import defaultdict
from mathutils import Vector

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
char = bpy.data.objects["char1"]
collider = bpy.data.objects["BodyCollider"]
PREROLL = -20
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")

# ── cleanup ──────────────────────────────────────────────────────
for name in ("CapeProxy", "CapeGrid", "RobeGrid"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
for mn in ("CapeSD", "RobeSD"):
    m = char.modifiers.get(mn)
    if m:
        char.modifiers.remove(m)
for gn in ("cape_sim", "cape_sd", "robe_sd"):
    g = char.vertex_groups.get(gn)
    if g:
        char.vertex_groups.remove(g)

# ── chain layout from rest bones ─────────────────────────────────
AMW = arm.matrix_world.copy()
chains = defaultdict(dict)   # (kind, chain) -> {row: (bone_name, world_head)}
for b in arm.data.bones:
    m = CHAIN_RE.match(b.name)
    if m:
        kind, cname, row = m.group(1), m.group(2), int(m.group(3))
        chains[(kind, cname)][row] = (b.name, (AMW @ b.matrix_local).to_translation())
for k, rows in sorted(chains.items()):
    print(f"chain {k}: rows={len(rows)}")

def build_grid(objname, chain_keys, closed):
    rowsn = min(len(chains[k]) for k in chain_keys)
    cols = [[chains[k][r] for r in range(rowsn)] for k in chain_keys]
    nch = len(cols)
    mesh = bpy.data.meshes.new(objname)
    obj = bpy.data.objects.new(objname, mesh)
    scene.collection.objects.link(obj)
    verts = []
    names = []
    for col in cols:
        for bname, p in col:
            verts.append(p)
            names.append(bname)
    faces = []
    npairs = nch if closed else nch - 1
    for i in range(npairs):
        j = (i + 1) % nch
        for r in range(rowsn - 1):
            a = i * rowsn + r
            b = j * rowsn + r
            faces.append((a, a + 1, b + 1, b))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    # weights: each vert -> its chain bone; pin rows 0-1
    for gi, bname in enumerate(names):
        vg = obj.vertex_groups.get(bname) or obj.vertex_groups.new(name=bname)
        vg.add([gi], 1.0, 'REPLACE')
    pin = obj.vertex_groups.new(name="pin")
    for gi in range(len(verts)):
        if gi % rowsn <= 1:
            pin.add([gi], 1.0, 'REPLACE')
    # subdivide 2x for cloth resolution (interpolates weights), then tris
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for _ in range(2):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                                  use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    # binarize pin after interpolation
    pi = pin.index
    hard, free = [], []
    for v in mesh.vertices:
        w = 0.0
        for ge in v.groups:
            if ge.group == pi:
                w = ge.weight
        (hard if w > 0.6 else free).append(v.index)
    pin.add(hard, 1.0, 'REPLACE')
    pin.remove(free)
    print(f"{objname}: {len(mesh.vertices)} verts {len(mesh.polygons)} tris, "
          f"pinned {len(hard)}")
    amod = obj.modifiers.new("Armature", 'ARMATURE')
    amod.object = arm
    cl = obj.modifiers.new("Cloth", 'CLOTH')
    cset = cl.settings
    cset.vertex_group_mass = "pin"
    cset.quality = 10
    cset.mass = 0.4
    cset.tension_stiffness = 25.0
    cset.compression_stiffness = 15.0
    cset.shear_stiffness = 15.0
    cset.bending_stiffness = 10.0
    cset.tension_damping = 8.0
    cset.compression_damping = 8.0
    cset.shear_damping = 8.0
    cset.bending_damping = 1.0
    cset.air_damping = 1.3
    ccol = cl.collision_settings
    ccol.collision_quality = 3
    ccol.distance_min = 0.015
    ccol.use_self_collision = False
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end
    obj.hide_render = True
    return obj, cl

cape_keys = sorted([k for k in chains if k[0] == "cape"],
                   key=lambda k: chains[k][0][1].x)
r0 = [k for k in chains if k[0] == "robe"]
ctr = sum((chains[k][0][1] for k in r0), Vector()) / len(r0)
import math
robe_keys = sorted(r0, key=lambda k: math.atan2(chains[k][0][1].y - ctr.y,
                                                chains[k][0][1].x - ctr.x))
print("cape order:", [k[1] for k in cape_keys])
print("robe order:", [k[1] for k in robe_keys])
cape_obj, cape_cl = build_grid("CapeGrid", cape_keys, closed=False)
robe_obj, robe_cl = build_grid("RobeGrid", robe_keys, closed=True)

# ── char1 SD blend groups (per garment, chain rows >= 1) ─────────
gi_info = {}
for g in char.vertex_groups:
    m = CHAIN_RE.match(g.name)
    if m:
        gi_info[g.index] = (m.group(1), int(m.group(3)))
w_cape = [0.0] * len(char.data.vertices)
w_robe = [0.0] * len(char.data.vertices)
for v in char.data.vertices:
    tot = sum(ge.weight for ge in v.groups)
    if tot < 1e-6:
        continue
    for ge in v.groups:
        info = gi_info.get(ge.group)
        if info and info[1] >= 1:
            if info[0] == "cape":
                w_cape[v.index] += ge.weight / tot
            else:
                w_robe[v.index] += ge.weight / tot
vg_c = char.vertex_groups.new(name="cape_sd")
vg_r = char.vertex_groups.new(name="robe_sd")
for i in range(len(char.data.vertices)):
    if w_cape[i] > 0.01:
        vg_c.add([i], min(1.0, w_cape[i]), 'REPLACE')
    if w_robe[i] > 0.01:
        vg_r.add([i], min(1.0, w_robe[i]), 'REPLACE')
print(f"cape_sd verts={sum(1 for w in w_cape if w > 0.01)} "
      f"robe_sd verts={sum(1 for w in w_robe if w > 0.01)}")

# ── SD binds at preroll ──────────────────────────────────────────
scene.frame_set(PREROLL)
for cl in (cape_cl, robe_cl):
    cl.show_viewport = False
    cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
for mn, tgt, vgn in (("CapeSD", cape_obj, "cape_sd"),
                     ("RobeSD", robe_obj, "robe_sd")):
    sd = char.modifiers.new(mn, 'SURFACE_DEFORM')
    sd.target = tgt
    sd.vertex_group = vgn
    sd.falloff = 4.0
    with bpy.context.temp_override(object=char, active_object=char,
                                   selected_objects=[char]):
        bpy.ops.object.surfacedeform_bind(modifier=mn)
    assert sd.is_bound, f"{mn} bind failed"
    print(f"{mn} bound")
for cl in (cape_cl, robe_cl):
    cl.show_viewport = True
    cl.show_render = True

# collider stays as configured (shrunk, soft)
print("collider mods:", [m.type for m in collider.modifiers])

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R10 DONE")
