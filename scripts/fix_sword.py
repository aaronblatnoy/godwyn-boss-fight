"""
fix_sword.py — Phase 1: separate the sword into Godwyn_Sword, relax the
right-hand grip, bone-parent the sword to RightHand, save blend + previews.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/fix_sword.py 2>&1

Invariants:
  - Armature 'Armature' (24 bones) + char1 skinning stay intact.
  - Baked textures / UVs / material untouched (vert moves only).
  - Shape keys preserved: all vert edits are applied through shape-key
    points (basis + every key) when shape keys exist.
"""
import bpy
import bmesh
import os
import sys
import math
from collections import deque
from mathutils import Vector, Matrix

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO, "models", "godwyn_game.glb")
BLEND_OUT = os.path.join(REPO, "models", "godwyn_sword.blend")
PREVIEW_DIR = "/tmp/sword_previews"

# ─────────────────────────────────────────────────────────────────
# TUNABLES (iterated per critique round)
# ─────────────────────────────────────────────────────────────────
P = dict(
    # finger curl (vertex-level, rest mesh)
    do_curl=False,
    curl_deg=55.0,          # max total curl angle at fingertips
    curl_start_frac=0.55,   # fraction along hand bone where curl begins
    curl_range=0.14,        # meters over which curl ramps to max
    curl_axis_sign=1.0,     # flip if fingers curl the wrong way
    thumb_x_min=None,       # local-x band to EXCLUDE from curl (thumb)
    thumb_x_max=None,
    # wrist pose (pose-mode, non-destructive)
    wrist_euler_deg=(0.0, 0.0, 0.0),
    forearm_euler_deg=(0.0, 0.0, 0.0),
    # left arm re-pose (it used to rest on the pommel; let it hang)
    left_arm_euler_deg=(20.0, 0.0, 0.0),
    left_forearm_euler_deg=(0.0, 0.0, 0.0),
    # sword bbox (world): the planted sword at the character's LEFT side
    sword_box=((0.42, -0.92, -0.01), (0.92, -0.40, 2.05)),
    glove_z_cut=1.80,       # in-box islands entirely above this z = glove plates
    glove_rad=0.32,         # ...and mean dist to LeftHand joint below this
    # sword placement
    snap_to_fist=True,      # move grip point (below pommel) into the fist
    grip_from_pommel=0.30,  # grip point distance below pommel along axis
    tip_dir=(-0.62, -0.18, -0.76),  # target world dir grip->tip (None = keep)
    axial_shift=0.0,        # slide sword along blade axis (+ = toward tip)
    sword_rot=[],           # extra world rotations about grip pivot
    sword_offset=(0.0, 0.0, 0.0),   # final manual world nudge
)

# ─────────────────────────────────────────────────────────────────
# 0. Clean scene + import
# ─────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials,
             bpy.data.images, bpy.data.actions):
    for blk in list(coll):
        if blk.users == 0:
            coll.remove(blk)

print(f"[fix_sword] importing {GLB}")
bpy.ops.import_scene.gltf(filepath=GLB)

arm = bpy.data.objects.get("Armature")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print(f"[fix_sword] imported objects: "
      f"{[(o.name, o.type, len(o.data.vertices) if o.type=='MESH' else '') for o in bpy.data.objects]}")
mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))
# drop stray helper objects (e.g. Icosphere) that came along in the glb
for o in meshes:
    if o is not mesh_obj:
        print(f"[fix_sword] removing stray mesh object {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)
assert arm is not None, "Armature not found"
assert mesh_obj is not None, "mesh not found"
me = mesh_obj.data
print(f"[fix_sword] mesh={mesh_obj.name} verts={len(me.vertices)} "
      f"faces={len(me.polygons)} vgroups={len(mesh_obj.vertex_groups)} "
      f"shapekeys={me.shape_keys.key_blocks.keys() if me.shape_keys else None}")
print(f"[fix_sword] mesh matrix_world:\n{mesh_obj.matrix_world}")
print(f"[fix_sword] arm  matrix_world:\n{arm.matrix_world}")

bones_before = sorted(b.name for b in arm.data.bones)
vgroups_before = sorted(g.name for g in mesh_obj.vertex_groups)
n_bones_before = len(bones_before)

rh_bone = arm.data.bones["RightHand"]
rf_bone = arm.data.bones["RightForeArm"]
awm = arm.matrix_world
rh_head_w = awm @ rh_bone.head_local
rf_head_w = awm @ rf_bone.head_local
# glTF bone tails are heuristic garbage — derive hand direction from joints
hand_dir = (rh_head_w - rf_head_w).normalized()
print(f"[fix_sword] RightHand head_w={tuple(round(c,4) for c in rh_head_w)} "
      f"RightForeArm head_w={tuple(round(c,4) for c in rf_head_w)} "
      f"hand_dir={tuple(round(c,3) for c in hand_dir)}")

mwm = mesh_obj.matrix_world
rh_gi = mesh_obj.vertex_groups["RightHand"].index

def rh_weight(v):
    for g in v.groups:
        if g.group == rh_gi:
            return g.weight
    return 0.0

# hand centroid: strongly hand-weighted verts near the wrist joint
hand_pts = [mwm @ v.co for v in me.vertices
            if rh_weight(v) > 0.6 and (mwm @ v.co - rh_head_w).length < 0.35]
hand_c = sum(hand_pts, Vector()) / max(len(hand_pts), 1)
print(f"[fix_sword] hand verts(within 35cm of wrist)={len(hand_pts)} "
      f"centroid={tuple(round(c,4) for c in hand_c)}")

# ─────────────────────────────────────────────────────────────────
# 1. Find the sword island (seed low near the ground, grow linked)
# ─────────────────────────────────────────────────────────────────
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()

# The mesh is a shell soup (~12.6k islands). The sword = the planted
# greatsword at the character's LEFT side (+X): every island whose bbox is
# FULLY contained in P['sword_box'] (blade isl 0.58..0.68 x, plus hilt/
# crossguard/pommel shells around z 1.4..2.0).
blo, bhi = Vector(P["sword_box"][0]), Vector(P["sword_box"][1])
world_co = [mwm @ v.co for v in bm.verts]

lh_gi = mesh_obj.vertex_groups["LeftHand"].index
lh_head_w = awm @ arm.data.bones["LeftHand"].head_local
print(f"[fix_sword] LeftHand head_w={tuple(round(c,4) for c in lh_head_w)}")

def lh_weight(v):
    for g in v.groups:
        if g.group == lh_gi:
            return g.weight
    return 0.0

seen = set()
visited = set()
n_islands = 0
n_lh_skipped = 0
for v0 in bm.verts:
    if v0.index in seen:
        continue
    comp = {v0.index}
    dq = deque([v0])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index not in comp:
                comp.add(o.index)
                dq.append(o)
    seen |= comp
    inside = all(
        blo.x <= world_co[i].x <= bhi.x and
        blo.y <= world_co[i].y <= bhi.y and
        blo.z <= world_co[i].z <= bhi.z
        for i in comp)
    if not inside:
        continue
    # The left glove drapes over the pommel and its shells sit fully inside
    # sword_box — do NOT steal them. Glove shells are (a) tight around the
    # LeftHand joint and (b) nearly fully LeftHand-weighted; sword shells
    # carry softer auto-skin weights.
    lws = [lh_weight(me.vertices[i]) for i in comp]
    mean_lw = sum(lws) / len(lws)
    mean_d = sum((world_co[i] - lh_head_w).length for i in comp) / len(comp)
    z_min = min(world_co[i].z for i in comp)
    if z_min > P["glove_z_cut"] and mean_d < P["glove_rad"]:
        n_lh_skipped += 1
        zs = [world_co[i].z for i in comp]
        print(f"[fix_sword]   glove shell kept on body: n={len(comp)} "
              f"lw={mean_lw:.2f} d={mean_d:.3f} z={min(zs):.2f}..{max(zs):.2f}")
        continue
    visited |= comp
    n_islands += 1
print(f"[fix_sword] sword = {n_islands} islands fully inside "
      f"{P['sword_box']} (skipped {n_lh_skipped} LeftHand-weighted islands)")

assert visited, "no sword islands found inside sword_box"
isl_w = [world_co[i] for i in visited]
lo = Vector((min(c.x for c in isl_w), min(c.y for c in isl_w), min(c.z for c in isl_w)))
hi = Vector((max(c.x for c in isl_w), max(c.y for c in isl_w), max(c.z for c in isl_w)))
print(f"[fix_sword] sword island: {len(visited)} verts  "
      f"bbox lo={tuple(round(c,3) for c in lo)} hi={tuple(round(c,3) for c in hi)}")
ws = [rh_weight(me.vertices[i]) for i in list(visited)[:2000]]
print(f"[fix_sword] island RightHand weight sample: min={min(ws):.3f} max={max(ws):.3f}")

# sanity: island must not contain the body (head is above z=2.7)
assert hi.z < 2.3, f"island reached z={hi.z:.2f} — grabbed the body, aborting"
assert len(visited) < 100000, "island too large — grabbed the body, aborting"
bm.free()

# sword long axis: blade tip (ground) -> pommel top; grip sits just
# below the pommel (where the left palm used to rest)
tip = min(isl_w, key=lambda c: c.z)          # blade tip (ground)
top = max(isl_w, key=lambda c: c.z)          # pommel end
axis_dir = (top - tip).normalized()
grip_pivot = top - axis_dir * P["grip_from_pommel"]
print(f"[fix_sword] sword axis {tuple(round(c,3) for c in tip)} -> "
      f"{tuple(round(c,3) for c in top)}  grip_pivot="
      f"{tuple(round(c,3) for c in grip_pivot)}")

# ─────────────────────────────────────────────────────────────────
# 2. Separate island -> Godwyn_Sword
# ─────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='DESELECT')
mesh_obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_obj
for v in me.vertices:
    v.select = v.index in visited
for e in me.edges:
    e.select = all(i in visited for i in e.vertices)
for f in me.polygons:
    f.select = all(i in visited for i in f.vertices)

objs_before = set(bpy.data.objects)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.separate(type='SELECTED')
bpy.ops.object.mode_set(mode='OBJECT')
new_objs = set(bpy.data.objects) - objs_before
assert len(new_objs) == 1, f"expected 1 new object, got {len(new_objs)}"
sword = new_objs.pop()
sword.name = "Godwyn_Sword"
sword.data.name = "Godwyn_Sword"
print(f"[fix_sword] separated: {sword.name} verts={len(sword.data.vertices)} "
      f"mats={[m.name if m else None for m in sword.data.materials]}")
print(f"[fix_sword] body now: verts={len(me.vertices)} faces={len(me.polygons)}")

# sword is a rigid prop: drop armature modifier / vgroups / shapekeys
for m in list(sword.modifiers):
    if m.type == 'ARMATURE':
        sword.modifiers.remove(m)
sword.vertex_groups.clear()
if sword.data.shape_keys:
    bpy.context.view_layer.objects.active = sword
    sword.shape_key_clear()
# strip debris shells that rode along: micro-fragments anywhere, plus the
# torn glove/drapery shreds clustered around the pommel top (where the left
# palm used to rest). The real hilt shell is large and runs down the handle,
# so a size cap keeps it safe.
_swm = sword.matrix_world
sbm = bmesh.new()
sbm.from_mesh(sword.data)
sbm.verts.ensure_lookup_table()
sseen = set()
kill = []
n_pommel_shreds = 0
for v0 in sbm.verts:
    if v0.index in sseen:
        continue
    comp = {v0.index}
    dq = deque([v0])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index not in comp:
                comp.add(o.index)
                dq.append(o)
    sseen |= comp
    if len(comp) < 15:
        kill.extend(comp)
        continue
    if len(comp) < 500:
        dmax = max((_swm @ sbm.verts[i].co - top).length for i in comp)
        if dmax < 0.20:
            kill.extend(comp)
            n_pommel_shreds += 1
            print(f"[fix_sword]   pommel shred killed: n={len(comp)} dmax={dmax:.3f}")
if kill:
    sbm.verts.ensure_lookup_table()
    bmesh.ops.delete(sbm, geom=[sbm.verts[i] for i in kill], context='VERTS')
    sbm.to_mesh(sword.data)
    sword.data.update()
    print(f"[fix_sword] removed {len(kill)} debris verts from sword")
sbm.free()

uvs = [l.name for l in sword.data.uv_layers]
print(f"[fix_sword] sword uv_layers={uvs} (must be non-empty)")
assert uvs, "sword lost its UVs!"

# ─────────────────────────────────────────────────────────────────
# 3. Wrist / forearm pose (non-destructive, pose mode)
# ─────────────────────────────────────────────────────────────────
def pose_bone_euler(name, deg):
    if not any(abs(a) > 1e-6 for a in deg):
        return
    pb = arm.pose.bones[name]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in deg)
    print(f"[fix_sword] posed {name} euler={deg}")

