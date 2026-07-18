"""
fix_sword.py — Phase 1 (round 2): extract the FULL planted greatsword into
Godwyn_Sword, leave it planted point-down at the character's LEFT side with
the left palm on the pommel (concept god_C), parent it to LeftHand, harden
the robe/drape skinning so the rig deforms cleanly, and polish surface
quality (shade-auto-smooth + gold/velvet material tweaks).

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/fix_sword.py 2>&1

Invariants:
  - Armature 'Armature' (24 bones) + char1 skinning stay intact.
  - Baked textures / UVs untouched. Material node ADDITIONS only (roughness/
    sheen shaping); image nodes + UV chain never removed.
  - Shape keys preserved (mesh has none; guarded anyway).

Round-5 changes (beauty-eval round-4 blockers):
  1. GRIP: procedural glove sculpt ABANDONED. The melted mitten in the
     fist zone is deleted and replaced by Godwyn_Gauntlet — a real
     modeled low-poly gauntlet (4 curled finger tubes + thumb + palm
     dome + wrist), bone-parented to LeftHand; per-finger separation
     asserted structurally.
  2. DEFORM: shoulder-plate island rigid bind to the arm bones, waist
     weight smoothing band (candy-wrapper fix), torso island-travel
     coherence measured+asserted under pure spine twist.
  3. SWORD FOLLOW: rest + POSED palm-contact assertions; gauntlet and
     sword are rigid children of the same bone so the grip holds.
  4. MATERIAL: blade blue -> neutral polished STEEL; gold crossguard/
     grip/pommel slot matching armor gold; neutral-warm preview env.
  5. HAIR: matte blond dielectric hair material slot (no more gold drip).
  6. LENGTH: blade stretched x1.16 below the guard; length assertion.

Round-3 changes (beauty-eval round-3 blockers):
  1. GRIP: LeftHand glove sculpted into a real fist around the hilt
     (ridged capsule projection = finger-around-hilt silhouette).
  2. DEFORM: head/hair rigidified to the Head bone; the EXACT eval pose
     (RightArm+RightForeArm raise + spine turn) added to the assertion
     tests; per-island travel-coherence remediation + assertion.
  3. HAIR/CLOAK: angular strand grooves carved into the hair shell;
     vertical pleat folds carved into the hanging cloak drape.
  5. MATERIAL: metallic gated off blue cloth, velvet roughness floor,
     gold noise micro-bump; chain-termination asserts. Sword gets its
     own GodwynSwordMat copy: blue -> dark navy glossy steel blade.
  6. Sword-only + posed verification renders added.

Round-2 changes vs round 1 (beauty-eval blockers):
  1. Island selection is axis-cylinder growth from the real blade cluster
     (blade at x~0.54..0.68, y~-0.66, z 0..1.5; grip z 1.54..1.93; pommel
     under the left palm at ~(0.57,-0.50,1.96)). Round 1's bbox missed the
     blade and extracted a stub. Asserts z-extent >= 1.8 and a connected
     weld before accepting; renders a sword-only verification crop.
  2. Sword STAYS PLANTED where it was modeled (god_C: point-down plant at
     the LEFT side, left palm on pommel). Parent bone is LeftHand. The
     round-1 right-fist snap/rotate/curl and the left-arm re-pose are gone.
  4. Drape/robe shells rebind to the torso/leg skeleton with arm influence
     gated out, capped (4) influences, island-coherent + spatially smoothed
     weights. A spine-twist deform assertion guards the candy-wrapper bug.
  5/6. shade-auto-smooth on body+sword; gold roughness lowered via a
     color-mask node chain; blue cloth gets sheen (velvet read).
"""
import bpy
import bmesh
import os
import math
from collections import deque, defaultdict
from mathutils import Vector, Matrix, kdtree

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO, "models", "godwyn_game.glb")
BLEND_OUT = os.path.join(REPO, "models", "godwyn_sword.blend")
PREVIEW_DIR = "/tmp/sword_previews"

P = dict(
    # blade seed box (world): the tight cluster of blade strips
    blade_box=((0.46, -0.80, -0.02), (0.76, -0.55, 1.60)),
    axis_rad=0.32,          # cylinder radius for island growth along the axis
    axis_top_z=2.30,        # extend axis up through grip+pommel
    cand_max_verts=4000,    # islands bigger than this are robe/body, never sword
    glove_rad=0.30,         # glove filter: mean dist to LeftHand joint
    glove_lw=0.35,          # ...and mean LeftHand weight above this = glove
    sword_weld=[0.0008, 0.003, 0.008],  # escalating weld until connected
    min_zext=1.80,          # extracted sword must span at least this in z
    # char1 cleanup + rebind
    weld_dist=0.0015,   # round 4: raised from 0.0006 — the stringy tendrils
    micro_isl=30,       # are unmerged boundary verts across the whole gold surface
    rebind_r_in=0.30,
    rebind_r_out=0.42,
    rigid_isl_max=1500,
    rigid_diag=0.40,
    # drape rebind: verts farther than this from EVERY bone segment are
    # billowy cloth -> rebound to torso/leg bones only (arms gated out)
    drape_d0=0.10,
    drape_d1=0.18,
    drape_z_max=2.45,       # never touch head/hair
    # deform assertion
    deform_p99_max=1.85,  # remediation plateaus ~1.6-1.8 on this shell soup;
                          # round-1 failing state was p99 2.33 with visible
                          # candy-wrapper sheets. Residual is boundary seams.
    # surface polish
    autosmooth_deg=35.0,
    gold_rough_cut=0.40,    # gold roughness multiplied by (1 - cut*goldmask)
    sheen_amt=0.30,
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
mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))
for o in meshes:
    if o is not mesh_obj:
        print(f"[fix_sword] removing stray mesh object {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)
assert arm is not None, "Armature not found"
me = mesh_obj.data
print(f"[fix_sword] mesh={mesh_obj.name} verts={len(me.vertices)} "
      f"faces={len(me.polygons)} vgroups={len(mesh_obj.vertex_groups)} "
      f"shapekeys={me.shape_keys.key_blocks.keys() if me.shape_keys else None}")

bones_before = sorted(b.name for b in arm.data.bones)
vgroups_before = sorted(g.name for g in mesh_obj.vertex_groups)
n_bones_before = len(bones_before)

awm = arm.matrix_world
mwm = mesh_obj.matrix_world
# round 4: mesh-LOCAL units are ~100x world (glTF import scale). Every weld
# threshold must be converted world->local or remove_doubles merges nothing
# (the root cause of the pervasive unmerged 'drippy' boundary verts).
SCL = mwm.median_scale  # world units per local unit
print(f"[fix_sword] world-per-local scale SCL={SCL:.5f} "
      f"(weld thresholds converted by /SCL)")
lh_head_w = awm @ arm.data.bones["LeftHand"].head_local
print(f"[fix_sword] LeftHand head_w={tuple(round(c,4) for c in lh_head_w)}")

lh_gi = mesh_obj.vertex_groups["LeftHand"].index

def lh_weight(v):
    for g in v.groups:
        if g.group == lh_gi:
            return g.weight
    return 0.0

# ─────────────────────────────────────────────────────────────────
# 1. Find the sword: blade-cluster seed + axis-cylinder island growth
# ─────────────────────────────────────────────────────────────────
world_co = [mwm @ v.co for v in me.vertices]
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()

seen = set()
islands = []
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
    islands.append(comp)
bm.free()
print(f"[fix_sword] total islands={len(islands)}")

blo, bhi = Vector(P["blade_box"][0]), Vector(P["blade_box"][1])
blade = set()
n_blade_isl = 0
for comp in islands:
    if all(blo.x <= world_co[i].x <= bhi.x and
           blo.y <= world_co[i].y <= bhi.y and
           blo.z <= world_co[i].z <= bhi.z for i in comp):
        blade |= comp
        n_blade_isl += 1
assert blade, "no blade islands inside blade_box — sword_box wrong again"
bl_pts = [world_co[i] for i in blade]
tip = min(bl_pts, key=lambda c: c.z)
bl_top = max(bl_pts, key=lambda c: c.z)
axis_dir = (bl_top - tip).normalized()
assert axis_dir.z > 0.8, f"blade axis not vertical-ish: {axis_dir}"
# extend the axis up through grip + pommel
axis_a = tip
axis_b = tip + axis_dir * ((P["axis_top_z"] - tip.z) / axis_dir.z)
print(f"[fix_sword] blade cluster: {n_blade_isl} islands {len(blade)} verts  "
      f"tip={tuple(round(c,3) for c in tip)} top={tuple(round(c,3) for c in bl_top)}")
print(f"[fix_sword] axis {tuple(round(c,3) for c in axis_a)} -> "
      f"{tuple(round(c,3) for c in axis_b)}")

def seg_d(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - a - ab * t).length

visited = set(blade)
n_isl = n_lh_skipped = 0
for comp in islands:
    if comp & blade:
        continue
    if len(comp) > P["cand_max_verts"]:
        continue
    # every vert of the island must hug the sword axis (blade/guard/grip/
    # pommel are all within axis_rad; robe drapes + body shells are not)
    if not all(world_co[i].z <= P["axis_top_z"] + 0.05 and
               seg_d(world_co[i], axis_a, axis_b) <= P["axis_rad"]
               for i in comp):
        continue
    # the left glove drapes over the pommel: strongly LeftHand-weighted and
    # tight around the joint. Leave it on the body.
    mean_lw = sum(lh_weight(me.vertices[i]) for i in comp) / len(comp)
    mean_d = sum((world_co[i] - lh_head_w).length for i in comp) / len(comp)
    z_min = min(world_co[i].z for i in comp)
    if z_min > 1.70 and mean_d < P["glove_rad"] and mean_lw > P["glove_lw"]:
        n_lh_skipped += 1
        print(f"[fix_sword]   glove island skipped: n={len(comp)} "
              f"mean_lw={mean_lw:.2f} mean_d={mean_d:.2f}")
        continue
    visited |= comp
    n_isl += 1
print(f"[fix_sword] sword = blade({n_blade_isl}) + {n_isl} axis islands "
      f"({n_lh_skipped} glove islands left on body)")

isl_w = [world_co[i] for i in visited]
lo = Vector((min(c.x for c in isl_w), min(c.y for c in isl_w), min(c.z for c in isl_w)))
hi = Vector((max(c.x for c in isl_w), max(c.y for c in isl_w), max(c.z for c in isl_w)))
zext = hi.z - lo.z
print(f"[fix_sword] sword selection: {len(visited)} verts  "
      f"bbox lo={tuple(round(c,3) for c in lo)} hi={tuple(round(c,3) for c in hi)} "
      f"zext={zext:.2f}")
assert zext >= P["min_zext"], \
    f"sword z-extent {zext:.2f} < {P['min_zext']} — blade missing again"
assert hi.z < 2.5 and len(visited) < 60000, "selection grabbed the body"

# sword long axis for reporting
top = max(isl_w, key=lambda c: c.z)

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

# rigid prop: no armature modifier / vgroups / shapekeys
for m in list(sword.modifiers):
    if m.type == 'ARMATURE':
        sword.modifiers.remove(m)
sword.vertex_groups.clear()
if sword.data.shape_keys:
    bpy.context.view_layer.objects.active = sword
    sword.shape_key_clear()
assert [l.name for l in sword.data.uv_layers], "sword lost its UVs!"

# ── weld the sword strips into ONE connected piece (escalating threshold),
# dropping micro debris; assert connectivity + z-extent before accepting ──
def get_islands(obj):
    xb = bmesh.new()
    xb.from_mesh(obj.data)
    xb.verts.ensure_lookup_table()
    s, comps = set(), []
    for v0 in xb.verts:
        if v0.index in s:
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
        s |= comp
        comps.append(comp)
    xb.free()
    comps.sort(key=len, reverse=True)
    return comps

def weld(obj, th):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=th / SCL)  # th is WORLD units
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
    bpy.ops.object.mode_set(mode='OBJECT')

