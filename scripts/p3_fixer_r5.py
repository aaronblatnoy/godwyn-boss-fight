"""
PHASE 3 FIXER r5 — cape bib + whip-peak calm.

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r5.py

r4 renders: fabric reads correctly at f30 but the whip peak (f14-18) is still
a shard tangle and the cape still flips over the shoulder into a chest clump
around f44. Final levers:
  * cape pin: rows 0-2 HARD (1.0), gradient to free by row 3.8 — the upper
    cape hangs from the shoulders and cannot flip forward over them
  * time_scale 0.75 on both grids: cloth sees 3/4-speed body motion — kills
    the whip energy spike while keeping the flow (heavy regal cloth)
  * air_damping 6
Rebake, save.
"""
import bpy
import re
import time

PREROLL = -45
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")
scene = bpy.context.scene
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]

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

# cape: rows 0-2 hard, free by 3.8
est = row_estimates(cape)
pin = cape.vertex_groups["pin"]
hard, grad, free = [], {}, []
for i, r in enumerate(est):
    if r <= 2.15:
        hard.append(i)
    elif r < 3.8:
        w = (3.8 - r) / 1.65
        if w >= 0.35:
            grad[i] = w
        else:
            free.append(i)
    else:
        free.append(i)
pin.add(hard, 1.0, 'REPLACE')
for i, w in grad.items():
    pin.add([i], w, 'REPLACE')
pin.remove(free)
print(f"CapeGrid: pin hard={len(hard)} grad={len(grad)} free={len(free)}")

for obj in (cape, robe):
    cset = obj.modifiers["Cloth"].settings
    cset.time_scale = 0.75
    cset.air_damping = 6.0
    obj.modifiers["Cloth"].point_cache.frame_start = PREROLL
    obj.modifiers["Cloth"].point_cache.frame_end = scene.frame_end

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R5 DONE")
