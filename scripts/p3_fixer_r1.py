"""
PHASE 3 FIXER r1 — motion + cloth flaw pass on models/godwyn_mocap.blend.

Run (fresh process on the saved blend):
  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r1.py

Fixes:
  1. Per-frame grounding curve: min foot Z per frame, jump window f29-32
     interpolated (keeps airborne height), clamped, 5-frame gaussian smoothed,
     subtracted from the Hips location keys -> contact windows sit at Z=0.
  2. Cloth blow-up: heavier/damped cloth (mass .6, air 4, t/c/s damping 15,
     bend damping 10, quality 15, collision_quality 6, self coll dist/friction
     up) on CapeGrid/RobeGrid.
  3. Grid resolution +1 subdivision so the SD bind has real support (kills the
     gold shard extrapolation spikes), SD falloff 2.5->2.0, ClothCS 8->20.
  4. Cape bib: BodyCollider rebuilt with wider torso coverage (keep threshold
     0.35->0.6 so shoulders/upper chest under the cape are collider),
     thickness_outer 0.004->0.02; pin gradient extended over cape row 2.
  5. Rebake -45..68, save.

char1 materials/UVs/skin weights, face, sword parenting: untouched.
Idempotent: grid subdivision is flag-guarded; collider is rebuilt by name;
grounding re-measures (re-run deltas ~0).
"""
import bpy
import bmesh
import re
import time
from mathutils import Vector
from mathutils.kdtree import KDTree

PREROLL = -45
CHAIN_RE = re.compile(r"^phys_(cape|robe)_(.+)_(\d+)$")

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
char = bpy.data.objects["char1"]
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))
print(f"clip {frames[0]}..{frames[-1]} arm_scale={s:.4f}")

act = arm.animation_data.action
slot = arm.animation_data.action_slot
cb = None
for layer in act.layers:
    for strip in layer.strips:
        c = strip.channelbag(slot)
        if c:
            cb = c
assert cb is not None

# ════════════════════════════════════════════════════════════════
# 1) PER-FRAME GROUNDING
# ════════════════════════════════════════════════════════════════
FOOT = ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase")

def min_foot_z(f):
    scene.frame_set(f)
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return min(ae.pose.bones[b].head.z for b in FOOT) * s  # heads only

z = {f: min_foot_z(f) for f in frames}
print("pre-ground minFootZ:",
      " ".join(f"{f}:{z[f]:.3f}" for f in frames[::6] + [frames[-1]]))

# grounding curve g: jump frames f29-32 get interpolated ground level from the
# takeoff/landing neighbours so the leap KEEPS its height
g = dict(z)
JF0, JF1 = 28, 33
for f in range(JF0 + 1, JF1):
    t = (f - JF0) / (JF1 - JF0)
    g[f] = g[JF0] * (1 - t) + g[JF1] * t
for f in frames:
    g[f] = min(max(g[f], 0.0), 0.25)          # clamp: never lift, cap at 25cm
# 5-frame gaussian [1,4,6,4,1]/16, edge-clamped
K = (1.0, 4.0, 6.0, 4.0, 1.0)
gs = {}
for f in frames:
    acc = wacc = 0.0
    for k, w in zip(range(-2, 3), K):
        fk = min(max(f + k, frames[0]), frames[-1])
        acc += w * g[fk]
        wacc += w
    gs[f] = acc / wacc
print("ground curve:",
      " ".join(f"{f}:{gs[f]:.3f}" for f in frames[::6] + [frames[-1]]))

pb = arm.pose.bones["Hips"]
M = pb.bone.matrix_local.to_3x3().inverted()
moved = 0
for fc in cb.fcurves:
    if fc.data_path != 'pose.bones["Hips"].location':
        continue
    for kp in fc.keyframe_points:
        f = int(round(kp.co.x))
        d = (M @ Vector((0.0, 0.0, -gs.get(f, 0.0) / s)))[fc.array_index]
        if abs(d) < 1e-9:
            continue
        kp.co.y += d
        kp.handle_left.y += d
        kp.handle_right.y += d
        moved += 1
    fc.update()
print(f"grounding: shifted {moved} hips keys")

z2 = {f: min_foot_z(f) for f in frames}
contact = [f for f in frames if not (JF0 < f < JF1)]
print(f"post-ground minFootZ: contact-min={min(z2[f] for f in contact):.4f} "
      f"contact-max={max(z2[f] for f in contact):.4f} "
      f"jump-apex={max(z2[f] for f in range(JF0, JF1 + 1)):.4f}")

# ════════════════════════════════════════════════════════════════
# 2) BODYCOLLIDER REBUILD — wider torso coverage, thicker
# ════════════════════════════════════════════════════════════════
old = bpy.data.objects.get("BodyCollider")
if old:
    bpy.data.objects.remove(old, do_unlink=True)

gi_cape = {gr.index for gr in char.vertex_groups if CHAIN_RE.match(gr.name)}
nv = len(char.data.vertices)
cape_all = [0.0] * nv
for v in char.data.vertices:
    cape_all[v.index] = sum(ge.weight for ge in v.groups if ge.group in gi_cape)
keep = [w < 0.6 for w in cape_all]          # was <0.35: shoulders now collider
print(f"collider keeps {sum(keep)}/{nv} verts (was thr .35, now .6)")

MW = char.matrix_world.copy()
mesh = char.data.copy()
mesh.name = "BodyCollider"
coll = bpy.data.objects.new("BodyCollider", mesh)
scene.collection.objects.link(coll)
src_pts, src_w = [], []
for v in char.data.vertices:
    if not keep[v.index]:
        continue
    src_pts.append(MW @ v.co)
    src_w.append([(ge.group, ge.weight) for ge in v.groups if ge.weight > 0.001])
