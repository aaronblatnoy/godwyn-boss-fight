"""
PHASE 3 FIXER r6 — kill the forward cape flip + post-whip clump (round-2 fixer).

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r6.py

r5 (time_scale 0.75 + rows 0-2 hard pin) only slowed the whip: the cape still
flips forward over the shoulder at f14-30, mummifies the chest, and never
recovers (towel-clump f44..end). Root-cause levers this round:

  1. FLIP: cape pin extended — rows 0-3.5 HARD (1.0), gradient to free by
     row 5.0 (min grad weight 0.3). The upper half of the cape rides the rig
     and geometrically cannot rotate past the shoulder plane.
  2. FLIP: weak backward wind (+Y = negated dive velocity) keyed f8..f34 so
     the free tail trails the body during the dive instead of overtaking it.
  3. CLUMP: air_damping 6 -> 2.5 (cape) / 3.0 (robe), cape mass 0.6 -> 0.8 —
     gravity can pull the tail back out to a hanging drape.
  4. INTERPENETRATION: object collision distance_min 0.008 -> 0.022,
     self-collision distance 0.01 -> 0.008 (collision_quality stays 6,
     sim quality stays 15, collider thickness_outer stays 0.015).
  5. SLAB: CapeGrid gets a SIMPLE Subdivision (1 level) BEFORE Cloth
     (833 -> ~3.3k sim verts), bending 60 -> 42 (-30%), time_scale 0.75 ->
     0.85 — fold energy comes back now that the flip is pinned out.
     CapeSD is re-bound (r12 recipe) because the grid's evaluated topology
     changes.

Rebake -45..68, save.
"""
import bpy
import re
import time
from mathutils import Vector

PREROLL = -45
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
char = bpy.data.objects["char1"]
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


# ── 1. cape pin: rows 0-3.5 hard, gradient to free by 5.0 ────────
est = row_estimates(cape)
pin = cape.vertex_groups["pin"]
hard, grad, free = [], {}, []
for i, r in enumerate(est):
    if r <= 3.55:
        hard.append(i)
    elif r < 5.0:
        w = (5.0 - r) / 1.45
        if w >= 0.3:
            grad[i] = w
        else:
            free.append(i)
    else:
        free.append(i)
pin.add(hard, 1.0, 'REPLACE')
for i, w in grad.items():
    pin.add([i], w, 'REPLACE')
if free:
    pin.remove(free)
print(f"CapeGrid pin: hard={len(hard)} grad={len(grad)} free={len(free)}")

# ── 2. backward wind during the dive (f8..f34) ───────────────────
if "CapeWind" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["CapeWind"], do_unlink=True)
s = arm.scale.x
hp = {}
for f in (10, 30):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    hp[f] = (arm.evaluated_get(dg).pose.bones["Hips"].head * s).copy()
vel = hp[30] - hp[10]
vel.z = 0.0
back = (-vel).normalized() if vel.length > 1e-3 else Vector((0, 1, 0))
print(f"dive travel={tuple(round(c, 2) for c in vel)} -> wind dir "
      f"{tuple(round(c, 2) for c in back)}")
bpy.ops.object.effector_add(type='WIND',
                            location=hp[10] - back * 3.0 + Vector((0, 0, 1.3)))
wind = bpy.context.active_object
wind.name = "CapeWind"
wind.rotation_euler = back.to_track_quat('Z', 'Y').to_euler()
fs = wind.field
fs.strength = 0.0
fs.flow = 0.0
fs.noise = 0.0
for f, v in ((PREROLL, 0.0), (8, 0.0), (12, 250.0), (28, 250.0), (34, 0.0)):
    fs.strength = v
    fs.keyframe_insert("strength", frame=f)
print("CapeWind keyed: 0 @f8 -> 250 @f12-28 -> 0 @f34")

# ── 3+4. cloth dynamics + collision margins ──────────────────────
for obj, air, mass, bend, tsc in ((cape, 2.5, 0.8, 42.0, 0.85),
                                  (robe, 3.0, 0.6, 60.0, 0.85)):
    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.time_scale = tsc
    cset.air_damping = air
    cset.mass = mass
    cset.bending_stiffness = bend
    cset.quality = 15
    ccol = cl.collision_settings
    ccol.collision_quality = 6
    ccol.distance_min = 0.022
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.008
    ccol.self_friction = 10.0
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end
    print(f"{obj.name}: ts={tsc} air={air} mass={mass} bend={bend} "
          f"dmin=0.022 self=0.008")

coll = bpy.data.objects["BodyCollider"]
coll.collision.thickness_outer = 0.015
print(f"BodyCollider thickness_outer={coll.collision.thickness_outer:.3f}")

# ── 5. cape resolution: SIMPLE subdiv before Cloth, rebind CapeSD ─
if "PreSubd" not in cape.modifiers:
    sub = cape.modifiers.new("PreSubd", 'SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 1
    sub.render_levels = 1
    ci = cape.modifiers.find("Cloth")
    while cape.modifiers.find("PreSubd") > ci:
        cape.modifiers.move(cape.modifiers.find("PreSubd"),
                            cape.modifiers.find("PreSubd") - 1)
        ci = cape.modifiers.find("Cloth")
print("CapeGrid stack:", [m.name for m in cape.modifiers])

# rebind CapeSD against the new (subdivided) rest topology — cloth hidden,
# PostSmooth active, at PREROLL (r12 recipe)
scene.frame_set(PREROLL)
cls = [o.modifiers["Cloth"] for o in (cape, robe)]
for cl in cls:
    cl.show_viewport = False
    cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
sd = char.modifiers["CapeSD"]
with bpy.context.temp_override(object=char, active_object=char,
                               selected_objects=[char]):
    if sd.is_bound:
        bpy.ops.object.surfacedeform_bind(modifier="CapeSD")  # unbind
    bpy.ops.object.surfacedeform_bind(modifier="CapeSD")      # bind
assert sd.is_bound, "CapeSD rebind FAILED"
print("CapeSD re-bound against subdivided grid")
for cl in cls:
    cl.show_viewport = True
    cl.show_render = True

# ── rebake ───────────────────────────────────────────────────────
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R6 DONE")