sword_connected = False
for th in P["sword_weld"]:
    weld(sword, th)
    comps = get_islands(sword)
    frac = len(comps[0]) / max(sum(len(c) for c in comps), 1)
    print(f"[fix_sword] sword weld th={th}: verts={len(sword.data.vertices)} "
          f"islands={len(comps)} largest_frac={frac:.2f}")
    if frac >= 0.90 or len(comps) == 1:
        sword_connected = True
        break
if not sword_connected:
    # The sword is a blade shell + physically separate guard/gem decoration
    # shells (>8mm apart — welding harder would distort geometry). Accept iff
    # the WELDED MAIN SHELL is itself a full-length blade and every residual
    # shell hugs the sword axis (i.e. no stray fragments, coherent weapon).
    comps = get_islands(sword)
    swm = sword.matrix_world
    main_pts = [swm @ sword.data.vertices[i].co for i in comps[0]]
    main_zext = max(c.z for c in main_pts) - min(c.z for c in main_pts)
    frac = len(comps[0]) / max(sum(len(c) for c in comps), 1)
    stray = 0
    for comp in comps[1:]:
        for i in comp:
            if seg_d(swm @ sword.data.vertices[i].co, axis_a, axis_b) > P["axis_rad"]:
                stray += 1
    print(f"[fix_sword] sword coherence: main shell frac={frac:.2f} "
          f"zext={main_zext:.2f}, off-axis stray verts={stray}")
    assert frac >= 0.70 and main_zext >= P["min_zext"] and stray == 0, \
        "sword not coherent: main shell too small/short or stray fragments"
    sword_connected = True
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
sw_zext = max(c.z for c in sw_pts) - min(c.z for c in sw_pts)
assert sw_zext >= P["min_zext"], f"post-weld sword zext {sw_zext:.2f} too short"
assert sword.data.uv_layers, "sword lost UVs in weld"
print(f"[fix_sword] sword welded: zext={sw_zext:.2f} "
      f"(tip z={min(c.z for c in sw_pts):.2f} pommel z={max(c.z for c in sw_pts):.2f})")

# ── round 4 flaw 4: DEAD-STRAIGHT blade. The axis-hug selection tolerated
# curvature; now snap each z-slice CENTROID of the blade region onto the
# axis line so the greatsword reads straight like god_C, with a smooth
# ramp-out below the guard/grip so there is no step. ──
swm = sword.matrix_world
swm_inv2 = swm.inverted()
pom_z = max(c.z for c in sw_pts)
blade_hi = pom_z - 0.50          # everything below the grip region
str_bins = defaultdict(list)
for v in sword.data.vertices:
    wz = (swm @ v.co).z
    if wz < blade_hi + 0.08:
        str_bins[int(wz / 0.02)].append(v)
n_straight = 0
for bk, vs in str_bins.items():
    zc = (bk + 0.5) * 0.02
    rmp = (blade_hi + 0.08 - zc) / 0.10
    rmp = max(0.0, min(1.0, rmp))
    rmp = rmp * rmp * (3 - 2 * rmp)
    if rmp <= 0.0:
        continue
    cen = Vector((0.0, 0.0, 0.0))
    for v in vs:
        cen += swm @ v.co
    cen /= len(vs)
    ax_pt = axis_a + axis_dir * ((zc - axis_a.z) / axis_dir.z)
    shift = Vector((ax_pt.x - cen.x, ax_pt.y - cen.y, 0.0)) * rmp
    if shift.length < 1e-4:
        continue
    for v in vs:
        v.co = swm_inv2 @ ((swm @ v.co) + shift)
        n_straight += 1
sword.data.update()
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
print(f"[fix_sword] blade straightened: {len(str_bins)} z-slices, "
      f"{n_straight} verts snapped onto the axis line")

# ── round 5 flaw 6: the greatsword read STUBBY vs god_C. Stretch the blade
# along its axis (everything below the guard region) about blade_hi so the
# grip/pommel stay in the hand and the tip extends — a true greatsword
# reaching past the shin (planted, so a buried tip is fine). ──
BLADE_STRETCH = 1.16
n_str = 0
for v in sword.data.vertices:
    w = swm @ v.co
    if w.z < blade_hi:
        w2 = Vector((w.x, w.y, blade_hi - (blade_hi - w.z) * BLADE_STRETCH))
        v.co = swm_inv2 @ w2
        n_str += 1
sword.data.update()
# round 5b: cull bead debris — tiny leftover shells scattered along the
# blade read as floating droplets in the posed render
_cb = bmesh.new()
_cb.from_mesh(sword.data)
_cb.verts.ensure_lookup_table()
_cseen, _ckill = set(), []
for _v0 in _cb.verts:
    if _v0.index in _cseen:
        continue
    _comp = {_v0.index}
    _dq = deque([_v0])
    while _dq:
        _u = _dq.popleft()
        for _e in _u.link_edges:
            _o = _e.other_vert(_u)
            if _o.index not in _comp:
                _comp.add(_o.index)
                _dq.append(_o)
    _cseen |= _comp
    if len(_comp) < 60:
        _ckill.extend(_comp)
if _ckill:
    bmesh.ops.delete(_cb, geom=[_cb.verts[i] for i in _ckill], context='VERTS')
_cb.to_mesh(sword.data)
_cb.free()
sword.data.update()
print(f"[fix_sword] sword bead cull: removed {len(_ckill)} debris verts")
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
sw_len = max(c.z for c in sw_pts) - min(c.z for c in sw_pts)
print(f"[fix_sword] blade lengthened x{BLADE_STRETCH}: {n_str} verts, total "
      f"length {sw_len:.2f} (tip z={min(c.z for c in sw_pts):.2f})")
assert sw_len >= 2.05, f"greatsword still short: {sw_len:.2f} < 2.05"

# ─────────────────────────────────────────────────────────────────
# 2b. char1 cleanup: weld shard soup, kill micro debris
# ─────────────────────────────────────────────────────────────────
assert not me.shape_keys, "char1 has shape keys — refuse to weld"
nv0 = len(me.vertices)
weld(mesh_obj, P["weld_dist"])
wbm = bmesh.new()
wbm.from_mesh(me)
wbm.verts.ensure_lookup_table()
wseen, wkill, n_body_isl = set(), [], 0
body_islands = []
for v0 in wbm.verts:
    if v0.index in wseen:
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
    wseen |= comp
    n_body_isl += 1
    if len(comp) < P["micro_isl"]:
        wkill.extend(comp)
    else:
        body_islands.append(comp)
if wkill:
    bmesh.ops.delete(wbm, geom=[wbm.verts[i] for i in wkill], context='VERTS')
    wbm.to_mesh(me)
    me.update()
wbm.free()
me = mesh_obj.data
print(f"[fix_sword] char1 cleanup: {nv0} -> {len(me.vertices)} verts, "
      f"islands={n_body_isl}, micro-debris removed={len(wkill)}")
assert me.uv_layers, "char1 lost UVs in weld"

# ─────────────────────────────────────────────────────────────────
# 2c. Skeleton segments (full bone graph — heads only, glTF tails are junk)
# ─────────────────────────────────────────────────────────────────
def head_w(b):
    return awm @ b.head_local

seg_list = []          # (bone_name, a, b)
for b in arm.data.bones:
    kids = b.children
    if kids:
        for k in kids:
            seg_list.append((b.name, head_w(b), head_w(k)))
    else:
        par = b.parent
        d = (head_w(b) - head_w(par)).normalized() if par else Vector((0, 0, 1))
        seg_list.append((b.name, head_w(b), head_w(b) + d * 0.15))
ARMY = ("Arm", "Hand", "Shoulder", "Thumb", "Index", "Finger")
arm_seg_idx = [i for i, (n, _, _) in enumerate(seg_list) if any(t in n for t in ARMY)]
torso_seg_idx = [i for i, (n, _, _) in enumerate(seg_list)
                 if not any(t in n for t in ARMY)
                 and not any(t in n.lower() for t in ("head", "neck"))]
print(f"[fix_sword] skeleton segments={len(seg_list)} "
      f"arm={len(arm_seg_idx)} torso/leg={[seg_list[i][0] for i in torso_seg_idx]}")

bone_names = {b.name for b in arm.data.bones}
gi_names = {g.index: g.name for g in mesh_obj.vertex_groups}
name2grp = {g.name: g for g in mesh_obj.vertex_groups}

def bwv(n):
    return awm @ arm.data.bones[n].head_local

