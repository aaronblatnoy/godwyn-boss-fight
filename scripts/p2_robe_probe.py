"""
Phase 2 probe — inspect godwyn_p1_weights.blend before adding robe/cape/hair
physics bone chains.

Reports:
  - objects (type, parent, parent_bone)
  - armature bone tree (name, head/tail world-z, use_deform)
  - mesh materials + per-material vertex counts + bounding boxes
  - shape keys
  - for each material region: dominant vertex groups (weight mass)
  - spatial slices of robe-material verts (to plan chain placement)
"""
import bpy
import os
import json
from collections import defaultdict
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p1_weights.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)

print("=== OBJECTS ===")
for o in bpy.data.objects:
    print(f"  {o.name:28s} type={o.type:9s} parent={o.parent.name if o.parent else None} "
          f"parent_type={o.parent_type} parent_bone={o.parent_bone!r}")

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print(f"\n=== ARMATURE '{arm.name}' ({len(arm.data.bones)} bones) ===")
def walk(b, d=0):
    hw = arm.matrix_world @ b.head_local
    tw = arm.matrix_world @ b.tail_local
    print(f"  {'  '*d}{b.name:24s} head=({hw.x:+.2f},{hw.y:+.2f},{hw.z:+.2f}) "
          f"tail=({tw.x:+.2f},{tw.y:+.2f},{tw.z:+.2f}) deform={b.use_deform}")
    for c in b.children:
        walk(c, d+1)
for b in arm.data.bones:
    if b.parent is None:
        walk(b)

for mesh in [o for o in bpy.data.objects if o.type == "MESH"]:
    me = mesh.data
    print(f"\n=== MESH '{mesh.name}' verts={len(me.vertices)} polys={len(me.polygons)} ===")
    print(f"  shape_keys: {[k.name for k in me.shape_keys.key_blocks] if me.shape_keys else None}")
    print(f"  vertex_groups: {[g.name for g in mesh.vertex_groups]}")
    print(f"  materials: {[m.name for m in me.materials if m]}")
    if not me.materials:
        continue
    # per-material vertex sets
    mat_verts = defaultdict(set)
    for p in me.polygons:
        for vi in p.vertices:
            mat_verts[p.material_index].add(vi)
    mw = mesh.matrix_world
    gname = {g.index: g.name for g in mesh.vertex_groups}
    for mi, vs in sorted(mat_verts.items()):
        mat = me.materials[mi]
        if mat is None:
            continue
        xs = [mw @ me.vertices[v].co for v in vs]
        mn = Vector((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
        mx = Vector((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
        # dominant groups
        mass = defaultdict(float)
        for v in vs:
            for g in me.vertices[v].groups:
                mass[gname.get(g.group, "?")] += g.weight
        top = sorted(mass.items(), key=lambda kv: -kv[1])[:8]
        print(f"  mat[{mi}] {mat.name:24s} nverts={len(vs):6d} "
              f"bbox=({mn.x:+.2f},{mn.y:+.2f},{mn.z:+.2f})..({mx.x:+.2f},{mx.y:+.2f},{mx.z:+.2f})")
        print(f"      top groups: {[(n, round(w,1)) for n, w in top]}")
        # z-slices with y-extent for cloth mats
        lname = mat.name.lower()
        if any(k in lname for k in ("robe", "cloth", "cape", "hair", "tabard", "skirt")):
            zs = sorted(c.z for c in xs)
            print(f"      z-range {zs[0]:+.2f}..{zs[-1]:+.2f}; slice extents:")
            import math
            z0, z1 = zs[0], zs[-1]
            n = 6
            for i in range(n):
                lo = z0 + (z1-z0)*i/n
                hi = z0 + (z1-z0)*(i+1)/n
                sl = [c for c in xs if lo <= c.z <= hi]
                if sl:
                    print(f"        z[{lo:+.2f},{hi:+.2f}] n={len(sl):5d} "
                          f"x=({min(c.x for c in sl):+.2f},{max(c.x for c in sl):+.2f}) "
                          f"y=({min(c.y for c in sl):+.2f},{max(c.y for c in sl):+.2f})")

print("\n=== PROBE DONE ===")
