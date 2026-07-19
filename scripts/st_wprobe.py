"""st_wprobe.py — Phase 3 fixer probe: shell structure + weight pathology + sword albedo.

Loads models/godwyn_st_feet.blend. READ-ONLY (no save).
  A. char1 vertex groups (names beyond bone names? RIGID_ARMOR survived GLB?)
  B. connected components of char1: count, size histogram, per-component
     dominant vgroups + bbox for the big ones near shoulder/wrist/skirt.
  C. weight pathology: influence-count histogram, weight-sum histogram,
     stats for verts near RightArm/RightForeArm/RightHand and inner skirt.
  D. Godwyn_Sword: sample godwyn_albedo at loop UVs by world-z band ->
     mean RGB (is the blade sampling robe-blue?).
"""
import bpy, math
from collections import deque, Counter
from mathutils import Vector

import os
REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_st_feet.blend"))

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
me = char1.data
bone_names = {b.name for b in arm.data.bones}

print("=== A. VGROUPS ===")
vg_names = [g.name for g in char1.vertex_groups]
extra = [n for n in vg_names if n not in bone_names]
print(f"n_vgroups={len(vg_names)} non-bone groups: {extra}")

print("=== B. COMPONENTS ===")
n_v = len(me.vertices)
adj = [[] for _ in range(n_v)]
for e in me.edges:
    a, b = e.vertices
    adj[a].append(b)
    adj[b].append(a)
mw = char1.matrix_world
wco = [mw @ v.co for v in me.vertices]
visited = [False] * n_v
comps = []
for s in range(n_v):
    if visited[s]:
        continue
    comp = []
    dq = deque([s]); visited[s] = True
    while dq:
        u = dq.popleft(); comp.append(u)
        for w in adj[u]:
            if not visited[w]:
                visited[w] = True; dq.append(w)
    comps.append(comp)
comps.sort(key=len, reverse=True)
print(f"n_components={len(comps)} sizes(top20)={[len(c) for c in comps[:20]]}")
print(f"n small(<50 v)={sum(1 for c in comps if len(c)<50)}")

gname = {i: g.name for i, g in enumerate(char1.vertex_groups)}
def dom_groups(comp, k=4):
    acc = Counter()
    for i in comp:
        for g in me.vertices[i].groups:
            if g.weight > 0.05:
                acc[gname[g.group]] += g.weight
    return [(n, round(w / len(comp), 2)) for n, w in acc.most_common(k)]

for ci, comp in enumerate(comps[:15]):
    xs = [wco[i].x for i in comp]; ys = [wco[i].y for i in comp]; zs = [wco[i].z for i in comp]
    print(f"[C{ci}] n={len(comp)} x[{min(xs):.2f},{max(xs):.2f}] y[{min(ys):.2f},{max(ys):.2f}] "
          f"z[{min(zs):.2f},{max(zs):.2f}] dom={dom_groups(comp)}")

print("=== C. WEIGHT PATHOLOGY ===")
pbs = arm.pose.bones
def region_stats(tag, center, rad):
    idxs = [i for i in range(n_v) if (wco[i] - center).length < rad]
    ninf = Counter(); badsum = 0; sums = []
    phys_touch = 0
    for i in idxs:
        gs = [g for g in me.vertices[i].groups if g.weight > 1e-4]
        ninf[min(len(gs), 8)] += 1
        s = sum(g.weight for g in gs)
        sums.append(s)
        if abs(s - 1.0) > 0.05:
            badsum += 1
        if any(gname[g.group].startswith("phys_") for g in gs):
            phys_touch += 1
    sums.sort()
    print(f"[{tag}] n={len(idxs)} inf_hist={dict(sorted(ninf.items()))} "
          f"sum!=1(±5%)={badsum} sum_min={sums[0] if sums else 0:.2f} "
          f"sum_med={sums[len(sums)//2] if sums else 0:.2f} phys_weighted={phys_touch}")

Aw = arm.matrix_world
region_stats("R_shoulder", Aw @ pbs["RightArm"].head, 0.28)
region_stats("R_wrist", Aw @ pbs["RightHand"].head, 0.22)
region_stats("innerskirt", Vector((0.0, -0.15, 0.55)), 0.45)
region_stats("L_thigh", Aw @ pbs["LeftUpLeg"].head, 0.30)

# which components own the tear zones? map region verts -> component id
comp_of = [0] * n_v
for ci, comp in enumerate(comps):
    for i in comp:
        comp_of[i] = ci
for tag, center, rad in (("R_shoulder", Aw @ pbs["RightArm"].head, 0.28),
                         ("R_wrist", Aw @ pbs["RightHand"].head, 0.22),
                         ("innerskirt", Vector((0.0, -0.15, 0.55)), 0.45)):
    cc = Counter(comp_of[i] for i in range(n_v) if (wco[i] - center).length < rad)
    print(f"[{tag}] components: {cc.most_common(8)}")

print("=== D. SWORD ALBEDO SAMPLING ===")
img = bpy.data.images.get("godwyn_albedo")
if img is None:
    for i2 in bpy.data.images:
        print("img:", i2.name, i2.size[:])
else:
    W, H = img.size
    px = list(img.pixels)  # RGBA
    sme = sword.data
    uvl = sme.uv_layers.active.data
    swco = [sword.matrix_world @ v.co for v in sme.vertices]
    zs = [w.z for w in swco]
    zmin, zmax = min(zs), max(zs)
    bands = {}
    for poly in sme.polygons:
        for li in poly.loop_indices:
            vi = sme.loops[li].vertex_index
            z = swco[vi].z
            t = (z - zmin) / (zmax - zmin)
            band = min(int(t * 5), 4)
            u, v = uvl[li].uv
            xi = min(int(u % 1.0 * W), W - 1); yi = min(int(v % 1.0 * H), H - 1)
            o = 4 * (yi * W + xi)
            bands.setdefault(band, []).append((px[o], px[o+1], px[o+2], u, v))
    for band in sorted(bands):
        s = bands[band]
        r = sum(x[0] for x in s)/len(s); g = sum(x[1] for x in s)/len(s); b = sum(x[2] for x in s)/len(s)
        us = [x[3] for x in s]; vs = [x[4] for x in s]
        print(f"[BAND {band}] z~{zmin + (band+0.5)/5*(zmax-zmin):.2f} n={len(s)} "
              f"meanRGB=({r:.2f},{g:.2f},{b:.2f}) u[{min(us):.2f},{max(us):.2f}] v[{min(vs):.2f},{max(vs):.2f}]")
print("ST_WPROBE DONE")