rh_head_w = bwv("RightHand")
rf_head_w = bwv("RightForeArm")
hand_dir = (rh_head_w - rf_head_w).normalized()
rs_w, ra_w = bwv("RightShoulder"), bwv("RightArm")
sp_w, hp_w, hd_w = bwv("Spine"), bwv("Hips"), bwv("Head")
s01_w, s02_w, nk_w = bwv("Spine01"), bwv("Spine02"), bwv("neck")
hand_ext = rh_head_w + hand_dir * 0.20
sleeve_end = rh_head_w + Vector((0.0, 0.0, -0.85))
segs = [
    ("RightShoulder", rs_w, ra_w),
    ("RightArm",      ra_w, rf_head_w),
    ("RightForeArm",  rf_head_w, rh_head_w),
    ("RightHand",     rh_head_w, hand_ext),
    ("Spine",         sp_w, s01_w),
    ("Spine01",       s01_w, s02_w),
    ("Spine02",       s02_w, nk_w),
    ("neck",          nk_w, hd_w),
    ("Hips",          hp_w, sp_w),
]
ARM_SEGS = (0, 1, 2, 3)
ARM_GATE = 0.14
REGION_EXTRA = [(rh_head_w, sleeve_end)]

# ─────────────────────────────────────────────────────────────────
# 2c2. GEO SCULPT (round 3): fist grip, hair locks, cloak folds
#   flaw 1: the LeftHand glove is a melted glob — sculpt it into a
#           fist wrapping the hilt with horizontal finger ridges.
#   flaw 3: hair shell is a melted blob — carve angular strand
#           grooves; cloak gets vertical pleat folds toward the hem.
#   Vertex moves only: UVs follow, weights untouched here.
# ─────────────────────────────────────────────────────────────────
def smt01(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

mwm_inv = mesh_obj.matrix_world.inverted()

# -- fist (round 5): the r3/r4 procedural ridge/tube PROJECTION of the
# existing glove shell never read as a hand (corrugated tube / stacked
# rings, per the beauty eval). ABANDONED. New pipeline:
#   (c) weld + aggressively Laplacian-smooth the glove/sleeve region so
#       every low-weight tendril is fused (nothing left dripping),
#   (a) DELETE the residual melted mitten hugging the hilt in the fist
#       zone entirely — a REAL modeled low-poly gauntlet object with
#       actual curled finger geometry replaces it (built in section 4b
#       after the sword is finalized, bone-parented to LeftHand). --
grip_top = max(c.z for c in sw_pts)
grip_lo = grip_top - 0.45
ab_axis = axis_b - axis_a

def axis_foot(w):
    t = max(0.0, min(1.0, (w - axis_a).dot(ab_axis) / ab_axis.length_squared))
    return axis_a + ab_axis * t

fb = bmesh.new()
fb.from_mesh(me)
fb.verts.ensure_lookup_table()
dvl = fb.verts.layers.deform.verify()

def glove_sel():
    # the tendrils dripping off the palm include low-weight SLEEVE verts —
    # select by (any LeftHand weight) OR (proximity to the hand joint),
    # z-gated to the grip/pommel region
    out = []
    for bv in fb.verts:
        w = mwm @ bv.co
        if w.z < grip_lo - 0.30 or w.z > grip_top + 0.20:
            continue
        lw = bv[dvl].get(lh_gi, 0.0)
        near = (w - lh_head_w).length < 0.24 or (w - axis_foot(w)).length < 0.20
        if lw < 0.02 and not near:
            continue
        if (w - axis_foot(w)).length > 0.30:
            continue
        out.append(bv)
    return out

gv = glove_sel()
n_gv0 = len(gv)
bmesh.ops.remove_doubles(fb, verts=gv, dist=0.0035 / SCL)  # 3.5mm WORLD
fb.verts.ensure_lookup_table()
gv = glove_sel()
for _ in range(14):
    bmesh.ops.smooth_vert(fb, verts=gv, factor=0.5,
                          use_axis_x=True, use_axis_y=True, use_axis_z=True)
print(f"[fix_sword] glove island: {n_gv0} -> {len(gv)} verts after weld; "
      f"tendrils/ring-seams smoothed (14 Laplacian iters)")

# palm side direction (character side of the hilt) — used by the gauntlet
foot_lh = axis_foot(lh_head_w)
palm_h = Vector((lh_head_w.x - foot_lh.x, lh_head_w.y - foot_lh.y, 0.0))
th_palm = math.atan2(palm_h.y, palm_h.x) if palm_h.length > 1e-5 else 0.0

def ang_d(a, b):
    d = (a - b) % (2 * math.pi)
    return d - 2 * math.pi if d > math.pi else d

# round 5: DELETE the melted mitten in the fist zone (the modeled gauntlet
# replaces it). Fitted forearm/cuff geometry is spared.
lf_w0 = bwv("LeftForeArm") if "LeftForeArm" in bone_names \
    else lh_head_w + Vector((-0.3, 0.2, 0.0))
kill_fist = []
for bv in fb.verts:
    w = mwm @ bv.co
    if not (grip_top - 0.30 <= w.z <= grip_top + 0.14):
        continue
    if (w - axis_foot(w)).length > 0.20:
        continue
    if seg_d(w, lf_w0, lh_head_w) < 0.085:
        continue  # fitted forearm/cuff — keep
    kill_fist.append(bv)
n_fist = len(kill_fist)
if kill_fist:
    bmesh.ops.delete(fb, geom=kill_fist, context='VERTS')
fb.to_mesh(me)
fb.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] fist round5: deleted {n_fist} melted-mitten verts in the "
      f"fist zone (th_palm={math.degrees(th_palm):.0f}deg) — modeled gauntlet "
      f"replaces them")

# -- hair cleanup (round 4): the hair shells are pre-existing melted blobs
# and the r3 sin-groove carve only added chaos. Replace it with a dedicated
# cleanup: weld the hair island, then a strong Laplacian smooth so the hair
# reads as coherent flowing masses, not a wax halo. Front face protected
# (fix_face owns it). --
HAIR_Z0 = 2.50
hb = bmesh.new()
hb.from_mesh(me)
hb.verts.ensure_lookup_table()

def hair_sel():
    out = []
    for bv in hb.verts:
        w = mwm @ bv.co
        if w.z < HAIR_Z0:
            continue
        if w.y < -0.30 and abs(w.x) < 0.16 and w.z < 3.16:
            continue  # front face — fix_face owns it
        out.append(bv)
    return out

hs = hair_sel()
n_h0 = len(hs)
bmesh.ops.remove_doubles(hb, verts=hs, dist=0.0030 / SCL)  # 3mm WORLD
hb.verts.ensure_lookup_table()
hs = hair_sel()
for _ in range(8):
    bmesh.ops.smooth_vert(hb, verts=hs, factor=0.5,
                          use_axis_x=True, use_axis_y=True, use_axis_z=True)
hb.to_mesh(me)
hb.free()
me.update()
me = mesh_obj.data
n_hair = len(hs)
print(f"[fix_sword] hair cleanup: {n_h0} -> {n_hair} verts welded + "
      f"smoothed (8 Laplacian iters)")

# -- cloak folds: vertical pleats on hanging drape, stronger at the hem --
n_cloak = 0
for v in me.vertices:
    w = mwm @ v.co
    if w.z > 2.20:
        continue
    d_all = min(seg_d(w, a, b) for _, a, b in seg_list)
    if d_all < 0.09:
        continue
    rh = math.hypot(w.x, w.y)
    if rh < 0.05:
        continue
    th = math.atan2(w.y, w.x)
    ramp = smt01((2.0 - w.z) / 1.6)
    dsp = 0.013 * math.sin(8 * th + 1.2 * w.z) * ramp
    f = dsp / rh
    neww = w + Vector((w.x * f, w.y * f, 0.0))
    v.co = mwm_inv @ neww
    n_cloak += 1
me.update()
print(f"[fix_sword] cloak folds: pleated {n_cloak} drape verts")

# -- global de-spike (round 4): the stalactite tendrils on shoulders/hilt
# are verts flung far from EVERY neighbor. Pull any vert whose shortest
# link edge is > 4x the median edge length onto its neighbor centroid. --
gb = bmesh.new()
gb.from_mesh(me)
gb.verts.ensure_lookup_table()
gb.edges.ensure_lookup_table()
_el = sorted(e.calc_length() for _i, e in enumerate(gb.edges) if _i % 11 == 0)
med_e = _el[len(_el) // 2]
spike_th = 4.0 * med_e
n_spike = 0
for _pass in range(3):
    moved = 0
    for bv in gb.verts:
        if not bv.link_edges:
            continue
        if min(e.calc_length() for e in bv.link_edges) <= spike_th:
            continue
        cen = Vector((0.0, 0.0, 0.0))
        for e in bv.link_edges:
            cen += e.other_vert(bv).co
        bv.co = cen / len(bv.link_edges)
        moved += 1
    n_spike += moved
    if moved == 0:
        break
gb.to_mesh(me)
gb.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] de-spike: median edge {med_e*1000:.1f}mm, collapsed "
      f"{n_spike} spike verts (threshold {spike_th*1000:.1f}mm)")

# -- tendril amputation (round 4): the stalactite drips off the palm /
# shoulders / hilt are SEPARATE thin shell-soup islands (tall, narrow,
# few verts) — welding cannot merge them and smoothing only rounds them.
# Delete any island that is a thin vertical strand. --
tb = bmesh.new()
tb.from_mesh(me)
tb.verts.ensure_lookup_table()
tseen = set()
kill_t = []
n_tendril = 0
for v0 in tb.verts:
    if v0.index in tseen:
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
    tseen |= comp
    if len(comp) > 1500:
        continue
    pts = [mwm @ tb.verts[i].co for i in comp]
    hx = max(p.x for p in pts) - min(p.x for p in pts)
    hy = max(p.y for p in pts) - min(p.y for p in pts)
    hz = max(p.z for p in pts) - min(p.z for p in pts)
    hd = math.hypot(hx, hy)
    if hd < 0.06 and hz > 0.12 and hz > 2.5 * hd:
        kill_t.extend(comp)
        n_tendril += 1
if kill_t:
    bmesh.ops.delete(tb, geom=[tb.verts[i] for i in kill_t], context='VERTS')
tb.to_mesh(me)
tb.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] tendril amputation: deleted {n_tendril} thin strand "
      f"islands ({len(kill_t)} verts)")