pose_bone_euler("RightHand", P["wrist_euler_deg"])
pose_bone_euler("RightForeArm", P["forearm_euler_deg"])
pose_bone_euler("LeftArm", P["left_arm_euler_deg"])
pose_bone_euler("LeftForeArm", P["left_forearm_euler_deg"])
bpy.context.view_layer.update()

# ─────────────────────────────────────────────────────────────────
# 4. Finger curl (vertex-level on rest mesh, shape-key aware)
# ─────────────────────────────────────────────────────────────────
if P["do_curl"]:
    # build a stable hand frame: Y along forearm->wrist, X = curl hinge axis
    y_ax = hand_dir.copy()
    ref = axis_dir if abs(axis_dir.dot(y_ax)) < 0.95 else Vector((0, 0, 1))
    x_ax = y_ax.cross(ref).normalized()
    z_ax = x_ax.cross(y_ax).normalized()
    B = Matrix((
        (x_ax.x, y_ax.x, z_ax.x, rh_head_w.x),
        (x_ax.y, y_ax.y, z_ax.y, rh_head_w.y),
        (x_ax.z, y_ax.z, z_ax.z, rh_head_w.z),
        (0, 0, 0, 1),
    ))
    Binv = B.inverted()
    hand_len = (hand_c - rh_head_w).length * 2.0   # approx wrist->fingertip
    d0 = hand_len * P["curl_start_frac"]
    max_ang = math.radians(P["curl_deg"])
    rng = P["curl_range"]
    sgn = P["curl_axis_sign"]
    mwm_inv = mwm.inverted()

    deltas = {}
    for v in me.vertices:
        if rh_weight(v) < 0.4:
            continue
        loc = Binv @ (mwm @ v.co)
        if loc.y <= d0:
            continue
        if P["thumb_x_min"] is not None and \
           P["thumb_x_min"] <= loc.x <= P["thumb_x_max"]:
            continue
        t01 = min((loc.y - d0) / rng, 1.0)
        t01 = t01 * t01 * (3 - 2 * t01)      # smoothstep
        ang = sgn * max_ang * t01
        R = Matrix.Rotation(ang, 4, 'X')
        hinge = Vector((loc.x, d0, loc.z * 0.35))
        newloc = R @ (loc - Vector((0, d0, 0))) + Vector((0, d0, 0))
        neww = B @ newloc
        deltas[v.index] = (mwm_inv @ neww) - v.co
    print(f"[fix_sword] curling {len(deltas)} finger verts "
          f"(deg={P['curl_deg']} start={P['curl_start_frac']} sign={sgn})")

    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            for i, d in deltas.items():
                kb.data[i].co += d
        for i, d in deltas.items():
            me.vertices[i].co += d
    else:
        for i, d in deltas.items():
            me.vertices[i].co += d
    me.update()

