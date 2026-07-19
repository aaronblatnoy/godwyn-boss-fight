"""Round 4 — isolate: no body collision, rebake, save."""
import bpy
import time

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
collider = bpy.data.objects["BodyCollider"]
PREROLL = -20

for m in list(collider.modifiers):
    if m.type == 'COLLISION':
        collider.modifiers.remove(m)
print("collider collision removed")

cl = proxy.modifiers["Cloth"]
cl.collision_settings.use_self_collision = False

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R4 DONE")
