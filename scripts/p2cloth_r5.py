"""
Round 5 — binarize pins (hard anchors only, no soft-spring patchwork),
thick-cloth stiffness, slight pressure so the closed remesh shell keeps
volume instead of deflating, collider back on (shrunk inside the body).
"""
import bpy
import time

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
collider = bpy.data.objects["BodyCollider"]
PREROLL = -20

# ── binarize pin group ───────────────────────────────────────────
me = proxy.data
vg = proxy.vertex_groups["pin"]
pi = vg.index
hard, freed = [], []
for v in me.vertices:
    w = 0.0
    for ge in v.groups:
        if ge.group == pi:
            w = ge.weight
    (hard if w > 0.45 else freed).append(v.index)
vg.add(hard, 1.0, 'REPLACE')
vg.remove(freed)
print(f"pins binarized: {len(hard)} hard anchors, {len(freed)} free verts")

# ── cloth: heavy thick cloth ─────────────────────────────────────
cl = proxy.modifiers["Cloth"]
cset = cl.settings
cset.quality = 12
cset.mass = 0.8
cset.tension_stiffness = 40.0
cset.compression_stiffness = 25.0
cset.shear_stiffness = 25.0
cset.bending_stiffness = 25.0
cset.tension_damping = 10.0
cset.compression_damping = 10.0
cset.shear_damping = 10.0
cset.bending_damping = 2.0
cset.air_damping = 2.0
cset.use_pressure = True
cset.uniform_pressure_force = 1.0
ccol = cl.collision_settings
ccol.collision_quality = 3
ccol.distance_min = 0.004
ccol.use_self_collision = False

# ── collider back on ─────────────────────────────────────────────
if not any(m.type == 'COLLISION' for m in collider.modifiers):
    collider.modifiers.new("Collision", 'COLLISION')
cs = collider.collision
cs.thickness_outer = 0.004
cs.thickness_inner = 0.005
cs.damping = 0.9
cs.cloth_friction = 8.0

old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"rebaked in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; R5 DONE")
