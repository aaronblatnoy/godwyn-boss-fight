"""
st_feet_probe.py — inspect foot/toe bones + toe geometry in godwyn_st_sword.blend.
Headless: blender --background --python ~/godwyn-boss-fight/scripts/st_feet_probe.py 2>&1
"""
import bpy
import os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_st_sword.blend"))

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print(f"[ARM] {arm.name}, bones={len(arm.data.bones)}")

# foot/leg-related bones
for b in arm.data.bones:
    n = b.name.lower()
    if any(k in n for k in ("foot", "toe", "leg", "hips")):
        h = arm.matrix_world @ b.head_local
        t = arm.matrix_world @ b.tail_local
        d = (t - h)
        print(f"[BONE] {b.name:28s} head=({h.x:+.3f},{h.y:+.3f},{h.z:+.3f}) "
              f"tail=({t.x:+.3f},{t.y:+.3f},{t.z:+.3f}) dir=({d.x:+.3f},{d.y:+.3f},{d.z:+.3f}) "
              f"parent={b.parent.name if b.parent else None}")

# current pose rotations on those bones
for pb in arm.pose.bones:
    n = pb.name.lower()
    if any(k in n for k in ("foot", "toe", "leg")):
        q = pb.rotation_quaternion if pb.rotation_mode == 'QUATERNION' else None
        e = pb.rotation_euler if pb.rotation_mode != 'QUATERNION' else None
        print(f"[POSE] {pb.name:28s} mode={pb.rotation_mode} quat={tuple(round(x,4) for x in q) if q else None} "
              f"eul={tuple(round(x,4) for x in e) if e else None} loc={tuple(round(x,4) for x in pb.location)}")

# evaluated mesh: toe/foot vertex spread (world), per side, low z
char1 = bpy.data.objects.get("char1")
print(f"[MESH] char1 verts={len(char1.data.vertices)}")
deps = bpy.context.evaluated_depsgraph_get()
ev = char1.evaluated_get(deps)
me = ev.to_mesh()
mw = ev.matrix_world
lo = [mw @ v.co for v in me.vertices if (mw @ v.co).z < 0.30]
print(f"[FEET] verts z<0.30: {len(lo)}")
for side, sgn in (("L", 1), ("R", -1)):
    sv = [w for w in lo if w.x * sgn > 0.02]
    if not sv:
        print(f"[{side}] none"); continue
    xs = [w.x for w in sv]; ys = [w.y for w in sv]; zs = [w.z for w in sv]
    print(f"[{side}] n={len(sv)} x[{min(xs):+.3f},{max(xs):+.3f}] y[{min(ys):+.3f},{max(ys):+.3f}] z[{min(zs):+.3f},{max(zs):+.3f}]")
    # front-most (most -y? or +y?) — print both extremes' centroids
    sv_sorted = sorted(sv, key=lambda w: w.y)
    front = sv_sorted[:40]; back = sv_sorted[-40:]
    fc = sum(front, Vector()) / len(front); bc = sum(back, Vector()) / len(back)
    print(f"[{side}] y-min-40 centroid=({fc.x:+.3f},{fc.y:+.3f},{fc.z:+.3f})  y-max-40 centroid=({bc.x:+.3f},{bc.y:+.3f},{bc.z:+.3f})")
ev.to_mesh_clear()

# vgroups: which foot groups exist and how many verts weighted
import collections
vg_idx = {vg.index: vg.name for vg in char1.vertex_groups if any(k in vg.name.lower() for k in ("foot", "toe", "leg"))}
cnt = collections.Counter()
for v in char1.data.vertices:
    for g in v.groups:
        if g.group in vg_idx and g.weight > 0.2:
            cnt[vg_idx[g.group]] += 1
print(f"[VG] {dict(cnt)}")
print("PROBE DONE")