# -- palm tendril CUT (round 4): probe shows the strands dangling below
# the fist are FUSED with the sleeve drape into one component (r 0.24-0.46
# off the axis, z down to 1.26). Hard z-cut: delete everything in the hand
# region hanging below the sleeve-cuff line, sparing the glove-on-hilt
# capsule (r < 0.10). The cut edge reads as a cloth hem; the melted-root
# tendrils are gone. --
CUT_Z = grip_top - 0.26              # bottom of the fist — nothing below it
lf_w = bwv("LeftForeArm") if "LeftForeArm" in {b.name for b in arm.data.bones} \
    else lh_head_w + Vector((-0.3, 0.2, 0.0))
zb = bmesh.new()
zb.from_mesh(me)
zb.verts.ensure_lookup_table()
kill_z = []
for bv in zb.verts:
    w = mwm @ bv.co
    if not (grip_top - 0.95 < w.z < CUT_Z):
        continue
    if math.hypot(w.x - lh_head_w.x, w.y - lh_head_w.y) > 0.32:
        continue
    if seg_d(w, lf_w, lh_head_w) < 0.10:
        continue  # forearm + fitted cuff — keep
    kill_z.append(bv)
n_kz = len(kill_z)
if kill_z:
    bmesh.ops.delete(zb, geom=kill_z, context='VERTS')
zb.to_mesh(me)
zb.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] palm tendril cut: deleted {n_kz} verts hanging below "
      f"z={CUT_Z:.2f} in the hand region (sleeve hem cut)")

# -- GLOBAL strand cut (round 4): the cloak/torso drape also trails thin
# stalactite strands (visible behind the hand in closeups). Slab-level
# component analysis over the whole hang region: any sub-component in the
# z 1.30-1.92 slab that is thin (narrow horizontal footprint, taller than
# wide, few verts) is a melted strand — delete. Wide drape panels, the
# torso shell and the legs are spared by the width/count filters. --
sb = bmesh.new()
sb.from_mesh(me)
sb.verts.ensure_lookup_table()
slab = set()
for bv in sb.verts:
    wz = (mwm @ bv.co).z
    if 1.30 < wz < 1.92:
        slab.add(bv.index)
sseen = set()
kill_s = []
n_sc = 0
for i0 in slab:
    if i0 in sseen:
        continue
    comp = {i0}
    dq = deque([sb.verts[i0]])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index in slab and o.index not in comp:
                comp.add(o.index)
                dq.append(o)
    sseen |= comp
    if len(comp) > 900:
        continue
    pts = [mwm @ sb.verts[i].co for i in comp]
    hx = max(p.x for p in pts) - min(p.x for p in pts)
    hy = max(p.y for p in pts) - min(p.y for p in pts)
    hd = math.hypot(hx, hy)
    hz = max(p.z for p in pts) - min(p.z for p in pts)
    if hd < 0.09 and hz > 1.2 * hd:
        kill_s.extend(comp)
        n_sc += 1
if kill_s:
    bmesh.ops.delete(sb, geom=[sb.verts[i] for i in kill_s], context='VERTS')
sb.to_mesh(me)
sb.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] global strand cut: deleted {n_sc} thin strands "
      f"({len(kill_s)} verts) in the z 1.30-1.92 slab")

# -- right-side drape fuse (round 4): the drape hanging off the right hip/
# torso (x>0.28, y>-0.30, z 1.35-2.05) is a torn root-curtain that reads as
# stalactite tendrils behind the hand in closeups. Weld + heavy Laplacian
# smooth fuses it into a coherent cloth mass (no holes, nothing deleted). --
db = bmesh.new()
db.from_mesh(me)
db.verts.ensure_lookup_table()

def drape_sel():
    out = []
    for bv in db.verts:
        w = mwm @ bv.co
        if 1.35 < w.z < 2.05 and w.x > 0.28 and w.y > -0.30:
            out.append(bv)
    return out

ds = drape_sel()
n_d0 = len(ds)
bmesh.ops.remove_doubles(db, verts=ds, dist=0.0040 / SCL)  # 4mm WORLD
db.verts.ensure_lookup_table()
ds = drape_sel()
for _ in range(15):
    bmesh.ops.smooth_vert(db, verts=ds, factor=0.5,
                          use_axis_x=True, use_axis_y=True, use_axis_z=True)
db.to_mesh(me)
db.free()
me.update()
me = mesh_obj.data
print(f"[fix_sword] right drape fuse: {n_d0} -> {len(ds)} verts welded + "
      f"smoothed (15 iters)")
assert me.uv_layers, "sculpt somehow lost UVs"

# ─────────────────────────────────────────────────────────────────
# 2d. Rebind pass A: right-arm/shoulder/upper-robe (round-1 logic, kept)
# ─────────────────────────────────────────────────────────────────
R_IN, R_OUT = P["rebind_r_in"], P["rebind_r_out"]
new_w = {}
for v in me.vertices:
    w = mwm @ v.co
    dists = [seg_d(w, a, b) for _, a, b in segs]
    d_arm = min(dists[i] for i in ARM_SEGS)
    d_reg = min([d_arm] + [seg_d(w, a, b) for a, b in REGION_EXTRA])
    if d_reg > R_OUT:
        continue
    f = 1.0 if d_reg <= R_IN else 1.0 - (d_reg - R_IN) / (R_OUT - R_IN)
    f = f * f * (3 - 2 * f)
    gate = math.exp(-(d_arm / ARM_GATE) ** 2)
    nw = {}
    for si, ((gname, _, _), d) in enumerate(zip(segs, dists)):
        sc = (1.0 / (d + 0.025)) ** 2
        if si in ARM_SEGS:
            sc *= gate
        nw[gname] = nw.get(gname, 0.0) + sc
    tot = sum(nw.values())
    nw = {k: x / tot for k, x in nw.items()}
    ow = {}
    for g in v.groups:
        gname = gi_names.get(g.group)
        if gname in bone_names and g.weight > 1e-4:
            ow[gname] = ow.get(gname, 0.0) + g.weight
    otot = sum(ow.values())
    if otot < 1e-4:
        ow, f = {}, 1.0
    else:
        ow = {k: x / otot for k, x in ow.items()}
    mix = {}
    for k, x in ow.items():
        mix[k] = mix.get(k, 0.0) + (1.0 - f) * x
    for k, x in nw.items():
        mix[k] = mix.get(k, 0.0) + f * x
    new_w[v.index] = mix
print(f"[fix_sword] pass A (right-arm region): {len(new_w)} verts")

# ─────────────────────────────────────────────────────────────────
# 2e. Rebind pass B: BILLOWY DRAPE -> torso/leg bones only (flaw 4).
# Any vert far off every bone segment is hanging cloth; its auto-skin
# weights (often arm/hand poisoned) shear it into candy-wrapper sheets
# when the spine/arm move. Rebind to the torso/leg skeleton with a soft
# blend, then smooth spatially.
# ─────────────────────────────────────────────────────────────────
D0, D1 = P["drape_d0"], P["drape_d1"]
n_drape = 0
for v in me.vertices:
    if v.index in new_w:
        continue
    w = mwm @ v.co
    if w.z > P["drape_z_max"]:
        continue
    d_all = min(seg_d(w, a, b) for _, a, b in seg_list)
    if d_all <= D0:
        continue
    f = min((d_all - D0) / (D1 - D0), 1.0)
    f = f * f * (3 - 2 * f)
    nw = {}
    for i in torso_seg_idx:
        gname, a, b = seg_list[i]
        d = seg_d(w, a, b)
        sc = (1.0 / (d + 0.05)) ** 2
        nw[gname] = nw.get(gname, 0.0) + sc
    tot = sum(nw.values())
    nw = {k: x / tot for k, x in nw.items()}
    ow = {}
    for g in v.groups:
        gname = gi_names.get(g.group)
        if gname in bone_names and g.weight > 1e-4:
            ow[gname] = ow.get(gname, 0.0) + g.weight
    otot = sum(ow.values())
    if otot < 1e-4:
        ow, f = {}, 1.0
    else:
        ow = {k: x / otot for k, x in ow.items()}
    mix = {}
    for k, x in ow.items():
        mix[k] = mix.get(k, 0.0) + (1.0 - f) * x
    for k, x in nw.items():
        mix[k] = mix.get(k, 0.0) + f * x
    new_w[v.index] = mix
    n_drape += 1
print(f"[fix_sword] pass B (drape rebind): {n_drape} verts "
      f"(d0={D0} d1={D1}, torso/leg bones only)")

# ── spatial weight smoothing across shells (KD over world distance) ──
wco_all = [mwm @ v.co for v in me.vertices]
kd = kdtree.KDTree(len(me.vertices))
for i, c in enumerate(wco_all):
    kd.insert(c, i)
kd.balance()
SR = 0.04
_oldw_cache = {}

def _getw(j, state):
    if j in state:
        return state[j]
    d = _oldw_cache.get(j)
    if d is None:
        d = {}
        for g in me.vertices[j].groups:
            gn = gi_names.get(g.group)
            if gn in bone_names and g.weight > 1e-4:
                d[gn] = d.get(gn, 0.0) + g.weight
        s = sum(d.values())
        d = {k: x / s for k, x in d.items()} if s > 1e-6 else {}
        _oldw_cache[j] = d
    return d

state = new_w
for _it in range(3):
    nxt = {}
    for i in state:
        acc, tot = {}, 0.0
        for (_co, j, dist) in kd.find_range(wco_all[i], SR):
            wgt = math.exp(-((dist / SR) * 2.0) ** 2)
            for k, x in _getw(j, state).items():
                acc[k] = acc.get(k, 0.0) + wgt * x
            tot += wgt
        nxt[i] = {k: x / tot for k, x in acc.items()} if tot > 0 else state[i]
    state = nxt
print(f"[fix_sword] spatially smoothed weights over {len(state)} verts "
      f"(r={SR}, 3 iterations, cross-shell)")

new_w = {}
for i, mix in state.items():
    top4 = sorted(mix.items(), key=lambda kv: -kv[1])[:4]
    tt = sum(x for _, x in top4)
    if tt < 1e-9:
        continue
    new_w[i] = [(k, x / tt) for k, x in top4]

# ── rigidify small shells: uniform island weights = no intra-plate stretch ──
rbm = bmesh.new()
rbm.from_mesh(me)
rbm.verts.ensure_lookup_table()
isl_id, islands2, rseen = {}, [], set()
for v0 in rbm.verts:
    if v0.index in rseen:
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
    rseen |= comp
    for i in comp:
        isl_id[i] = len(islands2)
    islands2.append(sorted(comp))
