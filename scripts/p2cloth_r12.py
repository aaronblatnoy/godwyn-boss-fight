"""
Round 12 — anti-crumple pass:
  grids: lighter mass, high bending, self-collision, post-cloth Smooth
         (same topology, SD binding stays valid)
  char1: Corrective Smooth after the SD mods over the cloth region
  rebind (with grid Smooth active at rest), rebake.
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
    cset.mass = 0.3
    cset.bending_stiffness = 60.0
    cset.bending_damping = 5.0
    ccol = cl.collision_settings
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.01
    ccol.self_friction = 5.0
    if "PostSmooth" not in obj.modifiers:
        sm = obj.modifiers.new("PostSmooth", 'SMOOTH')
        sm.factor = 0.6
        sm.iterations = 3
    print(obj.name, "stack:", [m.name for m in obj.modifiers])

# char1: union vgroup + corrective smooth after SDs
gc = char.vertex_groups["cape_sd"].index
gr = char.vertex_groups["robe_sd"].index
union = {}
for v in char.data.vertices:
    w = 0.0
    for ge in v.groups:
        if ge.group in (gc, gr):
            w = max(w, ge.weight)
    if w > 0.0:
        union[v.index] = w
if "cloth_smooth" in char.vertex_groups:
    char.vertex_groups.remove(char.vertex_groups["cloth_smooth"])
vg = char.vertex_groups.new(name="cloth_smooth")
for i, w in union.items():
    vg.add([i], w, 'REPLACE')
print(f"cloth_smooth verts: {len(union)}")

if "ClothCS" not in char.modifiers:
    cs = char.modifiers.new("ClothCS", 'CORRECTIVE_SMOOTH')
else:
    cs = char.modifiers["ClothCS"]
cs.vertex_group = "cloth_smooth"
cs.factor = 0.5
cs.iterations = 8
cs.smooth_type = 'LENGTH_WEIGHTED'
cs.use_only_smooth = False
cs.use_pin_boundary = False
print("char1 stack:", [m.name for m in char.modifiers])

# rebind (cloth off, PostSmooth ON so its rest effect is baked into the bind)
scene.frame_set(PREROLL)
cls = [o.modifiers["Cloth"] for o in (cape, robe)]
for cl in cls:
    cl.show_viewport = False
    cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
for mn in ("CapeSD", "RobeSD"):
    sd = char.modifiers[mn]
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
print("SAVED; R12 DONE")
