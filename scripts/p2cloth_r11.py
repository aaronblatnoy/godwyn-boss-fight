"""
Round 11 — stiffer flatter panels, calmer whip, sharper (but spatially
smooth) SD blend so the fitted bodice doesn't shred, rebind with softer
falloff, rebake.
"""
import bpy
import time

scene = bpy.context.scene
char = bpy.data.objects["char1"]
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]
PREROLL = -20

for obj in (cape, robe):
    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.quality = 12
    cset.mass = 0.4
    cset.tension_stiffness = 30.0
    cset.compression_stiffness = 20.0
    cset.shear_stiffness = 25.0
    cset.bending_stiffness = 30.0
    cset.tension_damping = 10.0
    cset.compression_damping = 10.0
    cset.shear_damping = 10.0
    cset.bending_damping = 3.0
    cset.air_damping = 2.0
    ccol = cl.collision_settings
    ccol.distance_min = 0.01
    ccol.collision_quality = 4

# sharpen SD groups: 0 below 0.2, 1 above 0.55, smoothstep between
for gname in ("cape_sd", "robe_sd"):
    vg = char.vertex_groups[gname]
    gi = vg.index
    ws = {}
    for v in char.data.vertices:
        for ge in v.groups:
            if ge.group == gi:
                ws[v.index] = ge.weight
    lo, hi = 0.2, 0.55
    add1, addm, rem = [], {}, []
    for i, w in ws.items():
        if w >= hi:
            add1.append(i)
        elif w <= lo:
            rem.append(i)
        else:
            t = (w - lo) / (hi - lo)
            addm[i] = t * t * (3 - 2 * t)
    vg.add(add1, 1.0, 'REPLACE')
    for i, w in addm.items():
        vg.add([i], w, 'REPLACE')
    vg.remove(rem)
    print(f"{gname}: full={len(add1)} blend={len(addm)} dropped={len(rem)}")

# rebind with softer falloff
scene.frame_set(PREROLL)
cls = [o.modifiers["Cloth"] for o in (cape, robe)]
for cl in cls:
    cl.show_viewport = False
    cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
for mn in ("CapeSD", "RobeSD"):
    sd = char.modifiers[mn]
    sd.falloff = 2.5
    with bpy.context.temp_override(object=char, active_object=char,
                                   selected_objects=[char]):
        if sd.is_bound:
            bpy.ops.object.surfacedeform_bind(modifier=mn)
        bpy.ops.object.surfacedeform_bind(modifier=mn)
    assert sd.is_bound, f"{mn} rebind failed"
    print(f"{mn} re-bound")
for cl in cls:
    cl.show_viewport = True
    cl.show_render = True

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R11 DONE")