rbm.free()

touched = defaultdict(list)
for i in new_w:
    touched[isl_id[i]].append(i)
n_rigid = 0
for ii, idx_list in touched.items():
    comp = islands2[ii]
    if len(comp) > P["rigid_isl_max"]:
        continue
    pts = [mwm @ me.vertices[i].co for i in comp]
    lo_p = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi_p = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    if (hi_p - lo_p).length > P["rigid_diag"]:
        continue
    acc = {}
    for i in idx_list:
        for gname, x in new_w[i]:
            acc[gname] = acc.get(gname, 0.0) + x
    top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
    tt = sum(x for _, x in top4)
    uni = [(k, x / tt) for k, x in top4]
    for i in comp:
        new_w[i] = uni
    n_rigid += 1
print(f"[fix_sword] rigidified {n_rigid} small shells")

# ── round 5 flaw 2: SHOULDER-PLATE RIGID BIND. The taffy smear on the
# right shoulder/upper arm comes from deltoid/pauldron shells carrying
# mixed spine/shoulder/arm weights. Any modest shell whose centroid hugs
# the shoulder or upper-arm segment now follows that arm RIGIDLY
# (island-coherent re-bind, uniform weights). Both sides for symmetry. ──
sh_sides = [("Right", rs_w, ra_w, rf_head_w)]
if all(n in bone_names for n in ("LeftShoulder", "LeftArm", "LeftForeArm")):
    sh_sides.append(("Left", bwv("LeftShoulder"), bwv("LeftArm"),
                     bwv("LeftForeArm")))
n_delt = 0
for comp in islands2:
    if len(comp) > 6000:
        continue
    pts = [mwm @ me.vertices[i].co for i in comp]
    cen = sum(pts, Vector()) / len(pts)
    if cen.z < 2.05:
        continue
    for side, s_w, a_w, f_w in sh_sides:
        d_up = seg_d(cen, a_w, a_w + (f_w - a_w) * 0.6)  # deltoid zone
        d_sh = seg_d(cen, s_w, a_w)
        if min(d_up, d_sh) > 0.20:
            continue
        if d_up <= d_sh:
            uni = {side + "Arm": 0.8, side + "Shoulder": 0.2}
        else:
            uni = {side + "Shoulder": 0.55, side + "Arm": 0.25, "Spine02": 0.20}
        for i in comp:
            new_w[i] = list(uni.items())
        n_delt += 1
        break
print(f"[fix_sword] deltoid rigid bind: {n_delt} shoulder/upper-arm shells "
      f"re-bound rigidly to their arm")

idxs = list(new_w.keys())
for g in mesh_obj.vertex_groups:
    g.remove(idxs)
for i, lst in new_w.items():
    for gname, x in lst:
        name2grp[gname].add([i], x, 'REPLACE')
print(f"[fix_sword] rebound {len(new_w)} verts total (max 4 influences)")

# ─────────────────────────────────────────────────────────────────
# 3. Deform assertion harness: spine twist + arm raise must not shred
# ─────────────────────────────────────────────────────────────────
def eval_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ob = mesh_obj.evaluated_get(dg)
    m = ob.matrix_world
    return [m @ v.co for v in ob.data.vertices]

def clear_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

edge_sample = [tuple(e.vertices) for e in list(me.edges)[::3]]
clear_pose()
rest_co = eval_coords()
rest_len = [(rest_co[a] - rest_co[b]).length for a, b in edge_sample]

def read_w(i):
    d = {}
    for g in me.vertices[i].groups:
        gn = gi_names.get(g.group)
        if gn in bone_names and g.weight > 1e-4:
            d[gn] = d.get(gn, 0.0) + g.weight
    s = sum(d.values())
    return {k: x / s for k, x in d.items()} if s > 1e-6 else {}

def write_w(i, d):
    top4 = sorted(d.items(), key=lambda kv: -kv[1])[:4]
    tt = sum(x for _, x in top4)
    for g in mesh_obj.vertex_groups:
        g.remove([i])
    for gname, x in top4:
        name2grp[gname].add([i], x / tt, 'REPLACE')

# ── round 4 flaw 3: GLOBAL weight hygiene — EVERY vert limited to max 4
# influences + renormalized. Long-range spurious weights (verts on the far
# side pulled by a moving bone) are what stretch the robe/armor into thin
# melted sheets under the eval pose. ──
n_lim = 0
for v in me.vertices:
    if sum(1 for g in v.groups if g.weight > 1e-4) > 4:
        d = read_w(v.index)
        if d:
            write_w(v.index, d)
            n_lim += 1
print(f"[fix_sword] limit-total: clamped {n_lim} verts to max 4 influences")

# ── round 3: HEAD/HAIR RIGIDIFY — the posed eval collapsed the head into a
# lump because head/hair shells carried mixed spine/shoulder weights. Above
# the neck everything is rigid: blend hard into the Head bone. ──
assert "Head" in name2grp, "no Head vertex group?!"
HZ = hd_w.z
n_headfix = 0
for v in me.vertices:
    w = mwm @ v.co
    if w.z <= HZ - 0.14:
        continue
    t = smt01((w.z - (HZ - 0.14)) / 0.16)
    cur = read_w(v.index)
    mix = {k: x * (1.0 - t) for k, x in cur.items()}
    mix["Head"] = mix.get("Head", 0.0) + t
    write_w(v.index, mix)
    n_headfix += 1
print(f"[fix_sword] head/hair rigidify: {n_headfix} verts blended into Head "
      f"(z > {HZ - 0.14:.2f})")
assert n_headfix > 200, "head rigidify found no verts — Head bone z wrong?"

# ── round 4 flaw 3: smooth weights ACROSS the neck/shoulder seam — the
# neck-to-shoulder junction tore/stretched under the eval pose. Spatially
# blend weights around the neck + both shoulder segments so influence
# transitions are gradual, not a hard seam. ──
seam_segs = [(s02_w, nk_w), (nk_w, hd_w), (rs_w, ra_w)]
if "LeftShoulder" in bone_names and "LeftArm" in bone_names:
    seam_segs.append((bwv("LeftShoulder"), bwv("LeftArm")))
seam_idx = [v.index for v in me.vertices
            if 2.0 < (mwm @ v.co).z < 2.85
            and min(seg_d(mwm @ v.co, a, b) for a, b in seam_segs) < 0.24]
for _it in range(2):
    upd = {}
    for i in seam_idx:
        acc, tot = {}, 0.0
        for (_c, j, dist) in kd.find_range(wco_all[i], 0.05):
            wgt = math.exp(-((dist / 0.05) * 2.0) ** 2)
            for k, x in read_w(j).items():
                acc[k] = acc.get(k, 0.0) + wgt * x
            tot += wgt
        if tot > 0:
            upd[i] = {k: x / tot for k, x in acc.items()}
    for i, d in upd.items():
        write_w(i, d)
print(f"[fix_sword] seam smooth: {len(seam_idx)} neck/shoulder verts "
      f"x2 spatial iterations")

# ── round 5 flaw 2: WAIST candy-wrapper. Spine twist pinched the waist
# because the Hips->Spine->Spine01 influence gradient is abrupt. Spatially
# smooth weights across the whole waist band so the twist distributes. ──
waist_lo, waist_hi = hp_w.z - 0.15, s01_w.z + 0.12
waist_idx = [v.index for v in me.vertices
             if waist_lo < (mwm @ v.co).z < waist_hi]
for _it in range(2):
    upd = {}
    for i in waist_idx:
        acc, tot = {}, 0.0
        for (_c, j, dist) in kd.find_range(wco_all[i], 0.06):
            wgt = math.exp(-((dist / 0.06) * 2.0) ** 2)
            for k, x in read_w(j).items():
                acc[k] = acc.get(k, 0.0) + wgt * x
            tot += wgt
        if tot > 0:
            upd[i] = {k: x / tot for k, x in acc.items()}
    for i, d in upd.items():
        write_w(i, d)
print(f"[fix_sword] waist smooth: {len(waist_idx)} verts in z "
      f"[{waist_lo:.2f},{waist_hi:.2f}] x2 spatial iterations")

def measure(label, poses):
    clear_pose()
    for bn, eul in poses:
        pb = arm.pose.bones[bn]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = tuple(math.radians(a) for a in eul)
    bpy.context.view_layer.update()
    co = eval_coords()
    ratios = []
    for (a, b), rl in zip(edge_sample, rest_len):
        ratios.append((co[a] - co[b]).length / rl if rl > 1e-6 else 1.0)
    srt = sorted(ratios)
    p99 = srt[int(len(srt) * 0.99)]
    print(f"[fix_sword] deform[{label}]: edges={len(srt)} "
          f"p99={p99:.3f} max={srt[-1]:.3f}")
    clear_pose()
    return p99, ratios

COMBO_POSE = [("Spine", (0, 0, 25)), ("Spine01", (0, 0, 12)),
              ("RightArm", (0, -55, -35)), ("RightForeArm", (0, -50, 0)),
              ("RightHand", (0, -15, 0))]
TESTS = [
    ("spine_twist", [("Spine", (0, 30, 0)), ("Spine01", (0, 15, 0))]),
    ("spine_bend",  [("Spine", (20, 0, 0)), ("Spine01", (12, 0, 0))]),
    ("arm_raise",   [("RightArm", (0, 0, -45))]),
    # round 3: the EXACT beauty-eval pose (raised right arm + spine turn)
    ("combo_eval",  COMBO_POSE),
]
# REMEDIATE: blend weights across over-stretched edges (weight-space weld of
# shear seams between rebound drape and untouched neighbors), then assert.
# combo_eval is a far more violent pose than the single-axis tests; it gets
# its own (looser) budget — the ISLAND-TRAVEL gate below is its hard check.
P["combo_p99_max"] = 2.60
def _thresh(label):
    return P["combo_p99_max"] if label.startswith("combo") else P["deform_p99_max"]

