"""
PHASE 3 FIXER r2 — anti-oscillation tune (after r1's probe showed settled
jitter up to 0.4 m/frame and action overshoot 2.25 m/frame).

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r2.py

Diagnosis: r1's soft pin gradient (many verts at 0.2-0.6 pin), aggressive
self-collision distance (15mm on ~30mm edges) and the 20mm collider shell
put the top cloth rows in permanent constraint-fighting. Fix:
  * steeper pin gradient (cape rows 0-1 hard, row 2 ~0.7, free by 2.6;
    robe rows 0-1 hard only — skirt hangs free like before)
  * self_distance_min 15->8mm, self_friction 25->15
  * cloth distance_min 12->8mm, collider thickness_outer 20->12mm
  * more damping (air 5, t/c/s 20, bend 15) + stiffer tension 40
Rebake (pin/settings only — SD binds stay valid), save.
"""
import bpy
import re
import time

PREROLL = -45
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")
scene = bpy.context.scene
char = bpy.data.objects["char1"]
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]
coll = bpy.data.objects["BodyCollider"]

coll.collision.thickness_outer = 0.012

def row_estimates(obj):
    rows = {}
    for gr in obj.vertex_groups:
        m = CHAIN_RE.match(gr.name)
        if m:
            rows[gr.index] = int(m.group(3))
    est = [0.0] * len(obj.data.vertices)
    for v in obj.data.vertices:
        acc = wacc = 0.0
        for ge in v.groups:
            if ge.group in rows:
                acc += ge.weight * rows[ge.group]
                wacc += ge.weight
        est[v.index] = acc / wacc if wacc > 1e-6 else 0.0
    return est

for obj, is_cape in ((cape, True), (robe, False)):
    est = row_estimates(obj)
    pin = obj.vertex_groups["pin"]
    hard, grad, free = [], {}, []
    for i, r in enumerate(est):
        if r <= 1.15:
            hard.append(i)
        elif is_cape and r < 2.6:
            # steep: 1.0 at row 1.15 -> 0.0 at row 2.6 (row 2 ~ 0.41...)
            w = (2.6 - r) / 1.45
            if w >= 0.35:
                grad[i] = w          # skip the soft 0-0.35 fighting zone
            else:
                free.append(i)
        else:
            free.append(i)
    pin.add(hard, 1.0, 'REPLACE')
    for i, w in grad.items():
        pin.add([i], w, 'REPLACE')
    pin.remove(free)
    print(f"{obj.name}: pin hard={len(hard)} grad={len(grad)} free={len(free)}")

    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.quality = 15
    cset.mass = 0.6
    cset.tension_stiffness = 40.0
    cset.compression_stiffness = 25.0
    cset.shear_stiffness = 30.0
    cset.bending_stiffness = 60.0
    cset.tension_damping = 20.0
    cset.compression_damping = 20.0
    cset.shear_damping = 20.0
    cset.bending_damping = 15.0
    cset.air_damping = 5.0
    ccol = cl.collision_settings
    ccol.collision_quality = 6
    ccol.distance_min = 0.008
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.008
    ccol.self_friction = 15.0
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R2 DONE")
