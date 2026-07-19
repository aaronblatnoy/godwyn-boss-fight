"""
Phase 2 probe #2 — connected-component (island) analysis of char1 so we can
identify robe / cape / hair geometry without material splits.
Per island: vert count, bbox, centroid, dominant vertex groups.
"""
import bpy
import os
from collections import defaultdict
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p1_weights.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)

mesh = bpy.data.objects["char1"]
me = mesh.data
mw = mesh.matrix_world

# union-find over edges
parent = list(range(len(me.vertices)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
for e in me.edges:
    union(e.vertices[0], e.vertices[1])

islands = defaultdict(list)
for i in range(len(me.vertices)):
    islands[find(i)].append(i)

gname = {g.index: g.name for g in mesh.vertex_groups}
print(f"=== {len(islands)} islands ===")
for root, vs in sorted(islands.items(), key=lambda kv: -len(kv[1])):
    xs = [mw @ me.vertices[v].co for v in vs]
    mn = Vector((min(c.x for c in xs), min(c.y for c in xs), min(c.z for c in xs)))
    mx = Vector((max(c.x for c in xs), max(c.y for c in xs), max(c.z for c in xs)))
    cen = sum(xs, Vector()) / len(xs)
    mass = defaultdict(float)
    for v in vs:
        for g in me.vertices[v].groups:
            mass[gname.get(g.group, "?")] += g.weight
    top = sorted(mass.items(), key=lambda kv: -kv[1])[:6]
    print(f"island[{root:6d}] n={len(vs):6d} "
          f"bb=({mn.x:+.2f},{mn.y:+.2f},{mn.z:+.2f})..({mx.x:+.2f},{mx.y:+.2f},{mx.z:+.2f}) "
          f"cen=({cen.x:+.2f},{cen.y:+.2f},{cen.z:+.2f})")
    print(f"    groups: {[(n, round(w)) for n, w in top]}")
print("=== DONE ===")
