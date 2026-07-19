"""
Round 13 — longer preroll so the cloth is settled at frame 1, rebake, save.
"""
import bpy
import time

scene = bpy.context.scene
PREROLL = -45
for name in ("CapeGrid", "RobeGrid"):
    cl = bpy.data.objects[name].modifiers["Cloth"]
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
print("SAVED; FINAL BAKE DONE")