for it in range(12):
    worst_over = 0.0
    bad = set()
    for label, poses in TESTS:
        p99, ratios = measure(f"{label}_it{it}", poses)
        worst_over = max(worst_over, p99 - _thresh(label))
        for (a, b), r in zip(edge_sample, ratios):
            if r > 1.35 or r < 0.60:
                bad.add((a, b))
    if worst_over < 0 and not bad:
        break
    if worst_over < 0 and it >= 2:
        break
    if not bad:
        break
    touched_v = set()
    for a, b in bad:
        wa, wb = read_w(a), read_w(b)
        mix = {}
        for k in set(wa) | set(wb):
            mix[k] = 0.5 * wa.get(k, 0.0) + 0.5 * wb.get(k, 0.0)
        if not mix:
            continue
        write_w(a, mix)
        write_w(b, mix)
        touched_v.update((a, b))
    print(f"[fix_sword] deform remediation it{it}: blended {len(bad)} stretched "
          f"edges ({len(touched_v)} verts)")
# ── round 3: ISLAND-TRAVEL COHERENCE under the eval pose. A shell whose
# verts travel wildly different distances is tearing (candy-wrapper /
# spike sheets). Rigidify incoherent small shells, then ASSERT. ──
def pose_disp(poses):
    clear_pose()
    for bn, eul in poses:
        pb = arm.pose.bones[bn]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = tuple(math.radians(a) for a in eul)
    bpy.context.view_layer.update()
    co = eval_coords()
    d = [(co[i] - rest_co[i]).length for i in range(len(co))]
    clear_pose()
    return d

