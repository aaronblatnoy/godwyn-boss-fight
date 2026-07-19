"""P3 fixer probe — materials, mesh islands, per-island material/bone stats.

Imports godwyn_game.glb fresh (same entry as fix_weights.py) and reports:
  - material slots + per-material face counts
  - connected vertex islands: size, dominant material, dominant bone,
    bbox, mean weight-entropy (how multi-bone the island is)
Writes /tmp/p3_probe.json
"""
import bpy, os, json
from collections import defaultdict

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = mesh.data
print("mesh:", mesh.name, "verts:", len(me.vertices), "polys:", len(me.polygons))
print("materials:", [m.name if m else None for m in me.materials])

matface = defaultdict(int)
for p in me.polygons:
    matface[p.material_index] += 1
print("faces per material index:", dict(matface))

# union-find islands over edges
parentuf = list(range(len(me.vertices)))
def find(a):
    while parentuf[a] != a:
        parentuf[a] = parentuf[parentuf[a]]
        a = parentuf[a]
    return a
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parentuf[ra] = rb
for e in me.edges:
    union(e.vertices[0], e.vertices[1])

isl = defaultdict(list)
for v in me.vertices:
    isl[find(v.index)].append(v.index)

# per-vertex dominant material via faces
vmat = defaultdict(lambda: defaultdict(int))
for p in me.polygons:
    for vi in p.vertices:
        vmat[vi][p.material_index] += 1

gname = {g.index: g.name for g in mesh.vertex_groups}
mw = mesh.matrix_world
report = []
for root, vis in sorted(isl.items(), key=lambda kv: -len(kv[1])):
    mats = defaultdict(int)
    bones = defaultdict(float)
    ninf = 0
    lo = [1e9]*3; hi = [-1e9]*3
    for vi in vis:
        for mi, c in vmat[vi].items():
            mats[mi] += c
        v = me.vertices[vi]
        ninf += len([g for g in v.groups if g.weight > 0.05])
        for g in v.groups:
            nm = gname.get(g.group)
            if nm:
                bones[nm] += g.weight
        c = mw @ v.co
        for k in range(3):
            lo[k] = min(lo[k], c[k]); hi[k] = max(hi[k], c[k])
    topb = sorted(bones.items(), key=lambda kv: -kv[1])[:3]
    report.append({
        "n": len(vis),
        "mat": max(mats, key=mats.get) if mats else None,
        "top_bones": [(n, round(w, 1)) for n, w in topb],
        "mean_inf": round(ninf/len(vis), 2),
        "bbox_lo": [round(x, 2) for x in lo],
        "bbox_hi": [round(x, 2) for x in hi],
    })
print(f"islands: {len(report)}")
for r in report[:60]:
    print(r)
with open("/tmp/p3_probe.json", "w") as fh:
    json.dump({"n_islands": len(report), "islands": report,
               "materials": [m.name if m else None for m in me.materials],
               "matface": {str(k): v for k, v in matface.items()}}, fh, indent=1)
print("=== PROBE DONE ===")