kd = KDTree(len(src_pts))
for i, p in enumerate(src_pts):
    kd.insert(p, i)
kd.balance()

bm = bmesh.new()
bm.from_mesh(mesh)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep[v.index]],
                 context='VERTS')
for v in bm.verts:
    v.co = MW @ v.co
bm.to_mesh(mesh)
bm.free()
mesh.materials.clear()
coll.matrix_world.identity()
bpy.context.view_layer.objects.active = coll
rm = coll.modifiers.new("Remesh", 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = 0.05
bpy.ops.object.modifier_apply(modifier="Remesh")
ratio = min(1.0, 6000 / max(1, len(mesh.vertices)))
if ratio < 1.0:
    dec = coll.modifiers.new("Dec", 'DECIMATE')
    dec.ratio = ratio
    bpy.ops.object.modifier_apply(modifier="Dec")
print(f"collider remeshed+decimated -> {len(mesh.vertices)} verts")

for gr in char.vertex_groups:               # same order -> same indices
    coll.vertex_groups.new(name=gr.name)
vgs = {gr.index: gr for gr in coll.vertex_groups}
for v in mesh.vertices:
    _, si, _ = kd.find(v.co)
    for gi, w in src_w[si]:
        tgt = vgs.get(gi)
        if tgt:
            tgt.add([v.index], w, 'REPLACE')

disp = coll.modifiers.new("Shrink", 'DISPLACE')   # inside the skin
disp.direction = 'NORMAL'
disp.mid_level = 0.0
disp.strength = -0.035
amod = coll.modifiers.new("Armature", 'ARMATURE')
amod.object = arm
coll.modifiers.new("Collision", 'COLLISION')
cs = coll.collision
cs.thickness_outer = 0.02                   # was 0.004
cs.thickness_inner = 0.01
cs.damping = 0.9
cs.cloth_friction = 10.0
coll.hide_render = True
print("collider stack:", [m.name for m in coll.modifiers])

# ════════════════════════════════════════════════════════════════
# 3) GRID UPGRADE — +1 subdivision, pin gradient, calm cloth
# ════════════════════════════════════════════════════════════════
def row_estimates(obj):
    """per-vert weighted mean chain row from the bone vertex groups"""
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

for obj, is_cape in ((cape, True), (robe, False)):
    if not obj.get("p3_subdiv"):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                                  use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj["p3_subdiv"] = True
        print(f"{obj.name}: subdivided -> {len(obj.data.vertices)} verts "
              f"{len(obj.data.polygons)} tris")
    # pin gradient: rows 0-1 hard, cape row 2 ~0.5 (hangs from shoulders)
    est = row_estimates(obj)
    pin = obj.vertex_groups["pin"]
    hard, grad, free = [], {}, []
    for i, r in enumerate(est):
        if r <= 1.15:
            hard.append(i)
        elif is_cape and r < 3.0:
            grad[i] = 0.95 * (3.0 - r) / 1.85
        elif not is_cape and r < 2.0:
            grad[i] = 0.5 * (2.0 - r) / 0.85
        else:
            free.append(i)
    pin.add(hard, 1.0, 'REPLACE')
    for i, w in grad.items():
        pin.add([i], w, 'REPLACE')
    pin.remove(free)
    print(f"{obj.name}: pin hard={len(hard)} grad={len(grad)} free={len(free)}")

    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.vertex_group_mass = "pin"
    cset.quality = 15
    cset.mass = 0.6                          # was .3 — stops snapping
    cset.tension_stiffness = 30.0
    cset.compression_stiffness = 20.0
    cset.shear_stiffness = 25.0
    cset.bending_stiffness = 60.0
    cset.tension_damping = 15.0
    cset.compression_damping = 15.0
    cset.shear_damping = 15.0
    cset.bending_damping = 10.0
    cset.air_damping = 4.0                   # was 2.0
    ccol = cl.collision_settings
    ccol.collision_quality = 6               # was 4
    ccol.distance_min = 0.012
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.015           # was .01
    ccol.self_friction = 25.0                # was 5
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end

cs_mod = char.modifiers["ClothCS"]
cs_mod.iterations = 20                       # was 8
cs_mod.factor = 0.5

# ════════════════════════════════════════════════════════════════
# 4) SD REBIND at preroll (grid topology changed, hips moved)
# ════════════════════════════════════════════════════════════════
scene.frame_set(PREROLL)
cls = [o.modifiers["Cloth"] for o in (cape, robe)]
for cl in cls:
    cl.show_viewport = False
    cl.show_render = False
bpy.context.view_layer.objects.active = char
bpy.context.view_layer.update()
for mn in ("CapeSD", "RobeSD"):
    sd = char.modifiers[mn]
    sd.falloff = 2.0                         # was 2.5 (r1 4.0)
    with bpy.context.temp_override(object=char, active_object=char,
                                   selected_objects=[char]):
        if sd.is_bound:
            bpy.ops.object.surfacedeform_bind(modifier=mn)   # unbind
        bpy.ops.object.surfacedeform_bind(modifier=mn)       # bind
    assert sd.is_bound, f"{mn} rebind failed"
    print(f"{mn} re-bound, falloff={sd.falloff}")
for cl in cls:
    cl.show_viewport = True
    cl.show_render = True

# ════════════════════════════════════════════════════════════════
# 5) REBAKE + SAVE
# ════════════════════════════════════════════════════════════════
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R1 DONE")
