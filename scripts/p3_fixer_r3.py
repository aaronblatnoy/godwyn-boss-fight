"""
PHASE 3 FIXER r3 — kill the residual oscillation.

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r3.py

r2 probe still showed 0.18-0.24 m/frame in the settled window. Change of
tack: self-collision was re-exciting the sim every step (constant contact
fighting on the closed skirt), and the hem had no floor to rest on.
  * self-collision OFF on both grids (SD + ClothCS hide residual overlap)
  * FloorCollider plane at Z=0 (hide_render) so the hem can come to rest
  * maximum calm: air_damping 8, t/c/s damping 25, bending_damping 25,
    quality 20 substeps
Rebake, save.
"""
import bpy
import time

PREROLL = -45
scene = bpy.context.scene
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]

# floor collider at Z=0 (idempotent)
if "FloorCollider" not in bpy.data.objects:
    pm = bpy.data.meshes.new("FloorCollider")
    E = 30.0
    pm.from_pydata([(-E, -E, 0), (E, -E, 0), (E, E, 0), (-E, E, 0)],
                   [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new("FloorCollider", pm)
    scene.collection.objects.link(fl)
    fl.modifiers.new("Collision", 'COLLISION')
    fl.collision.thickness_outer = 0.01
    fl.collision.thickness_inner = 0.01
    fl.collision.damping = 1.0
    fl.collision.cloth_friction = 20.0
    fl.hide_render = True
    print("FloorCollider added")

for obj in (cape, robe):
    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.quality = 20
    cset.mass = 0.6
    cset.tension_stiffness = 40.0
    cset.compression_stiffness = 25.0
    cset.shear_stiffness = 30.0
    cset.bending_stiffness = 60.0
    cset.tension_damping = 25.0
    cset.compression_damping = 25.0
    cset.shear_damping = 25.0
    cset.bending_damping = 25.0
    cset.air_damping = 8.0
    ccol = cl.collision_settings
    ccol.collision_quality = 6
    ccol.distance_min = 0.008
    ccol.use_self_collision = False          # was fighting every substep
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
print("SAVED; P3 FIXER R3 DONE")