# ─────────────────────────────────────────────────────────────────
# 5. Bone-parent sword to RightHand (world transform preserved)
# ─────────────────────────────────────────────────────────────────
mw_saved = sword.matrix_world.copy()
sword.parent = arm
sword.parent_type = 'BONE'
sword.parent_bone = 'RightHand'
bpy.context.view_layer.update()
sword.matrix_world = mw_saved
bpy.context.view_layer.update()
print(f"[fix_sword] sword parented to bone '{sword.parent_bone}' of {arm.name}")

# ─────────────────────────────────────────────────────────────────
# 6. Reposition / reorient sword in the grip
# ─────────────────────────────────────────────────────────────────
# fist center: mass of finger/palm verts 8-24cm from wrist along hand_dir
fist_pts = []
for v in me.vertices:
    if rh_weight(v) < 0.5:
        continue
    w = mwm @ v.co
    d = (w - rh_head_w).dot(hand_dir)
    if 0.08 <= d <= 0.24:
        fist_pts.append(w)
fist_c = sum(fist_pts, Vector()) / max(len(fist_pts), 1)
print(f"[fix_sword] fist verts={len(fist_pts)} "
      f"center={tuple(round(c,4) for c in fist_c)}")

if P["snap_to_fist"]:
    # move the grip point (below the pommel) into the fist center
    snap = fist_c - grip_pivot
    sword.matrix_world = Matrix.Translation(snap) @ sword.matrix_world
    grip_pivot = fist_c
    print(f"[fix_sword] snapped sword grip to fist: shift="
          f"{tuple(round(c,4) for c in snap)}")

if P["tip_dir"] is not None:
    # tip/top captured pre-snap; direction is translation-invariant
    cur_dir = (tip - top).normalized()   # pommel->tip direction
    tgt = Vector(P["tip_dir"]).normalized()
    q = cur_dir.rotation_difference(tgt)
    R = q.to_matrix().to_4x4()
    Tp = Matrix.Translation(grip_pivot)
    sword.matrix_world = Tp @ R @ Tp.inverted() @ sword.matrix_world
    print(f"[fix_sword] rotated blade: cur_dir={tuple(round(c,3) for c in cur_dir)} "
          f"-> {tuple(round(c,3) for c in tgt)}")

if abs(P["axial_shift"]) > 1e-9:
    tgt_axis = Vector(P["tip_dir"]).normalized() if P["tip_dir"] else (tip - top).normalized()
    sword.matrix_world = Matrix.Translation(tgt_axis * P["axial_shift"]) @ sword.matrix_world
    print(f"[fix_sword] axial shift {P['axial_shift']}m toward tip")

