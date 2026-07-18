"""p_fixer2_probe.py — round-2 fixer probe: weight pathology + sword placement facts."""
import bpy, os
from collections import deque
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_face.blend"))
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
sword = bpy.data.objects.get("Godwyn_Sword")
me = body.data
awm = arm.matrix_world
mwm = body.matrix_world

for bn in ("Hips","Spine","Spine1","Spine2","Neck","Head","RightShoulder","RightArm",
           "RightForeArm","RightHand","LeftShoulder","LeftArm","LeftForeArm","LeftHand"):
    if bn in arm.data.bones:
        h = awm @ arm.data.bones[bn].head_local
        print(f"[probe] bone {bn:15s} head_w=({h.x:+.3f},{h.y:+.3f},{h.z:+.3f})")

gi = {g.index: g.name for g in body.vertex_groups}
name2i = {g.name: g.index for g in body.vertex_groups}

# weight pathology
n0 = n_many = 0
sum_low = 0
for v in me.vertices:
    ws = [(g.group, g.weight) for g in v.groups if g.weight > 1e-6]
    s = sum(w for _, w in ws)
    if s < 1e-4:
        n0 += 1
    elif s < 0.5:
        sum_low += 1
    if len(ws) > 4:
        n_many += 1
print(f"[probe] verts={len(me.vertices)} zero-weight={n0} lowsum(<0.5)={sum_low} >4-influences={n_many}")

# where are the zero-weight verts?
zw = [mwm @ v.co for v in me.vertices if sum(g.weight for g in v.groups) < 1e-4]
if zw:
    lo = Vector((min(c.x for c in zw), min(c.y for c in zw), min(c.z for c in zw)))
    hi = Vector((max(c.x for c in zw), max(c.y for c in zw), max(c.z for c in zw)))
    print(f"[probe] zero-weight bbox lo={tuple(round(c,2) for c in lo)} hi={tuple(round(c,2) for c in hi)}")

# right-arm region stats: verts within 0.30m of the RightArm->RightHand chain
ra = awm @ arm.data.bones["RightArm"].head_local
rf = awm @ arm.data.bones["RightForeArm"].head_local
rh = awm @ arm.data.bones["RightHand"].head_local
rs = awm @ arm.data.bones["RightShoulder"].head_local

def seg_d(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - a - ab * t).length

arm_groups = {name2i[n] for n in ("RightShoulder","RightArm","RightForeArm","RightHand") if n in name2i}
n_reg = reg_zero = reg_low = 0
dom_counts = {}
for v in me.vertices:
    w = mwm @ v.co
    d = min(seg_d(w, rs, ra), seg_d(w, ra, rf), seg_d(w, rf, rh))
    if d > 0.30:
        continue
    n_reg += 1
    ws = sorted(((g.weight, gi[g.group]) for g in v.groups if g.weight > 1e-6), reverse=True)
    s = sum(x for x, _ in ws)
    if s < 1e-4:
        reg_zero += 1
    elif s < 0.5:
        reg_low += 1
    if ws:
        dom_counts[ws[0][1]] = dom_counts.get(ws[0][1], 0) + 1
print(f"[probe] right-arm-region verts={n_reg} zero={reg_zero} lowsum={reg_low}")
print(f"[probe] dominant groups in region: {sorted(dom_counts.items(), key=lambda kv: -kv[1])[:12]}")

# island stats
import bmesh
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
seen = set(); sizes = []
for v0 in bm.verts:
    if v0.index in seen: continue
    comp = {v0.index}; dq = deque([v0])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index not in comp:
                comp.add(o.index); dq.append(o)
    seen |= comp; sizes.append(len(comp))
bm.free()
sizes.sort()
micro = sum(1 for s in sizes if s < 15)
print(f"[probe] body islands={len(sizes)} micro(<15v)={micro} biggest={sizes[-5:]}")

# sword facts
if sword:
    pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
    lo = Vector((min(c.x for c in pts), min(c.y for c in pts), min(c.z for c in pts)))
    hi = Vector((max(c.x for c in pts), max(c.y for c in pts), max(c.z for c in pts)))
    print(f"[probe] sword verts={len(pts)} world bbox lo={tuple(round(c,3) for c in lo)} hi={tuple(round(c,3) for c in hi)}")
    print(f"[probe] RightHand head_w={tuple(round(c,3) for c in rh)}")
print("[probe] DONE")
