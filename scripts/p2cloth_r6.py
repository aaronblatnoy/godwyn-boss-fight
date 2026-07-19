"""Round 6 — sane mass (0.8/vert was tons of fabric), stiff thick cloth."""
import bpy
import time

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
cl = proxy.modifiers["Cloth"]
cset = cl.settings
cset.mass = 0.15
cset.quality = 12
cset.tension_stiffness = 60.0
cset.compression_stiffness = 35.0
cset.shear_stiffness = 35.0
cset.bending_stiffness = 60.0
cset.tension_damping = 15.0
cset.compression_damping = 15.0
cset.shear_damping = 15.0
cset.bending_damping = 5.0
cset.air_damping = 1.5
cset.use_pressure = False

PREROLL = -20
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R6 DONE")