for ax, deg in P["sword_rot"]:
    R = Matrix.Rotation(math.radians(deg), 4, ax)
    Tp = Matrix.Translation(grip_pivot)
    sword.matrix_world = Tp @ R @ Tp.inverted() @ sword.matrix_world
if any(abs(c) > 1e-9 for c in P["sword_offset"]):
    sword.matrix_world = Matrix.Translation(Vector(P["sword_offset"])) @ sword.matrix_world
bpy.context.view_layer.update()
if P["sword_rot"] or any(abs(c) > 1e-9 for c in P["sword_offset"]):
    print(f"[fix_sword] sword transformed: rot={P['sword_rot']} off={P['sword_offset']}")

sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
slo = Vector((min(c.x for c in sw_pts), min(c.y for c in sw_pts), min(c.z for c in sw_pts)))
shi = Vector((max(c.x for c in sw_pts), max(c.y for c in sw_pts), max(c.z for c in sw_pts)))
print(f"[fix_sword] sword FINAL world bbox lo={tuple(round(c,3) for c in slo)} "
      f"hi={tuple(round(c,3) for c in shi)}  fist_c={tuple(round(c,3) for c in fist_c)}")

# ─────────────────────────────────────────────────────────────────
# 7. Rig-intact assertions
# ─────────────────────────────────────────────────────────────────
assert sorted(b.name for b in arm.data.bones) == bones_before
assert len(arm.data.bones) == n_bones_before
assert sorted(g.name for g in mesh_obj.vertex_groups) == vgroups_before
assert any(m.type == 'ARMATURE' and m.object == arm for m in mesh_obj.modifiers), \
    "body lost its armature modifier"
assert mesh_obj.data.uv_layers, "body lost UVs"
print(f"[fix_sword] RIG INTACT: {n_bones_before} bones, "
      f"{len(vgroups_before)} vgroups, armature modifier + UVs present")

# ─────────────────────────────────────────────────────────────────
# 8. Previews (EEVEE): hand closeups + full body
# ─────────────────────────────────────────────────────────────────
os.makedirs(PREVIEW_DIR, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.film_transparent = False
world = bpy.data.worlds.new("PrevWorld") if scene.world is None else scene.world
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.18, 0.18, 0.20, 1.0)
    bg.inputs[1].default_value = 1.0

sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun", 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("PrevFill", bpy.data.lights.new("PrevFill", 'AREA'))
fill.data.energy = 300
fill.data.size = 4.0
fill.location = hand_c + Vector((0.5, -1.5, 0.6))
scene.collection.objects.link(fill)

cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(cam_obj, frm, to):
    cam_obj.location = frm
    d = (to - frm)
    cam_obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

target = fist_c  # grip center
shots = [
    ("hand_front", target + Vector((-0.42, -0.58, 0.08)), target, 50),
    ("hand_side",  target + Vector((-0.72, 0.06, 0.04)),  target, 50),
    ("hand_low",   target + Vector((-0.38, -0.62, -0.45)), target, 45),
    ("full_body",  Vector((-2.6, -3.6, 1.9)), Vector((-0.2, 0, 1.2)), 35),
    ("full_front", Vector((0, -4.2, 1.5)), Vector((0, 0, 1.4)), 40),
]
for name, frm, to, lens in shots:
    cam.data.lens = lens
    aim(cam, frm, to)
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[fix_sword] rendered {scene.render.filepath}")

# debug: sword alone from the hand_front camera (verify placement)
mesh_obj.hide_render = True
cam.data.lens = shots[0][3]
aim(cam, shots[0][1], shots[0][2])
scene.render.filepath = os.path.join(PREVIEW_DIR, "debug_sword_only.png")
bpy.ops.render.render(write_still=True)
mesh_obj.hide_render = False
print(f"[fix_sword] rendered {scene.render.filepath}")

# debug: LEFT hand on body only (did the glove survive the separation?)
sword.hide_render = True
lh_head_w = awm @ arm.data.bones["LeftHand"].head_local
cam.data.lens = 50
aim(cam, lh_head_w + Vector((0.65, -0.85, 0.35)), lh_head_w + Vector((0, 0, -0.1)))
scene.render.filepath = os.path.join(PREVIEW_DIR, "debug_left_hand.png")
bpy.ops.render.render(write_still=True)
sword.hide_render = False
print(f"[fix_sword] rendered {scene.render.filepath}")

# ─────────────────────────────────────────────────────────────────
# 9. Save blend
# ─────────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"[fix_sword] saved {BLEND_OUT}")
print("[fix_sword] DONE")
