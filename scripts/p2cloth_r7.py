"""
Round 7 — sim ONLY the flowing regions (cape rows >=2, robe rows >=3).
The fitted upper robe/bodice stays hard-pinned to the rig; the sim handles
just the trailing cape + skirt hem, so it cannot tangle the whole outfit.
Updates char1's SD blend group ("cape_sim") to match (no rebind needed —
SD binds all verts; the vgroup only modulates output).
"""
import bpy
import re
import time

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
char = bpy.data.objects["char1"]
CAPE_RE = re.compile(r"^phys_(cape|robe)_.*_(\d+)$")
FREE_ROW = {"cape": 2, "robe": 3}

def free_frac_map(obj):
    gi = {}
    for g in obj.vertex_groups:
        m = CAPE_RE.match(g.name)
        if m:
            gi[g.index] = (m.group(1), int(m.group(2)))
    out = [0.0] * len(obj.data.vertices)
    for v in obj.data.vertices:
        tot = 0.0
        fr = 0.0
        for ge in v.groups:
            if obj.vertex_groups[ge.group].name in ("pin", "cape_sim"):
                continue
            tot += ge.weight
            info = gi.get(ge.group)
            if info and info[1] >= FREE_ROW[info[0]]:
                fr += ge.weight
        if tot > 1e-6:
            out[v.index] = min(1.0, fr / tot)
    return out

# ── proxy: rebuild binary pin from its own transferred weights ───
ff = free_frac_map(proxy)
vg = proxy.vertex_groups["pin"]
hard = [i for i, w in enumerate(ff) if w < 0.5]
freed = [i for i, w in enumerate(ff) if w >= 0.5]
vg.remove(list(range(len(proxy.data.vertices))))
vg.add(hard, 1.0, 'REPLACE')
print(f"proxy pins: {len(hard)} hard, {len(freed)} free")

# ── char1: rebuild cape_sim (SD blend) to the same free region ───
ffc = free_frac_map(char)
if "cape_sim" in char.vertex_groups:
    char.vertex_groups.remove(char.vertex_groups["cape_sim"])
vgc = char.vertex_groups.new(name="cape_sim")
nsim = 0
for i, w in enumerate(ffc):
    if w > 0.0:
        vgc.add([i], w, 'REPLACE')
        nsim += 1
sd = char.modifiers["CapeSD"]
sd.vertex_group = "cape_sim"
print(f"char1 cape_sim verts: {nsim} (SD bound={sd.is_bound})")

# ── cloth params ─────────────────────────────────────────────────
cl = proxy.modifiers["Cloth"]
cset = cl.settings
cset.mass = 0.2
cset.bending_stiffness = 40.0
cset.quality = 12

PREROLL = -20
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R7 DONE")