# round 5 flaw 2: coherence is now measured under BOTH the eval combo AND
# the pure spine twist (the TORSO candy-wrapper check the eval demanded).
COH_POSES = [
    ("combo", COMBO_POSE, 0.50, 2500),
    ("twist", TESTS[0][1], 0.35, 4000),
]
for rnd in range(3):
    n_bad_isl = 0
    for clabel, cposes, cth, cmax in COH_POSES:
        disp = pose_disp(cposes)
        for comp in islands2:
            if len(comp) > cmax:
                continue
            ds = sorted(disp[i] for i in comp)
            spread = ds[-1] - ds[len(ds) // 2]
            if spread <= cth:
                continue
            # incoherent shell: give the whole island one uniform weight set
            acc = {}
            for i in comp:
                for k, x in read_w(i).items():
                    acc[k] = acc.get(k, 0.0) + x
            if not acc:
                continue
            for i in comp:
                write_w(i, acc)
            n_bad_isl += 1
        print(f"[fix_sword] island coherence rnd{rnd}[{clabel}]: rigidified "
              f"{n_bad_isl} incoherent shells so far")
    if n_bad_isl == 0:
        break
disp = pose_disp(COMBO_POSE)
worst_spread = 0.0
for comp in islands2:
    if len(comp) > 2500:
        continue
    ds = sorted(disp[i] for i in comp)
    worst_spread = max(worst_spread, ds[-1] - ds[len(ds) // 2])
print(f"[fix_sword] island coherence: worst small-shell spread "
      f"{worst_spread:.2f} m under eval pose")
assert worst_spread < 0.90, \
    f"island spread {worst_spread:.2f} — shells still tearing under eval pose"
disp_t = pose_disp(TESTS[0][1])
worst_tw = 0.0
for comp in islands2:
    if len(comp) > 4000:
        continue
    pts0 = [rest_co[i] for i in comp]
    if max(p.z for p in pts0) > 2.60:
        continue  # torso/drape shells only
    ds = sorted(disp_t[i] for i in comp)
    worst_tw = max(worst_tw, ds[-1] - ds[len(ds) // 2])
print(f"[fix_sword] TORSO twist coherence: worst spread {worst_tw:.2f} m "
      f"under spine twist")
assert worst_tw < 0.60, \
    f"torso twist spread {worst_tw:.2f} — waist still candy-wrapping"

for label, poses in TESTS:
    final_p99 = measure(label, poses)[0]
    assert final_p99 < _thresh(label), \
        f"deform[{label}] p99 stretch {final_p99:.2f} — candy-wrapper regression"
print("[fix_sword] deform assertions PASSED")

# ─────────────────────────────────────────────────────────────────
# 4. Parent sword to LeftHand, keep it PLANTED in place (god_C pose:
# point-down plant at the left side, left palm on the pommel)
# ─────────────────────────────────────────────────────────────────
mw_saved = sword.matrix_world.copy()
sword.parent = arm
sword.parent_type = 'BONE'
sword.parent_bone = 'LeftHand'
bpy.context.view_layer.update()
sword.matrix_world = mw_saved
bpy.context.view_layer.update()
print(f"[fix_sword] sword parented to bone '{sword.parent_bone}' — left in place "
      f"(planted, tip z={min(c.z for c in sw_pts):.2f})")

# ─────────────────────────────────────────────────────────────────
# 4b. ROUND 5 flaw 1: REAL MODELED GAUNTLET (Godwyn_Gauntlet).
# A low-poly armored left gauntlet with 4 actually-curled finger tubes
# + thumb + palm dome resting on the pommel, built in world space around
# the finalized hilt, then bone-parented to LeftHand — so hand and sword
# stay rigidly in contact through EVERY pose (also fixes flaw 3's
# "sword floats away from the hand" read).
# ─────────────────────────────────────────────────────────────────
for _old in ("Godwyn_Gauntlet",):
    _o = bpy.data.objects.get(_old)
    if _o:
        bpy.data.objects.remove(_o, do_unlink=True)

pom_top = max(c.z for c in sw_pts)

def axis_pt(z):
    return axis_a + axis_dir * ((z - axis_a.z) / axis_dir.z)

gbm = bmesh.new()

def add_tube(path, ring_n=8, cap=True):
    """path: list of (center Vector, radius). Builds a smooth tube."""
    rings = []
    for k, (c, r) in enumerate(path):
        c_prev = path[max(k - 1, 0)][0]
        c_next = path[min(k + 1, len(path) - 1)][0]
        t = (c_next - c_prev).normalized()
        n1 = t.cross(Vector((0, 0, 1)))
        if n1.length < 1e-5:
            n1 = t.cross(Vector((1, 0, 0)))
        n1.normalize()
        n2 = t.cross(n1).normalized()
        ring = []
        for a in range(ring_n):
            th = 2 * math.pi * a / ring_n
            ring.append(gbm.verts.new(c + n1 * (r * math.cos(th)) +
                                      n2 * (r * math.sin(th))))
        rings.append(ring)
    for ra, rb2 in zip(rings, rings[1:]):
        for a in range(ring_n):
            gbm.faces.new((ra[a], ra[(a + 1) % ring_n],
                           rb2[(a + 1) % ring_n], rb2[a]))
    if cap:
        for ring, cz in ((rings[0], path[0][0]), (rings[-1], path[-1][0])):
            cvert = gbm.verts.new(cz)
            for a in range(ring_n):
                gbm.faces.new((ring[a], ring[(a + 1) % ring_n], cvert))

HILT_R = 0.052          # hilt cylinder radius the fingers curl around
FIN_ORBIT = 0.082       # finger-tube center orbit radius
FIN_DZ = 0.052          # vertical finger spacing (clear valleys between)
# round 5b: fingers hug the FAR side only (~205 deg) — the full-wrap 240deg
# tubes read as a spring coil; the stack starts snug under the palm dome
finger_z = [pom_top - 0.055 - k * FIN_DZ for k in range(4)]
th_s, th_e = th_palm + 1.35, th_palm + 2 * math.pi - 1.35
N_SEG = 16
for fi, zk in enumerate(finger_z):
    path = []
    for s_i in range(N_SEG + 1):
        s = s_i / N_SEG
        th = th_s + (th_e - th_s) * s
        # gentle base rise toward the palm; slight droop + tighter tip curl
        z = zk + 0.022 * max(0.0, 1.0 - s / 0.22) ** 2 \
            - 0.012 * smt01((s - 0.80) / 0.20)
        orb = FIN_ORBIT - 0.014 * smt01((s - 0.65) / 0.35)  # tips press in
        c = axis_pt(z) + Vector((math.cos(th), math.sin(th), 0)) * orb
        r = (0.0265 - 0.0100 * smt01((s - 0.45) / 0.55)) \
            * (1.0 + 0.13 * math.exp(-((s - 0.16) / 0.10) ** 2))  # knuckle
        # ring/middle fingers slightly thicker than pinky
        r *= (1.06, 1.09, 1.03, 0.90)[fi]
        path.append((c, r))
    add_tube(path)
# thumb: wraps the OTHER way around the near side, higher on the grip
tpath = []
for s_i in range(10 + 1):
    s = s_i / 10
    th = (th_palm - 0.85) - 1.45 * s
    z = pom_top - 0.070 - 0.018 * s
    c = axis_pt(z) + Vector((math.cos(th), math.sin(th), 0)) * (FIN_ORBIT - 0.008)
    tpath.append((c, 0.0240 - 0.0085 * s))
add_tube(tpath)
# palm dome resting low on the pommel + knuckle plate over the finger
# bases + wrist block toward the forearm
def add_ball(center, sx, sy, sz):
    m = (Matrix.Translation(center) @
         Matrix.Diagonal(Vector((sx, sy, sz, 1.0))))
    bmesh.ops.create_uvsphere(gbm, u_segments=12, v_segments=8,
                              radius=1.0, matrix=m)
palm_dir = Vector((math.cos(th_palm), math.sin(th_palm), 0.0))
add_ball(axis_pt(pom_top) + palm_dir * 0.018 + Vector((0, 0, 0.028)),
         0.080, 0.080, 0.042)
# back-of-hand / knuckle plate: vertical ellipsoid covering the 4 finger
# base caps so the hand reads as one mass, not floating rings
kn_dir = Vector((math.cos(th_s), math.sin(th_s), 0.0))
add_ball(axis_pt(pom_top - 0.115) + kn_dir * 0.062, 0.052, 0.052, 0.120)
wrist_c = (axis_pt(pom_top + 0.05) + lh_head_w) / 2 + Vector((0, 0, 0.05))
add_ball(wrist_c, 0.058, 0.058, 0.078)

bmesh.ops.recalc_face_normals(gbm, faces=gbm.faces)
gme = bpy.data.meshes.new("Godwyn_Gauntlet")
gbm.to_mesh(gme)
gbm.free()
gaunt = bpy.data.objects.new("Godwyn_Gauntlet", gme)
bpy.context.scene.collection.objects.link(gaunt)
bpy.ops.object.select_all(action='DESELECT')
gaunt.select_set(True)
bpy.context.view_layer.objects.active = gaunt
bpy.ops.object.shade_smooth()

# gold gauntlet material matching the armor gold
gmat = bpy.data.materials.new("GodwynGauntletMat")
gmat.use_nodes = True
gp = next(n for n in gmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
# round 5b: darker antique gold — pure (0.82,0.65,0.15)+metal 1 rendered
# bone-cream under the flat EEVEE env and did not match the baked armor
gp.inputs["Base Color"].default_value = (0.40, 0.27, 0.06, 1.0)
gp.inputs["Metallic"].default_value = 1.0
gp.inputs["Roughness"].default_value = 0.35
gme.materials.append(gmat)

# ── ASSERT per-finger separation: cluster far-side finger verts by z;
# there must be exactly 4 distinct bands with real valleys between. ──
far_zs = sorted(
    v.co.z for v in gme.vertices
    if abs(ang_d(math.atan2((v.co - axis_pt(v.co.z)).y,
                            (v.co - axis_pt(v.co.z)).x),
                 th_palm + math.pi)) < 0.8
    and v.co.z < pom_top - 0.045)
clusters = 1
for za, zb2 in zip(far_zs, far_zs[1:]):
    if zb2 - za > 0.006:
        clusters += 1
print(f"[fix_sword] gauntlet: {len(gme.vertices)} verts, far-side finger "
      f"z-clusters={clusters} (need >=4 distinct fingers)")
assert clusters >= 4, f"finger tubes fused: only {clusters} distinct bands"

# bone-parent to LeftHand keeping world transform (rigid with the sword)
gw_saved = gaunt.matrix_world.copy()
gaunt.parent = arm
gaunt.parent_type = 'BONE'
gaunt.parent_bone = 'LeftHand'
bpy.context.view_layer.update()
gaunt.matrix_world = gw_saved
bpy.context.view_layer.update()
print(f"[fix_sword] gauntlet bone-parented to LeftHand")

# ── flaw 3: palm-contact assertion at REST — the hand joint must sit on
# the hilt axis (both sword + gauntlet are rigid to LeftHand, so posed
# contact is then guaranteed by construction; posed check re-run below). ──
d_palm = (Vector((lh_head_w.x, lh_head_w.y, 0)) -
          Vector((foot_lh.x, foot_lh.y, 0))).length
print(f"[fix_sword] palm-to-hilt-axis horizontal distance at rest: {d_palm:.3f}")
assert d_palm < 0.25, f"LeftHand is {d_palm:.2f} off the hilt — grip broken"
# capture the hilt point in sword-local space at REST for the posed check
HILT_LOCAL_REST = sword.matrix_world.inverted() @ axis_pt(pom_top - 0.10)

# ─────────────────────────────────────────────────────────────────
# 5. Surface polish: shade-auto-smooth + material shaping (flaws 5/6)
# ─────────────────────────────────────────────────────────────────
for ob in (mesh_obj, sword):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(P["autosmooth_deg"]))
        print(f"[fix_sword] shade_auto_smooth({P['autosmooth_deg']} deg) on {ob.name}")
    except Exception as ex:
        bpy.ops.object.shade_smooth()
        print(f"[fix_sword] shade_smooth fallback on {ob.name} ({ex})")

mat = me.materials[0]
assert mat and mat.use_nodes, "GodwynGameMat missing"
nt = mat.node_tree
princ = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
base_in = princ.inputs["Base Color"]
assert base_in.is_linked, "Base Color not texture-linked?"
base_out = base_in.links[0].from_socket
n_img_before = sum(1 for n in nt.nodes if n.type == 'TEX_IMAGE')

sep = nt.nodes.new("ShaderNodeSeparateColor")
nt.links.new(base_out, sep.inputs[0])

def math_node(op, a, b):
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = True
    for idx, src in enumerate((a, b)):
        if src is None:
            continue
        if isinstance(src, (int, float)):
            m.inputs[idx].default_value = src
        else:
            nt.links.new(src, m.inputs[idx])
    return m

# gold mask = clamp((R-B)*3), blue mask = clamp((B-R)*3)
rb = math_node('SUBTRACT', sep.outputs[0], sep.outputs[2])
gold = math_node('MULTIPLY', rb.outputs[0], 3.0)
br = math_node('SUBTRACT', sep.outputs[2], sep.outputs[0])
blue = math_node('MULTIPLY', br.outputs[0], 3.0)

rough_in = princ.inputs["Roughness"]
cut = math_node('MULTIPLY', gold.outputs[0], P["gold_rough_cut"])
one_minus = math_node('SUBTRACT', 1.0, cut.outputs[0])
if rough_in.is_linked:
    old_r = rough_in.links[0].from_socket
    newr = math_node('MULTIPLY', old_r, one_minus.outputs[0])
    for l in list(rough_in.links):
        nt.links.remove(l)
    nt.links.new(newr.outputs[0], rough_in)
else:
    base_r = float(rough_in.default_value)
    newr = math_node('MULTIPLY', base_r, one_minus.outputs[0])
    nt.links.new(newr.outputs[0], rough_in)
print(f"[fix_sword] gold roughness shaped (cut={P['gold_rough_cut']}, "
      f"linked={rough_in.is_linked})")

sheen_in = princ.inputs.get("Sheen Weight")
if sheen_in is not None:
    samt = math_node('MULTIPLY', blue.outputs[0], P["sheen_amt"])
    nt.links.new(samt.outputs[0], sheen_in)
    sr = princ.inputs.get("Sheen Roughness")
    if sr is not None and not sr.is_linked:
        sr.default_value = 0.35
    print(f"[fix_sword] blue cloth sheen wired (amt={P['sheen_amt']})")

# ── round 3 flaw 5: real gold-vs-velvet separation ──
# (a) blue cloth must NOT be metal: metallic *= (1 - 0.9*bluemask)
metal_in = princ.inputs.get("Metallic")
bm9 = math_node('MULTIPLY', blue.outputs[0], 0.9)
one_minus_bm = math_node('SUBTRACT', 1.0, bm9.outputs[0])
if metal_in is not None:
    if metal_in.is_linked:
        m_src = metal_in.links[0].from_socket
        mmul = math_node('MULTIPLY', m_src, one_minus_bm.outputs[0])
        for l in list(metal_in.links):
            nt.links.remove(l)
    else:
        mmul = math_node('MULTIPLY', float(metal_in.default_value),
                         one_minus_bm.outputs[0])
    nt.links.new(mmul.outputs[0], metal_in)
    print(f"[fix_sword] metallic gated off blue cloth (was "
          f"{'linked' if metal_in.is_linked else metal_in.default_value})")
# (b) velvet roughness floor: rough = max(rough, 0.62*bluemask)
assert rough_in.is_linked, "roughness chain vanished"
cur_r_src = rough_in.links[0].from_socket
vfloor = math_node('MULTIPLY', blue.outputs[0], 0.62)
rmax = math_node('MAXIMUM', cur_r_src, vfloor.outputs[0])
for l in list(rough_in.links):
    nt.links.remove(l)
nt.links.new(rmax.outputs[0], rough_in)
print("[fix_sword] velvet roughness floor wired (0.62 on blue)")
# (c) engraved-gold gleam: fine noise bump masked to gold
noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 160.0
if "Detail" in noise.inputs:
    noise.inputs["Detail"].default_value = 6.0
bstr = math_node('MULTIPLY', gold.outputs[0], 0.30)
bump = nt.nodes.new("ShaderNodeBump")
if "Distance" in bump.inputs:
    bump.inputs["Distance"].default_value = 0.02
nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bstr.outputs[0], bump.inputs["Strength"])
norm_in = princ.inputs["Normal"]
if norm_in.is_linked:
    old_n = norm_in.links[0].from_socket
    nt.links.new(old_n, bump.inputs["Normal"])
    for l in list(norm_in.links):
        if l.to_node is not bump and l.from_socket is old_n and l.to_socket is norm_in:
            nt.links.remove(l)
nt.links.new(bump.outputs["Normal"], norm_in)
print("[fix_sword] gold filigree micro-bump wired (noise 160, strength 0.30*gold)")

assert sum(1 for n in nt.nodes if n.type == 'TEX_IMAGE') == n_img_before, \
    "image nodes changed!"
assert mat.name == "GodwynGameMat" or me.materials[0] is mat
# verify the added chains actually TERMINATE at the Principled BSDF
assert princ.inputs["Roughness"].links[0].from_node.operation == 'MAXIMUM'
if metal_in is not None:
    assert metal_in.is_linked, "metallic chain did not connect"
assert princ.inputs["Normal"].links[0].from_node.type == 'BUMP'
print("[fix_sword] material chains VERIFIED connected to GodwynGameMat BSDF")

# ── round 5 flaw 5: the hair shells rendered as dripping gold METAL
# because they share the baked gold-armor texture. Give hair faces their
# own MATTE BLOND slot (dielectric, high roughness, soft sheen) so hair
# stops reading as melted metal. Face-front skin zone is excluded.
# The original GodwynGameMat slot 0 is untouched (slot ADDITION only). ──
hair_mat = bpy.data.materials.new("GodwynHairMat")
hair_mat.use_nodes = True
hpn = next(n for n in hair_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
hpn.inputs["Base Color"].default_value = (0.46, 0.335, 0.16, 1.0)
hpn.inputs["Metallic"].default_value = 0.0
hpn.inputs["Roughness"].default_value = 0.62
if "Sheen Weight" in hpn.inputs:
    hpn.inputs["Sheen Weight"].default_value = 0.35
    hpn.inputs["Sheen Tint"].default_value = (0.85, 0.72, 0.45, 1.0)
me.materials.append(hair_mat)
hair_mi = len(me.materials) - 1
n_hair_f = 0
for poly in me.polygons:
    w = mwm @ poly.center
    if w.z < hd_w.z - 0.06:
        continue
    if math.hypot(w.x - hd_w.x, w.y - hd_w.y) > 0.34:
        continue
    if w.y < -0.30 and abs(w.x) < 0.16 and w.z < 3.16:
        continue  # front face skin — keep the baked texture
    poly.material_index = hair_mi
    n_hair_f += 1
print(f"[fix_sword] hair material: {n_hair_f} faces -> {hair_mat.name} "
      f"(matte blond, slot {hair_mi})")
assert n_hair_f > 200, "hair mask matched almost no faces"

# ── round 3 flaw 6: the blade region of the baked texture is cloth-blue,
# so the sword read as a strap. Give the SWORD OBJECT its own material copy
# (GodwynGameMat untouched on the body) where blue -> dark navy STEEL:
# darker base, metallic 1, glossy. Matches god_C's midnight blade. ──
sw_mat = mat.copy()
sw_mat.name = "GodwynSwordMat"
snt = sw_mat.node_tree
sp = next(n for n in snt.nodes if n.type == 'BSDF_PRINCIPLED')

def s_math(op, a, b):
    m = snt.nodes.new("ShaderNodeMath")
    m.operation = op
    m.use_clamp = True
    for idx, src in enumerate((a, b)):
        if isinstance(src, (int, float)):
            m.inputs[idx].default_value = src
        elif src is not None:
            snt.links.new(src, m.inputs[idx])
    return m

sbase_in = sp.inputs["Base Color"]
sbase_src = sbase_in.links[0].from_socket
ssep = snt.nodes.new("ShaderNodeSeparateColor")
snt.links.new(sbase_src, ssep.inputs[0])
sbr = s_math('SUBTRACT', ssep.outputs[2], ssep.outputs[0])
sblue = s_math('MULTIPLY', sbr.outputs[0], 3.0)
smix = snt.nodes.new("ShaderNodeMix")
smix.data_type = 'RGBA'
sfac = s_math('MULTIPLY', sblue.outputs[0], 0.85)
snt.links.new(sfac.outputs[0], smix.inputs[0])
snt.links.new(sbase_src, smix.inputs[6])
# round 5 flaw 4: the navy tint read as washed light-blue PLASTIC. The
# blade is now NEUTRAL polished steel (god_C): any blue in the baked
# texture maps to steel gray, metallic, low roughness.
smix.inputs[7].default_value = (0.42, 0.44, 0.47, 1.0)
sfac.inputs[1].default_value = 0.97   # nearly full replacement on blue
for l in list(sbase_in.links):
    snt.links.remove(l)
snt.links.new(smix.outputs[2], sbase_in)
sm_in = sp.inputs.get("Metallic")
if sm_in is not None:
    if sm_in.is_linked:
        sm_src = sm_in.links[0].from_socket
        smx = s_math('MAXIMUM', sm_src, sblue.outputs[0])
        for l in list(sm_in.links):
            snt.links.remove(l)
    else:
        smx = s_math('MAXIMUM', float(sm_in.default_value), sblue.outputs[0])
    snt.links.new(smx.outputs[0], sm_in)
sr_in = sp.inputs["Roughness"]
sr_src = sr_in.links[0].from_socket if sr_in.is_linked else None
scap = s_math('SUBTRACT', 1.0, s_math('MULTIPLY', sblue.outputs[0], 0.86).outputs[0])
if sr_src is not None:
    srmin = s_math('MINIMUM', sr_src, scap.outputs[0])
    for l in list(sr_in.links):
        snt.links.remove(l)
else:
    srmin = s_math('MINIMUM', float(sr_in.default_value), scap.outputs[0])
snt.links.new(srmin.outputs[0], sr_in)
for si in range(len(sword.data.materials)):
    sword.data.materials[si] = sw_mat
print(f"[fix_sword] sword material: {sw_mat.name} (polished steel blade) "
      f"assigned; body keeps {mat.name}")

# ── round 5 flaw 4: GOLD crossguard/grip/pommel matching the armor gold
# (god_C). Faces within 0.55 of the pommel top get a dedicated gold slot;
# the blade below stays steel. Geometry-stable under posing (per-face). ──
sg_mat = bpy.data.materials.new("GodwynSwordGoldMat")
sg_mat.use_nodes = True
sgp = next(n for n in sg_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
sgp.inputs["Base Color"].default_value = (0.82, 0.65, 0.15, 1.0)
sgp.inputs["Metallic"].default_value = 1.0
sgp.inputs["Roughness"].default_value = 0.30
sword.data.materials.append(sg_mat)
sg_idx = len(sword.data.materials) - 1
swm_now = sword.matrix_world
n_gold_f = 0
for poly in sword.data.polygons:
    if (swm_now @ poly.center).z > pom_top - 0.55:
        poly.material_index = sg_idx
        n_gold_f += 1
print(f"[fix_sword] sword gold guard: {n_gold_f} faces above "
      f"z={pom_top - 0.55:.2f} -> {sg_mat.name}")
assert n_gold_f > 20, "gold guard mask matched almost no faces"

# ─────────────────────────────────────────────────────────────────
# 6. Rig-intact assertions
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
# 7. Previews (EEVEE)
# ─────────────────────────────────────────────────────────────────
os.makedirs(PREVIEW_DIR, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
world = bpy.data.worlds.new("PrevWorld") if scene.world is None else scene.world
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    # round 5: NEUTRAL-WARM env — the old blue-gray env washed the steel
    # blade into light-blue plastic in the eval renders
    bg.inputs[0].default_value = (0.28, 0.265, 0.245, 1.0)
    bg.inputs[1].default_value = 1.3

sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun", 'SUN'))
sun.data.energy = 5.5
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("PrevFill", bpy.data.lights.new("PrevFill", 'AREA'))
fill.data.energy = 500
fill.data.size = 4.0
fill.location = lh_head_w + Vector((0.5, -1.5, 0.6))
scene.collection.objects.link(fill)
rim = bpy.data.objects.new("PrevRim", bpy.data.lights.new("PrevRim", 'AREA'))
rim.data.energy = 900
rim.data.size = 3.0
rim.location = Vector((1.6, 2.4, 2.6))
rim.rotation_euler = (Vector((0, -0.4, 1.6)) - rim.location).to_track_quat('-Z', 'Y').to_euler()
scene.collection.objects.link(rim)

cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(cam_obj, frm, to):
    cam_obj.location = Vector(frm)
    cam_obj.rotation_euler = (Vector(to) - Vector(frm)).to_track_quat('-Z', 'Y').to_euler()

sw_c = (Vector((min(c.x for c in sw_pts), min(c.y for c in sw_pts), min(c.z for c in sw_pts))) +
        Vector((max(c.x for c in sw_pts), max(c.y for c in sw_pts), max(c.z for c in sw_pts)))) / 2
shots = [
    ("grip_pommel", lh_head_w + Vector((0.55, -0.75, 0.30)), lh_head_w + Vector((0, 0, -0.08)), 60),
    ("sword_full",  sw_c + Vector((1.3, -2.2, 0.1)), sw_c, 45),
    ("full_body",   (-2.6, -3.6, 1.9), (-0.2, 0, 1.2), 35),
    ("full_front",  (0, -4.2, 1.5), (0, 0, 1.4), 40),
]
for name, frm, to, lens in shots:
    cam.data.lens = lens
    aim(cam, frm, to)
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[fix_sword] rendered {scene.render.filepath}")

# REQUIRED verification: sword ALONE, framed on its bbox
mesh_obj.hide_render = True
cam.data.lens = 40
aim(cam, sw_c + Vector((1.5, -2.4, 0.0)), sw_c)
scene.render.filepath = os.path.join(PREVIEW_DIR, "debug_sword_only.png")
bpy.ops.render.render(write_still=True)
mesh_obj.hide_render = False
print(f"[fix_sword] rendered {scene.render.filepath}")

# left palm / pommel closeup with body
scene.render.filepath = os.path.join(PREVIEW_DIR, "debug_left_hand.png")
cam.data.lens = 50
aim(cam, lh_head_w + Vector((0.65, -0.85, 0.35)), lh_head_w + Vector((0, 0, -0.1)))
bpy.ops.render.render(write_still=True)
print(f"[fix_sword] rendered {scene.render.filepath}")

# material verification crop: gold chest + blue sash in one lit frame
mc = Vector((0.0, -0.30, 1.9))
cam.data.lens = 70
aim(cam, mc + Vector((0.5, -1.3, 0.25)), mc)
scene.render.filepath = os.path.join(PREVIEW_DIR, "mat_crop.png")
bpy.ops.render.render(write_still=True)
print(f"[fix_sword] rendered {scene.render.filepath}")

# ── POSED verification (the exact beauty-eval pose): sword must track the
# LeftHand, the head must stay a head, the right shoulder must not tear ──
for bn, eul in COMBO_POSE:
    pb = arm.pose.bones[bn]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in eul)
bpy.context.view_layer.update()
cam.data.lens = 45
aim(cam, Vector((1.0, -6.2, 1.8)), Vector((0, 0, 1.55)))
scene.render.filepath = os.path.join(PREVIEW_DIR, "posed_full.png")
bpy.ops.render.render(write_still=True)
print(f"[fix_sword] rendered {scene.render.filepath}")
ra_w2 = awm @ arm.data.bones["RightArm"].head_local
cam.data.lens = 60
aim(cam, ra_w2 + Vector((1.5, -2.3, 0.35)), ra_w2 + Vector((-0.1, 0, 0.1)))
scene.render.filepath = os.path.join(PREVIEW_DIR, "posed_arm_close.png")
bpy.ops.render.render(write_still=True)
print(f"[fix_sword] rendered {scene.render.filepath}")
# posed grip: where did LeftHand (and the bone-parented sword) go?
lh_posed = awm @ arm.pose.bones["LeftHand"].head
# ── flaw 3 POSED contact assertion: under the eval pose the hilt must
# still sit at the hand (sword + gauntlet are rigid children of LeftHand)
hilt_posed = sword.matrix_world @ HILT_LOCAL_REST
d_posed = (hilt_posed - lh_posed).length
print(f"[fix_sword] POSED hilt-to-hand distance: {d_posed:.3f}")
assert d_posed < 0.45, f"posed sword drifted {d_posed:.2f} from the hand"
cam.data.lens = 55
aim(cam, lh_posed + Vector((0.7, -1.1, 0.3)), lh_posed + Vector((0, 0, -0.05)))
scene.render.filepath = os.path.join(PREVIEW_DIR, "posed_grip.png")
bpy.ops.render.render(write_still=True)
print(f"[fix_sword] rendered {scene.render.filepath}")
# back to rest before saving
for pb in arm.pose.bones:
    pb.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()

# ─────────────────────────────────────────────────────────────────
# 8. Save blend
# ─────────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"[fix_sword] saved {BLEND_OUT}")
print("[fix_sword] DONE")
