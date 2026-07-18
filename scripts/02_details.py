"""
02_details.py — Phase 2: DRESS + HAIR + SWORD for Godwyn the Golden.

Builds on the MPFB2 anatomical body from 01_base_human.py
(models/godwyn_phase1.blend, object "Godwyn_Body", 3.2m, faces -Y).

Adds five objects to the "Godwyn" collection (idempotent — deletes any
prior versions by name, rebuilds, saves back to the same .blend):

  Godwyn_Armor  RE-OUTFIT: ornate near-FULL GOLD PLATE — engraved cuirass
                (breast+back, chest fully covered) + plackart ab lames,
                gorget collar lames, layered pauldrons, rerebraces +
                couters + vambraces + plate gauntlets over the hands,
                4-lame faulds + 6 hanging tassets + plate belt, cuisses,
                poleyns, greaves and articulated SABATONS (not barefoot).
                Plates are body-offset shells: real thickness (solidify),
                chamfered edges (bevel), rimmed with edge-trim ribs.
                Sternum filigree rides ON the breastplate.
  Godwyn_Tabard the deep-BLUE cloth INTEGRATED into the armor: a hanging
                front TABARD/SURCOAT panel (waist belt -> floor), side +
                trailing back panels, a blue underlayer band beneath the
                gold underskirt hem, gold laurel EMBROIDERY on every edge.
                (The back CAPE is GONE — SPEC updated: never a cape.)
  Godwyn_Hair   long golden-blonde: scalp cap + ~300 fine flowing strands
                down the back + ONE asymmetric side braid (right temple,
                merging into the loose hair). Reads as hair, not a wreath.
  Godwyn_Sword  longsword — gold grip/pommel/filigree crossguard, subtle
                blue-tinged tapered blade. OBJECT ORIGIN AT THE GRIP.
                Gripped firmly in the right hand, tip toward the ground.
  Godwyn_Eyes   solid eyeball spheres (sclera + protruding cornea) seated
                in the opened sockets; banded sclera/iris/pupil materials.

MESO DETAIL PASS: skirt carries sharpened cartridge pleats + a flowing
uneven hem; tabard panels hang in graded pleats with scalloped hems;
pauldrons carry engraving channels, rivet studs and a crest ridge; bracers
carry rings + studs; hair grows as clumped locks with lateral flow waves
and coherent front-fall bundles; the braid plait is tighter. Everything
stays parented/skinned to the ONE armature by 04 (animatable invariant).

PHASE-1 rules honoured (SPEC updated): NO crown, NO markings, near-full
gold plate coverage — only the face (and a little neck) reads as skin.
Deterministic (seeded), export-friendly (baked transforms, Godwyn_*
names, single collection). Renders GPU (OptiX) previews to
renders/wip/phase2/.

Usage:
  blender --background --python ~/godwyn-boss-fight/scripts/02_details.py 2>&1
"""
import bpy
import bmesh
import sys
import os
import math
import random
from mathutils import Vector, Euler, Matrix

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import lib_godwyn as G

REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO_ROOT, "models", "godwyn_phase1.blend")
WIP_DIR = os.path.join(REPO_ROOT, "renders", "wip", "phase2")
os.makedirs(WIP_DIR, exist_ok=True)

random.seed(1420)

# ---------------------------------------------------------------------------
# Landmarks measured from Godwyn_Body (p2_probe_landmarks.py +
# p5_probe_face_hand.py). Body faces -Y.
# ---------------------------------------------------------------------------
NECK_BASE = Vector((0.0, 0.20, 2.66))
HEAD_C = Vector((0.0, 0.135, 2.99))       # head centre
ELBOW_R = Vector((0.75, 0.125, 2.17))
WRIST_R = Vector((0.88, -0.19, 1.99))
HAND_R = Vector((0.98, -0.28, 1.84))      # right palm centroid
WAIST_Z = 1.97
HEM_Z = 0.40                              # robe hem — bare feet MUST read below

# ---------------------------------------------------------------------------
# ARM STRETCH (RE-OUTFIT fixer r4 blocker #8: "arms are stubby relative to
# the 3.2m heroic frame"). A +9% along-axis stretch of each arm about the
# shoulder: verts between shoulder and wrist slide outward along the arm
# axis proportionally to their axial distance; the HAND (past the wrist)
# translates RIGIDLY so the sculpted hand shape/thresholds just shift.
# ELBOW_R / WRIST_R / HAND_R and every hand-region threshold are transformed
# through the SAME function in main() — 04's finger-chain landmarks
# (_WRIST_LM/_HAND_LM) carry the matching stretched values.
# ---------------------------------------------------------------------------
ARM_K = 1.26       # fixer r5 blocker #8: 1.09 -> 1.16 (fingertips must
                   # reach mid-thigh; at 1.09 they barely passed the faulds)
                   # phase4 fixer r1 blocker #3: 1.16 -> 1.26 — arms still
                   # read short/stubby at Cam_Full against the slimmed
                   # cuirass; 04's bone table carries the matching 1.26.
_ARM_S = Vector((0.40, 0.08, 2.285))          # shoulder pivot (right side)
_ARM_AXIS = (Vector((0.88, -0.19, 1.99)) - _ARM_S).normalized()
_ARM_DW = (Vector((0.88, -0.19, 1.99)) - _ARM_S).length   # shoulder->wrist
# rigid translation applied to everything at/past the wrist:
_HAND_SH = _ARM_AXIS * ((_ARM_DW - 0.02) * (ARM_K - 1.0))


def _arm_stretch(co):
    """Stretched position for one point (pure transform, both sides)."""
    sgn = 1.0 if co.x >= 0.0 else -1.0
    S = Vector((sgn * _ARM_S.x, _ARM_S.y, _ARM_S.z))
    ax = Vector((sgn * _ARM_AXIS.x, _ARM_AXIS.y, _ARM_AXIS.z))
    d = (co - S).dot(ax)
    if d <= 0.02:
        return co.copy()
    dd = min(d, _ARM_DW) - 0.02
    fade = min(1.0, dd / 0.10)                # smooth engage past the shoulder
    return co + ax * (dd * (ARM_K - 1.0) * fade)

# ---------------------------------------------------------------------------
# HEROIC PROPORTION PASS (fixer r5 blocker #8: "toy/action-figure read —
# legs short relative to the torso block, head doll-like"). Applied at the
# END of main() to the FINISHED body+armor+tabard+hair+eyes (so every armor
# piece that conformed to the body deforms with it and stays conformal):
#   1. head narrowed 5% in x (soft ramp above the neck base),
#   2. legs lengthened: z*LEG_K below the hip plane LEG_Z0 (shin+thigh +9%),
#      everything above rigidly shifted up,
#   3. whole figure renormalized uniformly back to exactly 3.2m.
# The sword transforms RIGIDLY (its grip sits above the leg-stretch kink; a
# piecewise z-map would bend the straight blade). 04_rig applies the SAME
# transform to its bone table / finger-chain landmarks (see 04 _prop_pt).
# ---------------------------------------------------------------------------
LEG_K = 1.09
LEG_Z0 = 1.392
PROP_S = 3.20 / (3.20 + LEG_Z0 * (LEG_K - 1.0))


def _prop_remap(co):
    """Final-proportion position for one point (pure transform)."""
    z = co.z * LEG_K if co.z <= LEG_Z0 else co.z + LEG_Z0 * (LEG_K - 1.0)
    return Vector((co.x * PROP_S, co.y * PROP_S, z * PROP_S))


# runtime chest-front sampler (replaces the old hardcoded table, which sat
# ~15mm behind the real MPFB2 surface and made the filigree float)
_FRONT_VERTS = []      # filled by init_surface_sampler(body)


def init_surface_sampler(body):
    """Cache front-hemisphere torso verts for surf_y() conform sampling."""
    global _FRONT_VERTS
    _FRONT_VERTS = [v.co.copy() for v in body.data.vertices
                    if v.co.y < 0.20 and 1.8 < v.co.z < 2.75]
    print(f"[02_details] surface sampler: {len(_FRONT_VERTS)} front verts")


def surf_y(x, z, default=0.03):
    """Front (min-y) body surface at (x, z) — filigree conforms to this.

    r3 (major #5): tight window FIRST (the old wide 35x30mm window caught the
    pec bulge when sampling the steeply-receding clavicle line, floating the
    bar ~2cm off the sternum), then progressively widen before defaulting.
    """
    for wx, wz in ((0.020, 0.014), (0.035, 0.025), (0.060, 0.045)):
        ys = sorted(co.y for co in _FRONT_VERTS
                    if abs(co.x - x) < wx and abs(co.z - z) < wz)
        if ys:
            # average the few frontmost verts: min-of-window alone is noisy
            # and produced ragged/spiky ribbon edges near the pecs (r3)
            k = min(4, len(ys))
            return sum(ys[:k]) / k
    return default


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def link_obj(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    link_obj(ob)
    if mat:
        me.materials.append(mat)
    return ob


def shade_smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


def apply_mods(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name + "_Mesh"
    # p5b fixer r3 blocker #4: kill flipped/degenerate shards (a black
    # triangle rendered on the robe under the filigree). Every joined
    # assembly gets consistent outward normals + degenerate faces dissolved.
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    n1 = len(bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    if n0 != n1:
        print(f"[02_details] {name}: dissolved {n0 - n1} degenerate faces")
    return ob


def sphere_shell(name, loc, scale, rot_euler, mat, keep_z=-0.10,
                 thickness=0.014, seg=28, rings=18):
    """Partial UV-sphere shell (armor plate). keep_z: keep unit-sphere verts
    with local z > keep_z. Transform baked into vertices (identity object)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    doomed = [v for v in bm.verts if v.co.z <= keep_z]
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    R = Euler(rot_euler, "XYZ").to_matrix()
    for v in me.vertices:
        c = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
        v.co = loc + R @ c
    ob = bpy.data.objects.new(name, me)
    link_obj(ob)
    me.materials.append(mat)
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = -1.0
    apply_mods(ob)
    shade_smooth(ob)
    return ob


def curve_obj(name, splines, bevel, mat, cyclic=False, resolution=16):
    """splines: list of list[(Vector pt, radius_scale)] -> beveled bezier mesh."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    cu.resolution_u = resolution
    for pts in splines:
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(len(pts) - 1)
        for bp, (co, rad) in zip(sp.bezier_points, pts):
            bp.co = co
            bp.handle_left_type = bp.handle_right_type = "AUTO"
            bp.radius = rad
        sp.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, cu)
    link_obj(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    if mat:
        ob.data.materials.append(mat)
    shade_smooth(ob)
    return ob


def cylinder_between(name, p0, p1, r0, r1, mat, seg=20):
    """Tapered open tube from p0 to p1 (baked verts, identity object)."""
    axis = (p1 - p0)
    length = axis.length
    q = axis.normalized().to_track_quat("Z", "Y").to_matrix()
    verts, faces = [], []
    rings = 6
    for i in range(rings):
        t = i / (rings - 1)
        r = r0 + (r1 - r0) * t
        z = t * length
        for j in range(seg):
            a = 2 * math.pi * j / seg
            local = Vector((r * math.cos(a), r * math.sin(a), z))
            verts.append(p0 + q @ local)
    for i in range(rings - 1):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    ob = mesh_obj(name, verts, faces, mat)
    shade_smooth(ob)
    return ob


def uv_sphere(name, loc, scale, mat, seg=24, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for v in me.vertices:
        v.co = Vector((loc[0] + v.co.x * scale[0],
                       loc[1] + v.co.y * scale[1],
                       loc[2] + v.co.z * scale[2]))
    ob = bpy.data.objects.new(name, me)
    link_obj(ob)
    me.materials.append(mat)
    shade_smooth(ob)
    return ob


def surface_ribbon(name, path, half_w, mat, off=0.0060, thick=0.014):
    """
    Flat filigree ribbon CONFORMED to the chest (r3 major #5): every edge
    vertex samples the real body surface via surf_y(), so the strip bends
    with the pecs/sternum instead of bridging across them like a floating
    handlebar. path = [(x, z, width_scale), ...]; solidified to `thick`,
    sitting `off` proud of the skin (back face lands on/just inside it).
    """
    verts, faces = [], []
    n = len(path)
    for i, (x, z, ws) in enumerate(path):
        x0, z0, _ = path[max(0, i - 1)]
        x1, z1, _ = path[min(n - 1, i + 1)]
        t = Vector((x1 - x0, 0.0, z1 - z0))
        t = t.normalized() if t.length > 1e-9 else Vector((1.0, 0.0, 0.0))
        s = Vector((-t.z, 0.0, t.x))          # in-plane side direction
        w = max(half_w * ws, 0.004)
        for e in (-1.0, 1.0):
            px = x + s.x * w * e
            pz = z + s.z * w * e
            verts.append(Vector((px, surf_y(px, pz) - off, pz)))
    for i in range(n - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
    ob = mesh_obj(name, verts, faces, mat)
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 0.0                          # centred: guarantees skin contact
    apply_mods(ob)
    shade_smooth(ob)
    return ob


def mirror_x(ob, name):
    """Duplicate a baked-vert object mirrored across x=0."""
    me = ob.data.copy()
    me.name = name + "_Mesh"
    for v in me.vertices:
        v.co.x = -v.co.x
    me.flip_normals()
    new = bpy.data.objects.new(name, me)
    link_obj(new)
    return new


# ---------------------------------------------------------------------------
# PLATE HELPERS (re-outfit): rigid gold plate extracted from the body surface.
# body_shell guarantees fit (the plate IS the body, offset), smoothing mutes
# the anatomy so it reads as forged plate rather than painted skin, solidify
# gives every plate real thickness, and the bevel modifier chamfers the rims.
# ---------------------------------------------------------------------------

def _smooth_loop(pts, iters=3):
    n = len(pts)
    for _ in range(iters):
        pts = [(pts[(i - 1) % n] + pts[i] * 2.0 + pts[(i + 1) % n]) * 0.25
               for i in range(n)]
    return pts


def _chamfer(ob, width=0.0030):
    bev = ob.modifiers.new("Bev", "BEVEL")
    bev.width = width
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(40)


def body_shell(body, name, mat, keep, offset=0.009, thickness=0.008,
               smooth_iters=14, smooth_fac=0.5, bevel=0.0028,
               trim=None, trim_smooth=3, floor=None, clearance_fac=0.60,
               suppress=(), conform=True):
    """Rigid plate lifted off the body: keep faces whose verts all satisfy
    keep(co); smooth; inflate along normals by `offset`; solidify inward to
    `thickness`; chamfer edges. trim = bevel radius for boundary edge-trim
    ribs (classic plate rims). Returns [shell, *trim_ribs].

    conform=False (RE-OUTFIT fixer r1 blockers #1/#2/#3): SKIP the
    clamp-back-to-original-anatomy pass. The clamp guaranteed no sink-holes
    but it RESTORED every muscle bump (pecs/abs/calves/toes) into the plate,
    so the armor rendered as gold-painted skin. Non-conforming plates rely
    on heavy smoothing + the BVH minimum-clearance pass only, and get an
    extra post-clearance smoothing round so the clearance push-outs never
    re-print anatomy."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    doomed = [f for f in bm.faces if not all(keep(v.co) for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces],
                     context="VERTS")
    assert len(bm.verts) > 8, f"body_shell {name}: empty region"
    # r1 fix: smoothing SHRINKS convex regions (mm..cm on limbs) — plates sank
    # INSIDE the body (bare chest/thighs/toes, gold poking through only at
    # bulges). Remember the original surface, smooth, then CLAMP every vert
    # back to >= its original position along the original normal.
    # r4 fix: smoothing also CONTRACTS the open boundary tangentially (the
    # cuirass neckline receded ~5cm into a bare V-neck no matter how far the
    # keep-bounds were pushed). PIN boundary verts — only interior smooths.
    bm.normal_update()
    orig = {v.index: (v.co.copy(), v.normal.copy()) for v in bm.verts}
    pinned = set()
    for e in bm.edges:
        if len(e.link_faces) == 1:
            pinned.add(e.verts[0].index)
            pinned.add(e.verts[1].index)
    interior = [v for v in bm.verts if v.index not in pinned]
    for _ in range(smooth_iters):
        bmesh.ops.smooth_vert(bm, verts=interior, factor=smooth_fac,
                              use_axis_x=True, use_axis_y=True,
                              use_axis_z=True)
    bm.verts.ensure_lookup_table()

    def _suppressed(pt):
        return any((pt - sc).length < sr for sc, sr in suppress)

    if conform:
        for v in bm.verts:
            oco, onrm = orig[v.index]
            if _suppressed(oco):
                continue              # let smoothing erase this bump
            d = (v.co - oco).dot(onrm)
            if d < 0.0:
                v.co -= onrm * d      # back onto the original skin surface
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    # r3: light post-smooth rounds off residual anatomy bumps (nipples read
    # THROUGH the plate as golden skin) without the shrink of the heavy pass
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=interior, factor=0.30,
                              use_axis_x=True, use_axis_y=True,
                              use_axis_z=True)
    # r2 fix: per-origin clamping misses TANGENTIAL smoothing drift (verts
    # slide sideways down steep slopes — chest/pecs stayed bare). Enforce a
    # minimum clearance against the WHOLE body surface via BVH. Clearance is
    # DELIBERATELY smaller than `offset` so it only closes true sink-holes
    # without re-conforming the plate to every skin bump.
    from mathutils.bvhtree import BVHTree
    bbm = bmesh.new()
    bbm.from_mesh(body.data)
    bvh = BVHTree.FromBMesh(bbm)
    bbm.free()
    clearance = offset * clearance_fac

    def _clearance_pass():
        for v in bm.verts:
            loc, nrm, _, _ = bvh.find_nearest(v.co)
            if loc is None:
                continue
            if _suppressed(loc):
                continue
            d = (v.co - loc).dot(nrm)
            if d < clearance:
                v.co += nrm * (clearance - d)

    _clearance_pass()
    if not conform:
        # forge pass: smooth away the clearance push-outs (which re-print
        # anatomy bumps at reduced amplitude), then re-clear once so the
        # plate ends smooth AND outside the skin.
        for _ in range(3):
            bmesh.ops.smooth_vert(bm, verts=interior, factor=0.35,
                                  use_axis_x=True, use_axis_y=True,
                                  use_axis_z=True)
        _clearance_pass()
    for v in bm.verts:
        if floor is not None and v.co.z < floor:
            v.co.z = floor
    # boundary loops for edge trim (walk 1-face edges), BEFORE solidify
    loops = []
    if trim:
        adj = {}
        for e in bm.edges:
            if len(e.link_faces) == 1:
                a, b = e.verts
                adj.setdefault(a.index, []).append(b.index)
                adj.setdefault(b.index, []).append(a.index)
        co = {v.index: v.co.copy() for v in bm.verts}
        visited = set()
        for st in adj:
            if st in visited:
                continue
            loop = [st]
            visited.add(st)
            prev, cur = None, st
            while True:
                nxt = [n for n in adj[cur] if n != prev and n not in visited]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
                loop.append(cur)
                visited.add(cur)
            if len(loop) >= 8:
                loops.append(_smooth_loop([co[i] for i in loop], trim_smooth))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    link_obj(ob)
    me.materials.append(mat)
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = min(thickness, offset + 0.002)
    sol.offset = -1.0
    _chamfer(ob, bevel)
    apply_mods(ob)
    shade_smooth(ob)
    out = [ob]
    for k, loop in enumerate(loops):
        out.append(curve_obj(f"{name}_trim{k}", [[(p, 1.0) for p in loop]],
                             trim, mat, cyclic=True))
    return out


def body_radial(body, z, n=96, win=0.05, xmax=0.45):
    """Per-angle max radial extent of the body cross-section near height z.
    Returns (cy, [r_0..r_n-1]) with angle a measured from +y (back):
    point(a) = (r*sin(a), cy + r*cos(a)). r5 fix: the hip cross-section is
    NOT an ellipse — analytic fauld hoops left the hip-front corners bare."""
    # exclude the arms/hands (they hang through the waist z-band!)
    sel = [v.co for v in body.data.vertices
           if abs(v.co.z - z) < win and abs(v.co.x) < xmax
           and math.hypot(v.co.x, v.co.y - 0.20) < 0.50]
    assert sel, f"body_radial: no verts at z={z}"
    ymin = min(c.y for c in sel)
    ymax = max(c.y for c in sel)
    cy = 0.5 * (ymin + ymax)
    radii = [0.0] * n
    step = 2 * math.pi / n
    for c in sel:
        a = math.atan2(c.x, c.y - cy) % (2 * math.pi)
        r = math.hypot(c.x, c.y - cy)
        k = int(a / step) % n
        for kk in (k - 1, k, k + 1):
            kk %= n
            if r > radii[kk]:
                radii[kk] = r
    # fill empty sectors from neighbours, then light circular smoothing
    for _ in range(n):
        holes = [i for i in range(n) if radii[i] == 0.0]
        if not holes:
            break
        for i in holes:
            radii[i] = max(radii[(i - 1) % n], radii[(i + 1) % n])
    for _ in range(2):
        radii = [max(radii[i],
                     0.25 * radii[(i - 1) % n] + 0.5 * radii[i]
                     + 0.25 * radii[(i + 1) % n]) for i in range(n)]
    return cy, radii


def loft_band(name, rings, mat, thickness=0.009, bevel=0.0028):
    """Skin a stack of equal-length rings into a rigid band (fauld lame,
    gorget lame). Solidified + chamfered."""
    ns = len(rings[0])
    verts, faces = [], []
    for ring in rings:
        verts += ring
    for i in range(len(rings) - 1):
        for j in range(ns):
            a = i * ns + j
            b = i * ns + (j + 1) % ns
            faces.append((a, b, b + ns, a + ns))
    ob = mesh_obj(name, verts, faces, mat)
    # ensure outward normals before solidify
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = -1.0
    _chamfer(ob, bevel)
    apply_mods(ob)
    shade_smooth(ob)
    return ob


# ---------------------------------------------------------------------------
# FACE — open the eyelids + seat the MPFB2 eyeball helpers (blocker #2)
# ---------------------------------------------------------------------------

def enlarge_head(body, factor=1.09, z_lo=2.70, z_hi=2.86):
    # phase4 fixer r1 blocker #3: 1.06 -> 1.09 — the head read small against
    # the (now slimmed) cuirass barrel; rebalances the figurine proportions.
    """
    r3 minor #8: shoulders read overly broad vs the head. Gently scale the
    head about HEAD_C with a smooth blend through the neck (z_lo..z_hi) so
    there is no seam. Runs BEFORE refine_face/build_hair/build_eyes, which
    all measure the live mesh — everything downstream follows automatically.
    """
    me = body.data
    moved = 0
    for v in me.vertices:
        t = (v.co.z - z_lo) / (z_hi - z_lo)
        t = max(0.0, min(1.0, t))
        if t <= 0.0:
            continue
        s = 1.0 + (factor - 1.0) * (t * t * (3 - 2 * t))   # smoothstep
        v.co = HEAD_C + (v.co - HEAD_C) * s
        moved += 1
    me.update()
    print(f"[02_details] head enlarged x{factor} ({moved} verts, "
          f"blend z {z_lo}-{z_hi})")


def _group_verts(body, gname):
    vg = body.vertex_groups.get(gname)
    if vg is None:
        return set()
    gi = vg.index
    return {v.index for v in body.data.vertices
            if any(g.group == gi and g.weight > 0.0 for g in v.groups)}


def refine_face(body):
    """
    Fixer r2 blockers #1 + #3.

    EYES: the MPFB2 helper eyeballs rendered as hollow black sockets with
    leaking pupil geometry. Here we (a) measure each helper eye's centre +
    radius, (b) open the lids around it, (c) DELETE the broken helper
    geometry from the body, and return the eye data so build_eyes() can
    replace them with proper solid eyeball spheres (separate Godwyn_Eyes
    object: sclera sphere + protruding cornea, no gaps).

    FACE: sculpt real lips (upper+lower volume, philtrum) from the 'lips'
    vertex group, raise a soft brow ridge above the eyes, and flatten the
    fin-like ears against the skull ('ears' vertex group).

    Returns [(centre, radius), ...] for build_eyes().
    """
    me = body.data
    eye_data = []
    all_eye_idx = set()
    for side, gname in (("L", "helper-l-eye"), ("R", "helper-r-eye")):
        eye_idx = _group_verts(body, gname)
        if not eye_idx:
            print(f"[02_details] WARNING: {gname} missing — eye skipped",
                  file=sys.stderr)
            continue
        pts = [me.vertices[i].co.copy() for i in eye_idx]
        c = sum(pts, Vector()) / len(pts)
        r = max((p - c).length for p in pts)
        eye_data.append((c, r))
        all_eye_idx |= eye_idx

        # open the lids: non-eye verts near the socket, front of the eye.
        # r4 (major #2): NO asymmetry — the r3 'droop' made the left/right
        # lids visibly differ and the eyes read as uneven slits. Both lids
        # now open identically, slightly wider so iris+pupil read at
        # full-body distance.
        for v in me.vertices:
            if v.index in eye_idx:
                continue
            dx = v.co.x - c.x
            dz = v.co.z - c.z
            d = math.sqrt(dx * dx + dz * dz)
            if d > r * 1.75 or v.co.y > c.y + 0.01:
                continue
            fall = max(0.0, 1.0 - d / (r * 1.75)) ** 1.5
            # p5b fixer r3 blocker #1: the r4 wide-open lids exposed a
            # doll-white sclera frame all around the iris. Aperture reduced
            # so the upper lid OVERLAPS the ball (no white above the iris).
            # phase4 fixer r2 blocker #1 ("wide bug-eyed stare, flat lid
            # rims"): upper-lid lift cut ~30% (0.0038 -> 0.0026) — HOODED,
            # noble half-lowered gaze; the lid shelf in sculpt_face below
            # overhangs the ball so the aperture reads set back under bone.
            if dz > 0.002:      # upper lid: hooded, barely lifted
                v.co.z += 0.0026 * fall
                v.co.y += 0.0020 * fall
            elif dz < -0.002:   # lower lid: drop slightly
                v.co.z -= 0.0024 * fall
                v.co.y += 0.0013 * fall
        print(f"[02_details] eye {side}: lids opened @ "
              f"({c.x:.3f},{c.y:.3f},{c.z:.3f}) r={r:.3f}")

    # -- delete the broken helper eyeballs (replaced by Godwyn_Eyes) ----------
    if all_eye_idx:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        doomed = [bm.verts[i] for i in all_eye_idx]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(me)
        bm.free()
        print(f"[02_details] helper eyeballs deleted ({len(all_eye_idx)} verts)")

    sculpt_face(body, eye_data)
    me.update()
    return eye_data


def sculpt_face(body, eye_data):
    """Real lips + philtrum, soft brow ridge, ears flattened (blocker #3)."""
    me = body.data

    # -- LIPS: volume from the real MPFB2 'lips' vertex group -----------------
    lip_idx = _group_verts(body, "lips")
    if lip_idx:
        lip_idx = {i for i in lip_idx if i < len(me.vertices)}
        pts = [me.vertices[i].co for i in lip_idx]
        c = sum((p.copy() for p in pts), Vector()) / len(pts)
        half_w = max(abs(p.x - c.x) for p in pts) or 1e-4
        for i in lip_idx:
            v = me.vertices[i]
            lat = max(0.0, 1.0 - abs(v.co.x - c.x) / half_w) ** 0.8
            dz_lip = v.co.z - c.z
            # p5 fixer r1 blocker #1: lips were near-invisible in the
            # Cam_Face close-up — volume pushed well past the r4 values so
            # the mouth reads as a real sculpted feature, not a shading hint.
            # p5b fixer r3 blocker #1: the r1 volumes ballooned the mouth
            # into a tiny sphere-purse. Forward volume CUT ~35%; the width
            # pass below spreads the mouth laterally into a masculine form.
            # phase4 fixer r2 blocker #1 ("blobby undefined lips"): forward
            # volumes cut ~18% and the width pass below drops 22% -> 10% —
            # a narrower, more defined mouth.
            if dz_lip >= 0:                         # upper lip
                out = 0.0058 * lat
                # philtrum: subtle central dip on the upper lip
                # phase4 fixer r4 blocker #1: dip deepened 0.45 -> 0.32 —
                # the philtrum column must read at Cam_Face
                if abs(v.co.x - c.x) < half_w * 0.14:
                    out *= 0.32
                v.co.y -= out
                v.co.z += 0.0022 * lat              # crisper cupid's-bow lift
            else:                                   # lower lip: fuller
                v.co.y -= 0.0078 * lat
                v.co.z -= 0.0016 * lat
            # mouth SEAM: recess a thin band where the lips meet so the
            # part reads as a dark line (visible mouth, blocker #1)
            if abs(dz_lip) < 0.0045:
                seam = (1.0 - abs(dz_lip) / 0.0045) * lat
                # p4 r5 blocker #1 ("soft undefined mouth"): seam deepened
                # again — the lip part must hold a dark contact line
                v.co.y += 0.0096 * seam
            # r3 (major #6): relax the mouth corners slightly upward-neutral
            if abs(v.co.x - c.x) > half_w * 0.70:
                v.co.z += 0.0018
                v.co.y += 0.0008
            # p5r2 blocker #3: VERMILION BORDER — a raised rim just outside
            # the lip mass so the lip edge reads as a sculpted line.
            if 0.0050 < abs(dz_lip) < 0.0095:
                rim = (1.0 - abs(abs(dz_lip) - 0.00725) / 0.00225) * lat
                # p4 r4 blocker #1: vermilion border +40% — a sculpted edge
                # p4 r5 blocker #1: +25% again — vermilion volume must read
                v.co.y -= 0.0060 * max(0.0, rim)
        print(f"[02_details] lips sculpted (p5r1 volume+seam): {len(lip_idx)} "
              f"verts, c=({c.x:.3f},{c.y:.3f},{c.z:.3f})")
        # landmark props for 03_materials object-space warmth masks (p5r1 #4)
        body["godwyn_lip_c"] = list(c)

        # -- MOUTH WIDTH (p5b fixer r3 blocker #1): the pursed mouth read as
        # a porcelain doll. Widen the whole mouth region laterally ~22% with
        # a smooth 2-axis falloff (moves surrounding skin too — no seam).
        n_w = 0
        for v in me.vertices:
            if v.co.y > c.y + 0.03:
                continue
            dx = v.co.x - c.x
            dz = v.co.z - c.z
            fx = max(0.0, 1.0 - abs(dx) / (half_w * 1.9))
            fz = max(0.0, 1.0 - abs(dz) / 0.030)
            fall = (fx * fz) ** 1.1
            if fall <= 0.0:
                continue
            v.co.x = c.x + dx * (1.0 + 0.10 * fall)
            n_w += 1
        print(f"[02_details] mouth widened +10% ({n_w} verts, p4 r2 "
              "narrower/defined)")

        # -- CHIN: forward mass below the lower lip (jawline relief) ----------
        chin_c = Vector((0.0, c.y, c.z - 0.052))
        for v in me.vertices:
            dx = abs(v.co.x - chin_c.x)
            dz = abs(v.co.z - chin_c.z)
            if dx > half_w * 1.05 or dz > 0.040 or v.co.y > c.y + 0.03:
                continue
            fall = (max(0.0, 1.0 - dx / (half_w * 1.05))
                    * max(0.0, 1.0 - dz / 0.040)) ** 1.2
            v.co.y -= 0.0080 * fall
        print("[02_details] chin mass raised (p5r1 jawline relief)")

        # -- NOSE (r4 blocker #1): bridge + tip + nostril flares ---------------
        if len(eye_data) == 2:
            (c0, r0), (c1, r1) = eye_data
            eye_mid = (c0 + c1) * 0.5
            er = (r0 + r1) * 0.5
            z_bridge = eye_mid.z + er * 0.35        # top, between the brows
            z_tip = c.z + (eye_mid.z - c.z) * 0.34  # tip ~1/3 up lips->eyes
            z_base = c.z + (eye_mid.z - c.z) * 0.15 # nostril base
            nose_hw = half_w * 0.52
            n_moved = 0
            for v in me.vertices:
                if v.co.y > eye_mid.y + 0.02:       # front of the head only
                    continue
                if not (z_base - 0.012 < v.co.z < z_bridge):
                    continue
                ax = abs(v.co.x)
                if ax > nose_hw * 1.7:
                    continue
                if v.co.z >= z_tip:                 # bridge -> tip ramp
                    tz = (z_bridge - v.co.z) / max(z_bridge - z_tip, 1e-4)
                    prof = max(0.0, min(1.0, tz)) ** 1.2
                    wloc = nose_hw * (0.45 + 0.55 * prof)  # narrow bridge
                else:                               # tip -> base falloff
                    tz = ((v.co.z - (z_base - 0.012))
                          / max(z_tip - (z_base - 0.012), 1e-4))
                    prof = max(0.0, min(1.0, tz)) ** 0.7
                    wloc = nose_hw
                lat = max(0.0, 1.0 - ax / max(wloc, 1e-4)) ** 0.9
                if lat <= 0.0:
                    continue
                # p5r1 blocker #1: barely-shaded bridge — more forward mass,
                # plus an EXTRA bridge-specific ridge on the upper half so
                # the profile reads at the Cam_Face distance.
                v.co.y -= 0.0360 * prof * lat       # forward nose mass
                if v.co.z >= z_tip:                 # bridge ridge line
                    v.co.y -= 0.0060 * prof * (lat ** 2.5)
                n_moved += 1
                # nostril flares: side bulges near the base
                if z_base - 0.006 < v.co.z < z_base + 0.016 \
                        and nose_hw * 0.40 < ax < nose_hw * 1.25:
                    v.co.y -= 0.0045
                    v.co.x += math.copysign(0.0022, v.co.x)
                # nostril shadow: slight under-cut right at the base
                if z_base - 0.012 < v.co.z < z_base - 0.002 \
                        and ax < nose_hw * 0.9:
                    v.co.y += 0.0028
            print(f"[02_details] NOSE sculpted: bridge z={z_bridge:.3f} "
                  f"tip z={z_tip:.3f} base z={z_base:.3f} ({n_moved} verts)")
            body["godwyn_nose_tip"] = [0.0, c.y - 0.030, z_tip]

            # -- NASOLABIAL fold (p5r2 blocker #3): a soft crease running from
            # each nostril flare down-out to just past the mouth corner.
            for sgn2 in (1.0, -1.0):
                a_pt = Vector((sgn2 * nose_hw * 1.15, 0.0, z_base + 0.004))
                b_pt = Vector((sgn2 * half_w * 0.95, 0.0, c.z - 0.010))
                seg = b_pt - a_pt
                seg_l2 = max(seg.length_squared, 1e-8)
                for v in me.vertices:
                    if v.co.y > c.y + 0.02:
                        continue
                    rel = Vector((v.co.x - a_pt.x, 0.0, v.co.z - a_pt.z))
                    t2 = max(0.0, min(1.0, rel.dot(seg) / seg_l2))
                    close = a_pt + seg * t2
                    d = math.hypot(v.co.x - close.x, v.co.z - close.z)
                    if d > 0.014:
                        continue
                    fall = (1.0 - d / 0.014) ** 1.5
                    # phase4 fixer r3 blocker #1: crease +32% (was invisible)
                    v.co.y += 0.0058 * fall          # recessed crease
            print("[02_details] nasolabial folds creased (p5r2)")

            # -- PHILTRUM groove (p5r2): sharper central channel nose->lip ----
            for v in me.vertices:
                if v.co.y > c.y + 0.01:
                    continue
                ax2 = abs(v.co.x)
                if ax2 > 0.010 or not (c.z + 0.004 < v.co.z < z_base):
                    continue
                fall = (1.0 - ax2 / 0.010)
                # p4 r5 blocker #1: philtrum channel deepened again
                v.co.y += 0.0070 * fall

        # -- CHEEKS (major #6): fill the gaunt hollows + raise cheekbone volume
        if eye_data:
            for ec, er in eye_data:
                sgn = math.copysign(1.0, ec.x) if abs(ec.x) > 1e-4 else 1.0
                cheek_c = Vector((ec.x + sgn * 0.012, ec.y,
                                  (ec.z + c.z) * 0.5 + 0.006))
                for v in me.vertices:
                    dx = v.co.x - cheek_c.x
                    dz = v.co.z - cheek_c.z
                    if abs(dx) > 0.065 or abs(dz) > 0.075:
                        continue
                    if v.co.y > ec.y + 0.035:      # only the front of the face
                        continue
                    fall = (max(0.0, 1.0 - abs(dx) / 0.065)
                            * max(0.0, 1.0 - abs(dz) / 0.075)) ** 1.3
                    # p5b r3 blocker #1: zygomatic mass +55% + lateral push so
                    # the cheekbone reads as a plane break, not a soft swell
                    # fixer r4 blocker #7 ("doughy undefined features"):
                    # another +27% mass + lateral
                    # phase4 fixer r3 blocker #1: +26% more zygomatic mass +
                    # lateral — the malar plane break must read at Cam_Face
                    v.co.y -= 0.0265 * fall
                    v.co.x += math.copysign(0.0072, v.co.x) * fall
                    v.co.z += 0.0018 * fall        # lifted, youthful mass
                # p5r2 blocker #3: plane break — a soft hollow UNDER the
                # cheekbone so the malar plane visibly turns.
                for v in me.vertices:
                    dx = v.co.x - cheek_c.x
                    dz = v.co.z - (cheek_c.z - 0.055)
                    if abs(dx) > 0.050 or abs(dz) > 0.028:
                        continue
                    if v.co.y > ec.y + 0.035:
                        continue
                    fall = (max(0.0, 1.0 - abs(dx) / 0.050)
                            * max(0.0, 1.0 - abs(dz) / 0.028)) ** 1.4
                    v.co.y += 0.0050 * fall        # sub-malar hollow (r4 +30%)
            # cheek landmark props for 03's warmth masks (p5r1 #4)
            (c0, r0), (c1, r1) = eye_data
            for tag, (ec, er) in (("l", (c0, r0)), ("r", (c1, r1))):
                sgn = math.copysign(1.0, ec.x) if abs(ec.x) > 1e-4 else 1.0
                body[f"godwyn_cheek_{tag}"] = [
                    ec.x + sgn * 0.012, ec.y - 0.02, (ec.z + c.z) * 0.5]
            print("[02_details] cheeks filled + cheekbones raised (r3 #6)")

            # -- MIDFACE NARROWING (phase4 fixer r4 blocker #1: "flat wide
            # facial planes"): pull the maxilla wall BELOW the cheekbones
            # inward so the face tapers eye->mouth instead of reading as one
            # wide flat plane. Zone: between mouth and lower-eye heights,
            # inside the zygomatic prominence (|x| 0.03..0.11), front of the
            # face only. Smooth 3-axis falloff — no seam with the widened
            # cheekbone mass above.
            (c0m, r0m), (c1m, r1m) = eye_data
            eye_zm = (c0m.z + c1m.z) * 0.5
            z_lo_m = c.z + 0.008              # just above the mouth corners
            z_hi_m = eye_zm - 0.028           # below the malar mass
            n_mid = 0
            for v in me.vertices:
                if v.co.y > c.y + 0.03:
                    continue
                if not (z_lo_m < v.co.z < z_hi_m):
                    continue
                ax_m = abs(v.co.x)
                if not (0.030 < ax_m < 0.115):
                    continue
                tz_m = (v.co.z - z_lo_m) / max(z_hi_m - z_lo_m, 1e-4)
                fz_m = math.sin(math.pi * tz_m)
                fx_m = math.sin(math.pi * (ax_m - 0.030) / 0.085)
                fall_m = (fz_m * fx_m) ** 1.2
                if fall_m <= 0.0:
                    continue
                v.co.x *= 1.0 - 0.055 * fall_m     # taper inward
                v.co.y += 0.0022 * fall_m          # slight plane recess
                n_mid += 1
            print(f"[02_details] midface narrowed ({n_mid} verts, p4 r4)")
    else:
        print("[02_details] WARNING: 'lips' group missing — lips skipped",
              file=sys.stderr)

    # -- BROW: real supraorbital ridge (p5b fixer r3 blocker #1: the face
    # still rendered FLAT — relief raised again to 23mm-scale and widened
    # so the ridge reads as bone structure at portrait distance)
    for c, r in eye_data:
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 2.8 or not (r * 0.9 < dz < r * 2.6):
                continue
            if v.co.y > c.y + 0.012:
                continue
            fx = max(0.0, 1.0 - dx / (r * 2.8)) ** 0.8   # wider, gentler
            fz = math.sin(math.pi * (dz - r * 0.9) / (r * 1.7))
            # fixer r4 blocker #7: ridge +17% so the brow bone reads under
            # the new dense brow tufts
            # phase4 fixer r3 blocker #1 ("facial planes flat"): +19% again —
            # the supraorbital shelf must cast a real shadow over the socket
            # phase4 fixer r4 blocker #1: +17% again (0.0320 -> 0.0375) —
            # paired with the deeper socket recess this makes the brow line
            # a real horizontal shadow break at Cam_Face.
            v.co.y -= 0.0375 * fx * max(0.0, fz)
            v.co.z += 0.0018 * fx * max(0.0, fz)
        # p5r2 blocker #3: recess the upper eye socket UNDER the new ridge so
        # the overhang reads (set-back sockets, not a bump on a flat plane)
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 1.9 or not (r * 0.20 < dz < r * 0.85):
                continue
            if v.co.y > c.y + 0.008:
                continue
            fx = max(0.0, 1.0 - dx / (r * 1.9))
            fz = math.sin(math.pi * (dz - r * 0.20) / (r * 0.65))
            # phase4 fixer r2 blocker #1: socket recess DEEPENED 0.0042 ->
            # 0.0068 — the eyes must sit back under the brow bone, not on
            # the front plane of a doll mask.
            # phase4 fixer r4 blocker #1 ("still a mannequin"): 0.0068 ->
            # 0.0094 — the orbital socket must hold a real shadow pocket.
            v.co.y += 0.0094 * fx * max(0.0, fz)
        # phase4 fixer r2 blocker #1: HOODED LID SHELF — a soft fold of
        # skin draped forward-and-down over the upper third of the
        # aperture so the upper lid overhangs the ball (noble, heavy-lidded
        # FromSoft gaze, not a wide-open stare).
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 1.5 or not (r * 0.12 < dz < r * 0.55):
                continue
            if v.co.y > c.y + 0.006:
                continue
            fx = max(0.0, 1.0 - dx / (r * 1.5))
            fz = math.sin(math.pi * (dz - r * 0.12) / (r * 0.43))
            hood = fx * max(0.0, fz)
            v.co.y -= 0.0032 * hood      # drape forward over the ball
            v.co.z -= 0.0022 * hood      # and pull down: hooded aperture
        # fixer r5 blocker #7 ("porcelain mannequin — no lid structure"):
        # DEFINED UPPER-LID CREASE — a crisp narrow fold line above the
        # aperture so the lid reads structurally, not as a smooth doll bulge
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 1.6 or not (r * 0.36 < dz < r * 0.74):
                continue
            if v.co.y > c.y + 0.008:
                continue
            fx = max(0.0, 1.0 - dx / (r * 1.6))
            fz = 1.0 - abs(dz - r * 0.55) / (r * 0.19)
            if fz <= 0.0:
                continue
            # p4 r5 blocker #1 ("flat lids"): crease fold deepened 0.0034 ->
            # 0.0050 — a real supratarsal fold shadow above the aperture
            v.co.y += 0.0050 * fx * (fz ** 1.4)
        # phase4 fixer r3 blocker #1 ("no lower-lid definition"): a subtle
        # LOWER-LID SHELF — a narrow raised band just under the aperture
        # (the lid margin catching light) with a soft recess below it where
        # the lid meets the cheek (tear-trough plane change).
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 1.5 or v.co.y > c.y + 0.006:
                continue
            fx = max(0.0, 1.0 - dx / (r * 1.5))
            if -r * 0.55 < dz < -r * 0.18:            # lid-margin shelf
                fz = 1.0 - abs(dz + r * 0.365) / (r * 0.185)
                v.co.y -= 0.0022 * fx * max(0.0, fz) ** 1.3
            elif -r * 1.05 < dz < -r * 0.55:          # tear-trough recess
                fz = 1.0 - abs(dz + r * 0.80) / (r * 0.25)
                v.co.y += 0.0026 * fx * max(0.0, fz) ** 1.3
    # phase4 fixer r2 blocker #1 ("enormous smooth forehead"): the frontal
    # bone bulged forward above the brow. Sweep the forehead BACK with a
    # ramp from the brow ridge to the hairline so the profile slopes like
    # a real skull instead of ballooning.
    if eye_data:
        ez = sum(c.z for c, _ in eye_data) / len(eye_data)
        er_m = sum(r for _, r in eye_data) / len(eye_data)
        ey = min(c.y for c, _ in eye_data)
        z_fh0 = ez + er_m * 2.4          # just above the brow ridge
        z_fh1 = ez + er_m * 5.2          # hairline-ish
        n_fh = 0
        for v in me.vertices:
            if not (z_fh0 < v.co.z < z_fh1) or v.co.y > ey + 0.03:
                continue
            t_fh = (v.co.z - z_fh0) / (z_fh1 - z_fh0)
            fall = math.sin(math.pi * min(t_fh, 1.0)) ** 1.2
            lat = max(0.0, 1.0 - abs(v.co.x) / 0.14)
            v.co.y += 0.0085 * fall * (0.35 + 0.65 * lat)
            n_fh += 1
        print(f"[02_details] forehead swept back ({n_fh} verts, p4 r2)")
        # eye landmarks for 03's lid-darkening masks (p4 r2 blocker #1)
        for tag2, (ec2, er2) in (("l", eye_data[0]),
                                 ("r", eye_data[-1])):
            body[f"godwyn_eye_{tag2}"] = [ec2.x, ec2.y, ec2.z]
    print("[02_details] brow ridge raised + sockets recessed + hooded lid "
          "shelf + lid crease (p4 r2 structural pass)")

    # -- JAW (p5r2 blocker #3): squarer gonial corners from the ear landmarks -
    for tag, sgn in (("l", 1.0), ("r", -1.0)):
        ec = body.get(f"godwyn_ear_{tag}")
        if ec is None:
            continue
        jc = Vector((ec[0] * 0.94, ec[1] - 0.015, ec[2] - 0.062))
        for v in me.vertices:
            d = (v.co - jc).length
            if d > 0.056 or math.copysign(1.0, v.co.x) != sgn:
                continue
            fall = (1.0 - d / 0.056) ** 1.3
            # p5b r3 blocker #1: squarer masculine jaw — widen +65%
            # fixer r4 blocker #7: +20% more — the jawline must plane-break
            # phase4 fixer r3 blocker #1: +20% more — jaw plane break
            v.co.x += sgn * 0.0180 * fall     # widen the gonial angle
            v.co.z -= 0.0052 * fall           # drop the corner (square, not V)
    # -- CHIN SQUARE (p5b r3 blocker #1): widen the chin tip laterally and
    # flatten its point so the chin reads masculine, not a doll's V.
    lm = body.get("godwyn_lip_c")
    if lm is not None:
        cc = Vector((0.0, lm[1], lm[2] - 0.055))
        for v in me.vertices:
            dx = abs(v.co.x)
            dz = abs(v.co.z - cc.z)
            if dx > 0.045 or dz > 0.035 or v.co.y > cc.y + 0.025:
                continue
            fall = (max(0.0, 1.0 - dx / 0.045)
                    * max(0.0, 1.0 - dz / 0.035)) ** 1.2
            if dx > 0.008:
                v.co.x += math.copysign(0.0060, v.co.x) * fall  # widen
            else:
                v.co.y += 0.0022 * fall       # flatten the central point
    print("[02_details] jaw squared + chin widened/flattened (p5b r3)")

    # -- EARS: flatten the triangular fins against the skull -------------------
    ear_idx = _group_verts(body, "ears")
    if ear_idx:
        ear_idx = {i for i in ear_idx if i < len(me.vertices)}
        for sgn in (1.0, -1.0):
            side = [i for i in ear_idx
                    if math.copysign(1.0, me.vertices[i].co.x) == sgn]
            if not side:
                continue
            x_base = min(abs(me.vertices[i].co.x) for i in side)
            zc = sum(me.vertices[i].co.z for i in side) / len(side)
            for i in side:
                v = me.vertices[i]
                prot = abs(v.co.x) - x_base       # protrusion beyond skull
                if prot <= 0.0:
                    continue
                v.co.x = sgn * (x_base + prot * 0.45)   # flatten to the head
                v.co.y += prot * 0.30                    # sweep gently back
                v.co.z += (zc - v.co.z) * 0.22 * min(1.0, prot / 0.02)  # de-point
            ec = sum((me.vertices[i].co.copy() for i in side),
                     Vector()) / len(side)
            body[f"godwyn_ear_{'l' if sgn > 0 else 'r'}"] = list(ec)
        print(f"[02_details] ears flattened: {len(ear_idx)} verts")
    else:
        print("[02_details] WARNING: 'ears' group missing — ears skipped",
              file=sys.stderr)
    me.update()


def build_eyes(eye_data, mat_sclera, mat_iris, mat_pupil, mat_skin):
    """
    Godwyn_Eyes (r3 blocker #1): one solid DENSE UV-sphere eyeball per eye
    (48x36 — the old 32x24 sphere gave the pupil band only ~4 quads, which
    rendered as a tiny SQUARE dot), plus a protruding cornea bulge, plus
    REAL eyelid shells (upper + lower skin-material bands hugging the ball)
    so the sclera is partially covered and the eye reads lidded, not staring.

    Face-level material bands: pupil (<12 deg from forward -Y), iris
    (<30 deg), sclera (rest). Slot order 0/1/2/3 = sclera/iris/pupil/skin —
    03_materials refills these slots by the same order.
    """
    fwd = Vector((0.0, -1.0, 0.0))
    parts = []
    centres = []
    for k, (c, r) in enumerate(eye_data):
        R = r * 1.10                       # inflate: lids must overlap the ball
        # ADVANCE the ball: the helper centroid sits deep in the skull — at
        # +0.003 the sphere was ~15mm recessed behind the lid aperture and
        # the sockets rendered as shadowed black slits.
        # p5b fixer r3 blocker #1: -0.011 pushed the ball so far forward the
        # lids no longer overlapped it (white frame around the iris). Sunk
        # back 3.5mm; the tighter lid aperture above now covers the top.
        centre = c + Vector((0.0, -0.0075, 0.0))
        centres.append(centre.copy())
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=36, radius=R)
        me = bpy.data.meshes.new(f"_eye{k}")
        bm.to_mesh(me)
        bm.free()
        for v in me.vertices:
            d = v.co.normalized()
            ang = math.degrees(d.angle(fwd))
            # phase4 fixer r3 blocker #1 ("small glassy eyes, flat iris"):
            # iris band widened 30 -> 33 deg (~10% larger iris) and the
            # CORNEAL BULGE strengthened (0.09 -> 0.13R) so the lens reads
            # as a curved refractive form with a real broken highlight.
            # p4 r5 blocker #1 ("small beady eyes"): iris band 33 -> 36 deg
            if ang < 36.0:                 # cornea bulge, smooth falloff
                v.co += d * (R * 0.13
                             * math.cos(math.radians(ang * 90.0 / 36.0)))
            v.co += centre
        me.update()
        ob = bpy.data.objects.new(f"_eye{k}", me)
        link_obj(ob)
        for m in (mat_sclera, mat_iris, mat_pupil):
            me.materials.append(m)
        n_band = [0, 0, 0]
        for poly in me.polygons:
            # centre from live vertex coords — poly.center can be stale here
            pc = sum((me.vertices[vi].co.copy() for vi in poly.vertices),
                     Vector()) / len(poly.vertices)
            d = pc - centre
            ang = math.degrees(d.normalized().angle(fwd))
            # p4 r3: iris band 30 -> 33 deg, pupil 12 -> 13 (larger iris)
            # p4 r5 blocker #1: iris 33 -> 36 deg, pupil 13 -> 14 — larger
            # iris disc + more visible sclera via the opened aperture below
            poly.material_index = 2 if ang < 14.0 else (1 if ang < 36.0 else 0)
            n_band[poly.material_index] += 1
        assert n_band[1] >= 8 and n_band[2] >= 8, \
            f"eye{k} banding too coarse (square-pupil risk): {n_band}"
        shade_smooth(ob)
        parts.append(ob)

        # -- EYELIDS: curved skin shells over the top/bottom of the ball ------
        # Upper lid covers the top ~40%% of the visible ball; lower lid a thin
        # band. Same falloff family as the socket-opening pass so they meet
        # the surrounding skin.
        # r4 major #2: aperture opened symmetrically — the r3 lid shells
        # covered the ball down to z=0.10 and up to -0.26, leaving a narrow
        # slit. Iris+pupil must read at full-body distance.
        # p5b fixer r3 blocker #1: upper lid extended DOWN (0.24 -> 0.10) so
        # it visibly overlaps the top of the iris — no doll-white frame.
        # fixer r1 major #6: ALMOND aperture — the straight horizontal lid
        # edges made the eye read as a boxy rectangular slot. The upper
        # lid's lower edge now curves DOWN toward the corners and the lower
        # lid's upper edge curves UP, so the lids meet at the canthi and the
        # opening is widest at the centre (a real eye shape).
        # RE-OUTFIT fixer r3 blocker #1 ("dark eyelid-geometry artifacts"):
        # the r2 lid shells were narrow floating bands at R*1.16 — their FREE
        # RIMS (top of the upper lid, bottom of the lower lid) hovered 1.6mm
        # proud of the ball and rendered as dark slit shadows ringing both
        # eyes. Fix: (a) each lid now extends all the way to its pole, so the
        # only free edge left is the APERTURE edge; (b) the shell radius is
        # tighter (R*1.10) and the aperture edge is SEATED — verts within a
        # margin of the aperture curve are pulled radially down to R*1.015 so
        # the lid lip touches the ball (no gap, no shadow slit); (c) side
        # extent trimmed (y < 0.18R) so the shell never juts past the socket.
        # p4 r5 blocker #1 ("beady dark eyes, little visible sclera"): the
        # aperture OPENS — upper lid edge raised 0.10 -> 0.20, lower lid
        # edge dropped -0.30 -> -0.40, so real sclera shows either side of
        # the (now larger) iris and the eye reads open + lidded, not a slit.
        for lname, z_lo, z_hi, cu, cd, seat_hi in (
                (f"_lidU{k}", 0.20, 1.01, 0.46, 0.0, False),
                (f"_lidD{k}", -1.01, -0.40, 0.0, 0.40, True)):
            Rl = R * 1.10                  # clear the cornea bulge, hug the ball
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=24,
                                      radius=Rl)
            doomed = []
            for v in bm.verts:
                xn = v.co.x / Rl
                zlo_e = z_lo - cu * xn * xn      # upper lid dips at corners
                zhi_e = z_hi + cd * xn * xn      # lower lid rises at corners
                if not (zlo_e < v.co.z / Rl < zhi_e and v.co.y < 0.18 * Rl):
                    doomed.append(v)
            bmesh.ops.delete(bm, geom=doomed, context="VERTS")
            # seat the aperture rim onto the eyeball (kill the shadow slit)
            for v in bm.verts:
                xn = v.co.x / Rl
                zn = v.co.z / Rl
                ap = (z_hi + cd * xn * xn) if seat_hi else (z_lo - cu * xn * xn)
                d_ap = abs(zn - ap)
                if d_ap < 0.14:                    # rim band near the aperture
                    f = 1.0 - d_ap / 0.14          # 1 at the edge, 0 inside
                    r_target = R * (1.015 + (Rl / R - 1.015) * (1.0 - f))
                    v.co = v.co.normalized() * r_target
            lme = bpy.data.meshes.new(lname)
            bm.to_mesh(lme)
            bm.free()
            if len(lme.vertices) == 0:
                print(f"[02_details] WARNING: {lname} empty — skipped",
                      file=sys.stderr)
                continue
            for v in lme.vertices:
                v.co += centre + Vector((0.0, 0.001, 0.0))  # tuck back a hair
            lme.update()
            lid = bpy.data.objects.new(lname, lme)
            link_obj(lid)
            lme.materials.append(mat_skin)
            sol = lid.modifiers.new("Solid", "SOLIDIFY")
            sol.thickness = 0.0035
            sol.offset = -1.0
            apply_mods(lid)
            shade_smooth(lid)
            parts.append(lid)

    assert len(parts) >= 4, f"expected eyeballs+lids, built {len(parts)}"
    eyes = join(parts, "Godwyn_Eyes")
    assert len(eyes.data.materials) >= 4, \
        f"Godwyn_Eyes slot contract broken: {len(eyes.data.materials)} slots"

    # -- "EyeUV" radial map (p5r1 blocker #1): U = angle-from-forward / 30deg
    # (0 at the pupil centre, 1.0 at the iris rim). 03_materials rebuilds
    # Mat_EyeIris as a radial gradient over this U — a perfectly ROUND pupil
    # + limbal ring, killing the square face-band pupil artifact. Lid verts
    # land at U >> 1 (skin material — unaffected).
    uvl = eyes.data.uv_layers.new(name="EyeUV")
    me_e = eyes.data
    for loop in me_e.loops:
        co = me_e.vertices[loop.vertex_index].co
        centre = min(centres, key=lambda cc: (co - cc).length)
        d = co - centre
        if d.length > 1e-6:
            # p4 r5: normalized to the widened 36-deg iris band
            u = math.degrees(d.normalized().angle(fwd)) / 36.0
        else:
            u = 0.0
        uvl.data[loop.index].uv = (u, 0.5)
    print(f"[02_details] Godwyn_Eyes built: {len(eye_data)} dense eyeballs "
          "(round iris/pupil bands) + upper/lower eyelid shells")
    return eyes


# ---------------------------------------------------------------------------
# RIGHT HAND — curl the fingers into a loose master grip (major #7)
# ---------------------------------------------------------------------------

def curl_fingers(body, side="R", max_deg=78.0):
    """
    Curl one hand's finger vertices around a grip axis. Right hand: a firm
    master grip for the sword. Left hand: a gentle relaxed half-curl so the
    open bind-pose splay doesn't read as a mannequin.

    Palm side is detected from the 'fingernails' vertex group (nails face
    the BACK of the hand — palm = opposite).

    Returns (grip_point, grip_axis, palm_normal) in bind space; the sword is
    placed on this axis and 04 re-derives the posed transform from it.
    """
    me = body.data
    sgn = 1.0 if side == "R" else -1.0
    wrist = Vector((sgn * WRIST_R.x, WRIST_R.y, WRIST_R.z))
    hand_c = Vector((sgn * HAND_R.x, HAND_R.y, HAND_R.z))
    f_dir = (hand_c - wrist).normalized()

    hand = [v for v in me.vertices
            if 0.02 < (v.co - wrist).dot(f_dir) < 0.40
            and (v.co - wrist).length < 0.50
            and sgn * v.co.x > 0.80 + _HAND_SH.x]
    if not hand:
        print(f"[02_details] WARNING: no {side}-hand verts — curl skipped",
              file=sys.stderr)
        return hand_c.copy(), Vector((0.3, -0.2, -0.93)), Vector((0, -1, 0))
    WRIST_S, HAND_S = wrist, hand_c   # local aliases used below

    smax = max((v.co - WRIST_S).dot(f_dir) for v in hand)

    # palm normal from fingernail verts (they face the back of the hand)
    nail_idx = _group_verts(body, "fingernails")
    nail_n = Vector()
    for v in hand:
        if v.index in nail_idx:
            nail_n += v.normal
    if nail_n.length > 1e-3:
        back_n = nail_n.normalized()
        palm_n = (-back_n - f_dir * (-back_n).dot(f_dir)).normalized()
    else:
        palm_n = Vector((0, -1, 0))
        print(f"[02_details] WARNING: no nail verts on {side} hand — "
              "palm normal fallback (0,-1,0)", file=sys.stderr)

    # grip axis = knuckle line
    axis = f_dir.cross(palm_n).normalized()
    # sign: curling must move fingertips toward the palm side
    from mathutils import Quaternion
    test = Quaternion(axis, math.radians(8.0)) @ f_dir
    if (test - f_dir).dot(palm_n) < 0.0:
        axis = -axis

    s0 = smax * 0.42                       # knuckle line
    p0 = WRIST_S + f_dir * s0
    for v in hand:
        s = (v.co - WRIST_S).dot(f_dir)
        if s <= s0:
            continue
        t = min(1.0, (s - s0) / (smax - s0))
        ang = math.radians(max_deg) * (t ** 0.85)
        q = Quaternion(axis, ang)
        rel = v.co - p0
        along = rel.dot(axis)
        v.co = p0 + axis * along + q @ (rel - axis * along)
    me.update()

    grip_point = p0 + f_dir * (0.30 * (smax - s0)) + palm_n * 0.038
    # knuckle landmark for 03's warmth masks (p5r1 #4): back of the knuckles
    knuckle = p0 - palm_n * 0.030
    body[f"godwyn_knuckle_{side.lower()}"] = list(knuckle)
    print(f"[02_details] {side} fingers curled {max_deg:.0f}deg: "
          f"knuckle s0={s0:.3f} "
          f"palm_n=({palm_n.x:.2f},{palm_n.y:.2f},{palm_n.z:.2f}) "
          f"grip=({grip_point.x:.3f},{grip_point.y:.3f},{grip_point.z:.3f})")
    return grip_point, axis, palm_n


# ---------------------------------------------------------------------------
# TORSO — macro muscle definition sculpt (p5 fixer r1, major #5)
# ---------------------------------------------------------------------------

def sculpt_torso(body):
    """
    Landmark-based macro definition on the EXPOSED chest/arms: clavicle
    ridges, pectoral mass + sternum groove, rectus abdominis blocking,
    biceps relief. Macro shapes live in the MESH so they survive
    normal-map baking and armature deformation. Runs BEFORE
    init_surface_sampler so the armor filigree conforms to the new chest.
    """
    me = body.data
    n_cl = n_pec = n_ab = n_bi = 0

    for v in me.vertices:
        if v.co.y > 0.18:                      # front hemisphere only
            continue
        x, z = v.co.x, v.co.z
        ax = abs(x)

        # -- CLAVICLE ridge: sternal notch -> shoulder, slight sag ----------
        if ax < 0.36 and 2.46 < z < 2.62:
            z_cl = 2.555 - 0.045 * (ax / 0.36)
            dz = z - z_cl
            if abs(dz) < 0.030:
                fall = math.cos(math.pi * dz / 0.060) ** 2
                ramp = min(1.0, ax / 0.05)     # fade at the sternal notch
                v.co.y -= 0.0065 * fall * (0.35 + 0.65 * ramp)
                n_cl += 1
            elif -0.062 < dz < -0.030:         # infraclavicular hollow
                v.co.y += 0.0030
                n_cl += 1

        # -- PECS: forward mass + sternum groove + under-pec crease ---------
        # p5b fixer r3 blocker #3: chest still read FLAT at full-body
        # distance — pec plate mass +70%, groove/crease deepened to match.
        if 0.03 < ax < 0.32 and 2.16 < z < 2.50:
            fx = max(0.0, 1.0 - abs(ax - 0.150) / 0.135)
            fz = max(0.0, 1.0 - abs(z - 2.33) / 0.165)
            fall = (fx * fz) ** 1.2
            v.co.y -= 0.0180 * fall
            n_pec += 1
        if ax < 0.024 and 2.18 < z < 2.50:     # sternum groove
            fall = (1.0 - ax / 0.024) * max(0.0, 1.0 - abs(z - 2.34) / 0.16)
            v.co.y += 0.0075 * fall
            n_pec += 1
        if 0.05 < ax < 0.24 and 2.150 < z < 2.200:  # under-pec crease
            v.co.y += 0.0048 * (1.0 - abs(z - 2.175) / 0.025)
            n_pec += 1

        # -- RECTUS blocking above the robe waistline ------------------------
        # p5b r3 blocker #3: visible ab plane (relief +70%)
        if ax < 0.135 and 1.975 < z < 2.16:
            if ax < 0.016:                     # linea alba groove
                v.co.y += 0.0052 * (1.0 - ax / 0.016)
            else:
                seg = 1.0
                for z_seg in (2.045, 2.115):   # horizontal tendon creases
                    seg = min(seg, abs(z - z_seg) / 0.010)
                block = max(0.0, 1.0 - (ax - 0.016) / 0.119)
                v.co.y -= 0.0085 * block * min(1.0, seg)
            n_ab += 1

    # -- BICEPS: radial mass on each exposed upper arm ------------------------
    for sgn in (1.0, -1.0):
        a0 = Vector((sgn * 0.48, 0.10, 2.48))
        a1 = Vector((sgn * ELBOW_R.x, ELBOW_R.y, ELBOW_R.z))
        axis = (a1 - a0)
        alen = axis.length
        axis_n = axis.normalized()
        for v in me.vertices:
            rel = v.co - a0
            t = rel.dot(axis_n) / alen
            if not (0.10 < t < 0.90):
                continue
            radial = rel - axis_n * (rel.dot(axis_n))
            d = radial.length
            if d > 0.105 or d < 1e-5:
                continue
            prof = math.sin(math.pi * (t - 0.10) / 0.80) ** 1.5
            v.co += radial.normalized() * (0.0075 * prof)
            n_bi += 1

    # -- DELTOID caps (p5b fixer r3 blocker #3): radial mass over each
    # shoulder ball so the arm visibly attaches through muscle.
    n_dl = n_tr = n_fa = 0
    for sgn in (1.0, -1.0):
        dc = Vector((sgn * 0.485, 0.10, 2.53))
        for v in me.vertices:
            rel = v.co - dc
            d = rel.length
            if d > 0.145 or sgn * v.co.x < 0.34:
                continue
            fall = math.cos(0.5 * math.pi * d / 0.145) ** 1.4
            v.co += rel.normalized() * (0.0110 * fall)
            n_dl += 1
        # -- TRAPEZIUS slope: neck-to-shoulder mass on the upper back --------
        for v in me.vertices:
            if v.co.y < 0.04:                  # back half only
                continue
            ax2 = sgn * v.co.x
            if not (0.05 < ax2 < 0.34) or not (2.52 < v.co.z < 2.75):
                continue
            fx = math.sin(math.pi * (ax2 - 0.05) / 0.29)
            fz = max(0.0, 1.0 - abs(v.co.z - 2.62) / 0.13)
            v.co.z += 0.0075 * fx * fz         # slope up toward the neck
            v.co.y += 0.0055 * fx * fz         # back mass
            n_tr += 1
        # -- FOREARM mass (visible at the wrist, below the bracer) -----------
        f0 = Vector((sgn * ELBOW_R.x, ELBOW_R.y, ELBOW_R.z))
        f1 = Vector((sgn * WRIST_R.x, WRIST_R.y, WRIST_R.z))
        faxis = f1 - f0
        flen = faxis.length
        faxis_n = faxis.normalized()
        for v in me.vertices:
            rel = v.co - f0
            t = rel.dot(faxis_n) / flen
            if not (0.05 < t < 0.85):
                continue
            radial = rel - faxis_n * rel.dot(faxis_n)
            d = radial.length
            if d > 0.085 or d < 1e-5:
                continue
            prof = math.sin(math.pi * (t - 0.05) / 0.80) ** 1.2
            v.co += radial.normalized() * (0.0050 * prof)
            n_fa += 1

    me.update()
    print(f"[02_details] torso sculpted (p5b r3 #3): clavicle {n_cl}, "
          f"pec/sternum {n_pec}, rectus {n_ab}, biceps {n_bi}, "
          f"deltoid {n_dl}, traps {n_tr}, forearm {n_fa} vert hits")


# ---------------------------------------------------------------------------
# ARMOR
# ---------------------------------------------------------------------------

def _limb_radial(body, z, sgn, n=40, win=0.05, z_max=1.60, y_range=None):
    """Per-angle max radial extent of ONE leg's cross-section near height z.
    Like body_radial but centred on the leg itself (verts with sgn*x>0.03).
    y_range=(y0,y1) excludes the foot's forward instep/toe verts when
    sampling near the ankle (they'd balloon the ring over the foot).
    Returns (cx, cy, [r_0..r_n-1]), angle a from +y (back)."""
    sel = [v.co for v in body.data.vertices
           if abs(v.co.z - z) < win and sgn * v.co.x > 0.03 and v.co.z < z_max
           and (y_range is None or y_range[0] < v.co.y < y_range[1])]
    assert sel, f"_limb_radial: no verts at z={z} sgn={sgn}"
    cx = 0.5 * (min(c.x for c in sel) + max(c.x for c in sel))
    cy = 0.5 * (min(c.y for c in sel) + max(c.y for c in sel))
    radii = [0.0] * n
    step = 2 * math.pi / n
    for c in sel:
        a = math.atan2(c.x - cx, c.y - cy) % (2 * math.pi)
        r = math.hypot(c.x - cx, c.y - cy)
        k = int(a / step) % n
        for kk in (k - 1, k, k + 1):
            kk %= n
            if r > radii[kk]:
                radii[kk] = r
    for _ in range(n):
        holes = [i for i in range(n) if radii[i] == 0.0]
        if not holes:
            break
        for i in holes:
            radii[i] = max(radii[(i - 1) % n], radii[(i + 1) % n])
    for _ in range(3):
        radii = [max(radii[i],
                     0.25 * radii[(i - 1) % n] + 0.5 * radii[i]
                     + 0.25 * radii[(i + 1) % n]) for i in range(n)]
    return cx, cy, radii


def build_greave(body, mat_gold, sgn, tag):
    """RE-OUTFIT fixer r2 blocker #1: the r1 greave lofted the PER-ANGLE
    anatomical envelope of the leg, so the calf-muscle silhouette printed
    straight into the plate (it rendered as a gold-painted leg). This
    version is a RIGID FORGED FORM that overrides the anatomy:
      - a straight axis from knee to ankle (no anatomical center drift),
      - per-station radius = near-straight taper fitted OVER the leg's max
        radial extent (circular sections — never traced anatomy), lightly
        smoothed so it reads as one forged swell, not muscle,
      - a sharp triangular frontal shin crest,
      - rolled rims top + bottom and an engraved mid-band.
    main() shrinks the body's calf verts underneath — zero print-through."""
    parts = []
    NGR = 40
    stations = (1.100, 1.020, 0.900, 0.760, 0.620, 0.480, 0.340, 0.230, 0.165)
    _, cy_ref, _ = _limb_radial(body, 0.48, sgn, NGR, win=0.045)
    # 1. anatomical envelope: max radius + center per station
    raw = []
    for z in stations:
        yr = (cy_ref - 0.105, cy_ref + 0.105) if z < 0.36 else None
        cx, cy, rad = _limb_radial(body, z, sgn, NGR, win=0.045, y_range=yr)
        raw.append((z, cx, cy, max(rad)))
    # 2. rigid straight axis knee -> ankle
    top = Vector((raw[0][1], raw[0][2], raw[0][0]))
    bot = Vector((raw[-1][1], raw[-1][2], raw[-1][0]))
    z_span = raw[0][0] - raw[-1][0]
    # 3. required clearance radius per station about the STRAIGHT axis
    need = []
    for (z, cx, cy, rmax) in raw:
        t = (raw[0][0] - z) / z_span
        c = top.lerp(bot, t)
        need.append(rmax + math.hypot(cx - c.x, cy - c.y) + 0.011)
    # 4. profile: fixer r4 blocker #11 ("greaves still read as ANATOMICAL
    # gold calves") — the old max(taper, need)+smooth still LIFTED the
    # profile over the calf bulge, printing anatomy into the plate. Now a
    # TRUE STRAIGHT-TAPER cone: R_bot is the ankle clearance and R_top is
    # raised until the straight line clears EVERY station (the calf sits
    # fully inside a rigid forged shell — zero muscle silhouette).
    r_bot = need[-1]
    r_top = need[0]
    for i, (z, _, _, _) in enumerate(raw[:-1]):
        t = (raw[0][0] - z) / z_span
        if t < 0.999:
            r_top = max(r_top, (need[i] - r_bot * t) / (1.0 - t))
    # phase4 fixer r3 major #4 ("greaves read as ribbed stovepipe
    # cylinders"): a GENTLE FORGED ENTASIS on the straight taper — a +3%
    # swell peaking a third of the way down, clearly a smithed form (NOT
    # the anatomical calf print of r1: it is symmetric and axis-centred),
    # so the shin plate reads as forged steel rather than a pipe.
    prof = []
    for (z, _, _, _) in raw:
        t = (raw[0][0] - z) / z_span
        base_r = r_top + (r_bot - r_top) * t
        prof.append(base_r * (1.0 + 0.030 * math.sin(math.pi
                                                     * min(t / 0.66, 1.0))))
    rings = []
    ring_geo = []                      # (center, R, z) for the trims
    for i, (z, _, _, _) in enumerate(raw):
        t = (raw[0][0] - z) / z_span
        c = top.lerp(bot, t)
        Rz = prof[i]
        ring = []
        for j in range(NGR):
            a = 2 * math.pi * j / NGR
            # sharp triangular frontal crest (front of the body is -y)
            da = (a - math.pi + math.pi) % (2 * math.pi) - math.pi
            crest = 0.017 * max(0.0, 1.0 - abs(da) / 0.60) * (1.0 - 0.40 * t)
            r = Rz + crest
            ring.append(Vector((c.x + r * math.sin(a), c.y + r * math.cos(a),
                                z)))
        rings.append(ring)
        ring_geo.append((c, Rz, z))
    parts.append(loft_band(f"_greave{tag}", rings, mat_gold,
                           thickness=0.010, bevel=0.0032))
    # rolled rims top + bottom (circular — match the rigid sections)
    for c, Rz, z in (ring_geo[0], ring_geo[-1]):
        pts = []
        for j in range(NGR):
            a = 2 * math.pi * j / NGR
            r = Rz + 0.003
            pts.append((Vector((c.x + r * math.sin(a),
                                c.y + r * math.cos(a), z)), 1.0))
        parts.append(curve_obj(f"_greave{tag}_rim{z:.2f}", [pts], 0.0062,
                               mat_gold, cyclic=True))
    # phase4 fixer r3 major #4: the THREE horizontal rings (bi 1/4/7) were
    # the "uniform segment rings" stovepipe read — only ONE chased mid-shin
    # band remains as a goldsmith accent; the rolled rims + shin crest +
    # entasis carry the form now.
    for bi in (4,):
        c, Rz, z = ring_geo[bi]
        band = [(Vector((c.x + (Rz - 0.002) * math.sin(2 * math.pi * j / NGR),
                         c.y + (Rz - 0.002) * math.cos(2 * math.pi * j / NGR),
                         z)), 1.0) for j in range(NGR)]
        parts.append(curve_obj(f"_greave{tag}_band{bi}", [band],
                               0.0044, mat_gold, cyclic=True))
    # crest border ribs: two thin ridges flanking the frontal shin crest so
    # the crest reads as an ornamented panel, not a plain bulge
    for side in (-1.0, 1.0):
        rib = []
        for i, (c, Rz, z) in enumerate(ring_geo):
            t = i / (len(ring_geo) - 1.0)
            a = math.pi + side * 0.72          # just outside the crest wedge
            r = Rz + 0.0035 * (1.0 - 0.40 * t)
            rib.append((Vector((c.x + r * math.sin(a), c.y + r * math.cos(a),
                                z)), 1.0 - 0.25 * t))
        parts.append(curve_obj(f"_greave{tag}_crestrib{side:+.0f}", [rib],
                               0.0034, mat_gold))
    # SIDE HINGE detail (fixer r4 blocker #11): two small hinge barrels +
    # pin studs on the OUTER face — a real two-piece greave closure read.
    a_out = math.copysign(math.pi / 2.0, sgn)      # outer side of this leg
    for bi in (2, 6):
        c, Rz, z = ring_geo[bi]
        hc = Vector((c.x + (Rz + 0.0035) * math.sin(a_out),
                     c.y + (Rz + 0.0035) * math.cos(a_out), z))
        barrel = cylinder_between(f"_greave{tag}_hinge{bi}",
                                  hc + Vector((0, 0, 0.030)),
                                  hc - Vector((0, 0, 0.030)),
                                  0.0075, 0.0075, mat_gold, seg=12)
        parts.append(barrel)
        for dz in (0.034, -0.034):
            parts.append(uv_sphere(f"_greave{tag}_pin{bi}{dz:+.2f}",
                                   hc + Vector((0, 0, dz)),
                                   (0.0085, 0.0085, 0.006), mat_gold,
                                   seg=12, rings=8))
    return parts


def build_poleyn(body, mat_gold, sgn, tag):
    """RE-OUTFIT fixer r3 blocker #2 ("knees are bare round gold gaps —
    no poleyn"): a real articulated knee cop bridging cuisse -> greave:
      - a domed COP plate over the front of the knee (fitted to the sampled
        knee cross-section, so it actually seats on the leg),
      - a SIDE WING on each flank (classic fan-plate silhouette),
      - one upper + one lower LAME arc so the articulation reads,
      - a rim rib around the cop edge.
    All centred from _limb_radial at the knee — never hand-placed."""
    parts = []
    # knee centre + max radius from the real leg (z ~ knee gap 0.96-1.10)
    cx, cy, rad = _limb_radial(body, 1.03, sgn, 32, win=0.055, z_max=1.60)
    rmax = max(rad)
    z_knee = 1.035
    # front direction is -y; the cop sits proud of the front of the knee
    cop_c = Vector((cx, cy - rmax * 0.55, z_knee))
    # domed cop: forward-facing partial ellipsoid (local +z -> -y world)
    parts.append(sphere_shell(
        f"_poleyn{tag}", cop_c,
        (rmax * 1.00, rmax * 1.30, rmax * 0.85),   # x wide, z tall (pre-rot)
        (math.radians(90), 0, 0), mat_gold, keep_z=0.28, thickness=0.010))
    # rim rib around the cop edge (fused, slightly sunk)
    R = Euler((math.radians(90), 0, 0), "XYZ").to_matrix()
    rim_lat = 0.30
    rim_rad = math.sqrt(max(1.0 - rim_lat * rim_lat, 0.0)) * 0.96
    rim = []
    for j in range(25):
        a = 2 * math.pi * j / 24.0
        local = Vector((rmax * 1.00 * rim_rad * math.cos(a),
                        rmax * 1.30 * rim_rad * math.sin(a),
                        rmax * 0.85 * rim_lat))
        rim.append((cop_c + R @ local, 1.0))
    parts.append(curve_obj(f"_poleyn{tag}_rim", [rim], 0.0058, mat_gold,
                           cyclic=True))
    # side wings (phase4 fixer r3 major #4: "add knee poleyns with FAN
    # FLANGES"): each flank now carries a 3-plate fan — the main wing plus
    # two smaller flange plates fanned above/behind it, each rotated a step
    # further back, the classic gothic poleyn fan silhouette.
    for ws, wtag in ((1.0, "o"), (-1.0, "i")):
        for fi, (scl, dz, dy, tilt) in enumerate((
                (1.00, 0.0, 0.0, 15),
                (0.74, rmax * 0.42, rmax * 0.16, 34),
                (0.52, rmax * 0.74, rmax * 0.30, 52))):
            wing_c = Vector((cx + ws * rmax * (0.92 - 0.05 * fi),
                             cy - rmax * 0.10 + dy, z_knee + dz))
            parts.append(sphere_shell(
                f"_poleyn{tag}_wing{wtag}{fi}", wing_c,
                (rmax * 0.55 * scl, rmax * 0.72 * scl, rmax * 0.30 * scl),
                (0, math.radians(90 * ws), math.radians(tilt)), mat_gold,
                keep_z=0.30, thickness=0.008, seg=20, rings=14))
    # upper + lower articulation lames: proud front arcs bridging the gap
    for lz, lr_off in ((z_knee + rmax * 0.95, 0.008),
                       (z_knee - rmax * 0.95, 0.006)):
        _, _, radL = _limb_radial(body, min(max(lz, 0.30), 1.55), sgn, 32,
                                  win=0.055, z_max=1.60)
        rL = max(radL) + 0.014 + lr_off
        arc = []
        for j in range(15):
            a = math.pi * (0.5 + j / 14.0)      # front semicircle (-y half)
            arc.append((Vector((cx + rL * math.sin(a) * 0.98,
                                cy + rL * math.cos(a), lz)),
                        1.0 - 0.30 * abs(j / 14.0 - 0.5) * 2.0))
        parts.append(curve_obj(f"_poleyn{tag}_lame{lz:.2f}", [arc], 0.0068,
                               mat_gold))
    print(f"[02_details] poleyn{tag}: cop r={rmax:.3f} at "
          f"({cx:.3f},{cy:.3f},{z_knee})")
    return parts


def build_sabaton(body, mat_gold, sgn, tag):
    """RE-OUTFIT fixer r1 blocker #1: a REAL articulated sabaton — a lofted
    armored boot fully enclosing the foot (rounded-square cross-sections,
    tapered toe cap) + 3 overlapping instep lames + an ankle cuff. NO toes:
    sections are convex envelopes of the foot verts, never the skin itself.
    (main() deletes the body's foot polys underneath — zero poke-through.)"""
    feet = [v.co for v in body.data.vertices
            if v.co.z < 0.26 and sgn * v.co.x > 0.03]
    assert feet, f"build_sabaton: no foot verts (sgn={sgn})"
    y_heel = max(c.y for c in feet)
    y_toe = min(c.y for c in feet)
    parts = []
    NSB = 28
    n_st = 10
    floor_z = 0.004
    rings = []
    st_geo = []                       # (xc, y, w, z_top) per station
    for si in range(n_st):
        t = si / (n_st - 1)
        y = y_heel + (y_toe + 0.012 - y_heel) * t
        win = max(0.022, (y_heel - y_toe) / (n_st - 1))
        sel = [c for c in feet if abs(c.y - y) < win]
        if not sel:                   # past the toe tip: reuse last section
            xc, _, w, z_top = st_geo[-1]
        else:
            xc = 0.5 * (min(c.x for c in sel) + max(c.x for c in sel))
            w = max(abs(c.x - xc) for c in sel) + 0.007   # p4 r2: slimmer
            z_top = max(c.z for c in sel) + 0.009
        if t > 0.60:                  # tapered toe cap
            # fixer r4 blocker #11 ("crude sandal-like lame stacks, no
            # proper toe cap"): a DEFINED gothic toe cap.
            # phase4 fixer r2 major #6 ("stubby duck-foot cones"): the
            # draw-down starts earlier (0.72 -> 0.60) and pulls harder so
            # the boot narrows into a long elegant gothic profile.
            k = (t - 0.60) / 0.40
            w *= (1.0 - 0.58 * k)
            z_top = floor_z + (z_top - floor_z) * (1.0 - 0.50 * k)
        st_geo.append((xc, y, w, z_top))
        zm = 0.5 * (z_top + floor_z)
        h = 0.5 * (z_top - floor_z)
        ring = []
        p = 3.0                       # superellipse exponent (rounded square)
        for j in range(NSB):
            a = 2 * math.pi * j / NSB
            cs, sn = math.cos(a), math.sin(a)
            px = xc + w * math.copysign(abs(cs) ** (2.0 / p), cs)
            pz = zm + h * math.copysign(abs(sn) ** (2.0 / p), sn)
            ring.append(Vector((px, y, max(pz, floor_z))))
        rings.append(ring)
    # POINTED TOE CAP (fixer r5 blocker #8: "toes read as stacked slipper
    # strips"): ONE continuous pointed gothic wedge.
    # phase4 fixer r2 major #6 ("stubby duck-foot cones"): the point now
    # extends 130mm past the toes through a smooth 7-ring draw-down —
    # the long elegant Elden Ring sabaton silhouette.
    xc, y, w, z_top = st_geo[-1]
    tip = Vector((xc, y_toe - 0.130, floor_z + 0.30 * (z_top - floor_z)))
    for f in (0.80, 0.63, 0.47, 0.33, 0.20, 0.11, 0.04):
        rings.append([tip + (r0 - tip) * f for r0 in rings[-1]])
    parts.append(loft_band(f"_sabaton{tag}", rings, mat_gold,
                           thickness=0.009, bevel=0.0030))
    # ARTICULATED INSTEP LAMES (fixer r4 blocker #11): 5 REAL overlapping
    # plate strips (mesh bands with solidify thickness + chamfer), each
    # proud of the last, each finished with a rolled leading-edge rim —
    # stepped forged plates with specular breaks, not sandal straps.
    for li, si in enumerate((1, 2, 3, 4, 5)):
        xc, y, w, z_top = st_geo[si]
        zm = 0.5 * (z_top + floor_z)
        h = 0.5 * (z_top - floor_z)
        # fixer r5 blocker #8: proudness cut ~40% — the tall steps were the
        # "slipper strip" read; the lames now read as tight articulation
        off = 0.0030 + 0.0015 * li          # each lame proud of the last
        yy0 = y + 0.013 - 0.006 * li        # trailing edge (heel side)
        yy1 = y - 0.021 - 0.006 * li        # leading edge (toe side)
        lverts = []
        for yy in (yy0, yy1):
            for k in range(13):
                a = math.pi * k / 12.0
                px = xc + (w + off) * math.cos(a)
                pz = zm + (h + off) * math.sin(a)
                lverts.append(Vector((px, yy, max(pz, 0.030))))
        lfaces = [(k, k + 1, k + 14, k + 13) for k in range(12)]
        lob = mesh_obj(f"_sabaton{tag}_lame{li}", lverts, lfaces, mat_gold)
        sol = lob.modifiers.new("Solid", "SOLIDIFY")
        sol.thickness = 0.0055
        sol.offset = 0.0                    # centred: no normal-sign risk
        _chamfer(lob, 0.0022)
        apply_mods(lob)
        shade_smooth(lob)
        parts.append(lob)
        # rolled rim on the leading (visible) edge of each lame
        rim = [(Vector((xc + (w + off + 0.0022) * math.cos(math.pi * k / 12.0),
                        yy1,
                        max(zm + (h + off + 0.0022)
                            * math.sin(math.pi * k / 12.0), 0.030))), 1.0)
               for k in range(13)]
        parts.append(curve_obj(f"_sabaton{tag}_lamerim{li}", [rim], 0.0032,
                               mat_gold))
    # ANKLE COP (fixer r4 blocker #11): a domed plate over the instep/ankle
    # front bridging the cuff and the top lame.
    xc1, y1, w1, zt1 = st_geo[2]
    cop_c = Vector((xc1, y1 + 0.004, zt1 + 0.030))
    parts.append(sphere_shell(
        f"_sabaton{tag}_anklecop", cop_c,
        (w1 * 1.05, 0.052, 0.048),
        (math.radians(-38), 0, 0), mat_gold, keep_z=0.10, thickness=0.007,
        seg=20, rings=14))
    # rolled toe-cap rim: a proud arc where the toe wedge begins
    xc, y, w, z_top = st_geo[7]
    zm, h = 0.5 * (z_top + floor_z), 0.5 * (z_top - floor_z)
    arc = [(Vector((xc + (w + 0.0052) * math.cos(math.pi * k / 12.0),
                    y - 0.004,
                    max(zm + (h + 0.0052) * math.sin(math.pi * k / 12.0),
                        0.020))), 1.0)
           for k in range(13)]
    parts.append(curve_obj(f"_sabaton{tag}_toecap", [arc], 0.0054, mat_gold))
    # (fixer r5 blocker #8: the r3 toe-ridge arcs at stations 8/9 DELETED —
    # they were the "even exposed lame strips" over the toe; the single
    # extended gothic point + the toe-cap rim carry the design now.)
    # heel cup ridge: proud arc around the heel station
    xc, y, w, z_top = st_geo[0]
    zm, h = 0.5 * (z_top + floor_z), 0.5 * (z_top - floor_z)
    arc = [(Vector((xc + (w + 0.004) * math.cos(math.pi * k / 12.0), y + 0.004,
                    zm + (h + 0.004) * math.sin(math.pi * k / 12.0))), 1.0)
           for k in range(13)]
    parts.append(curve_obj(f"_sabaton{tag}_heel", [arc], 0.0052, mat_gold))
    # ankle cuff: body-fitted ring where boot meets greave (y-filtered so
    # the forward instep verts don't balloon the ring over the foot)
    _, cy_ref, _ = _limb_radial(body, 0.48, sgn, 32, win=0.045)
    cx, cy, rad = _limb_radial(body, 0.235, sgn, 32, win=0.035,
                               y_range=(cy_ref - 0.095, cy_ref + 0.095))
    cuff = []
    for j in range(32):
        a = 2 * math.pi * j / 32
        r = rad[j] + 0.011
        cuff.append((Vector((cx + r * math.sin(a), cy + r * math.cos(a),
                             0.238)), 1.0))
    parts.append(curve_obj(f"_ankleCuff{tag}", [cuff], 0.0082, mat_gold,
                           cyclic=True))
    return parts


def build_armor(mat_gold, body):
    parts = []
    # -- layered pauldrons: 3 overlapping plates, EACH with a rim lip ----------
    pauldron_r = []
    plates = [
        # (loc, scale, y-tilt deg, keep_z) — r4 minor #6: inner rims sunk
        # 18mm inward / 12mm down so every plate CONTACTS the deltoid
        # instead of floating off the shoulder.
        # p5b r3: plates shifted +35mm outward / +10mm up + slightly larger
        # to seat over the widened (+14%) shoulders and new deltoid caps.
        # fixer r1 blocker #4 (C-3PO/football read): plates FLATTENED — the
        # near-spherical z-scales ballooned; lower profiles read as forged
        # lames hugging the deltoid, not inflated domes.
        # fixer r3 blocker #2 ("arms read stubby"): every plate scaled ~-8%
        # so the pauldron mass stops swallowing the upper arm; rerebrace
        # below reads longer as a result.
        # phase4 fixer r1 major #4 ("pauldrons read as inflated balloons"):
        # x/y scaled another -8%, z -15% — lower forged-lame profiles seated
        # tighter to the deltoid, not domes.
        (Vector((0.480, 0.18, 2.606)), (0.193, 0.201, 0.092), 24, -0.15),
        (Vector((0.540, 0.18, 2.520)), (0.173, 0.185, 0.064), 44, -0.05),
        (Vector((0.576, 0.17, 2.440)), (0.153, 0.166, 0.052), 60, -0.05),
    ]
    for i, (loc, sc, tilt, kz) in enumerate(plates):
        pauldron_r.append(sphere_shell(
            f"_pauldR{i}", loc, sc, (0, math.radians(tilt), 0),
            mat_gold, keep_z=kz))
        # rim lip around EVERY plate edge — p5r1 major #6: the rim hoops sat
        # at the ellipsoid EQUATOR (full radius at z=-0.02) while the plates
        # were sunk/tilted, so they visibly FLOATED off the domes. Every ring
        # now sits at its true latitude radius sqrt(1-lat^2), scaled 0.99 so
        # it INTERSECTS the shell slightly (flush seated).
        R = Euler((0, math.radians(tilt), 0), "XYZ").to_matrix()
        # p5r2 blocker #2: rim rings SUNK into the shell (0.955 radius —
        # tube centre ~1cm inside the ellipsoid so the bevel body emerges
        # from the plate as a fused raised ridge, never a detached hoop)
        rim_lat = max(kz, -0.02) + 0.02        # just above the open edge
        rim_rad = math.sqrt(max(1.0 - rim_lat * rim_lat, 0.0)) * 0.955
        rim_spline = []
        for j in range(17):
            a = 2 * math.pi * j / 16.0
            local = Vector((sc[0] * rim_rad * math.cos(a),
                            sc[1] * rim_rad * math.sin(a),
                            sc[2] * rim_lat))
            rim_spline.append((loc + R @ local, 1.0))
        pauldron_r.append(curve_obj(f"_pauldR_rim{i}", [rim_spline],
                                    0.013 - 0.002 * i, mat_gold))
        # phase4 fixer r2 major #3: LAUREL GARLAND along the top plate's
        # rim — structured ornament at the pauldron edge (the shader's
        # all-over crackle is cut; purposeful bands carry the filigree).
        if i == 0:
            lat_g = rim_lat + 0.16
            rad_g = math.sqrt(max(1.0 - lat_g * lat_g, 0.0)) * 0.985
            for lj in range(12):
                a = 2 * math.pi * lj / 12.0
                a2 = a + 0.05
                p_g = loc + R @ Vector((sc[0] * rad_g * math.cos(a),
                                        sc[1] * rad_g * math.sin(a),
                                        sc[2] * lat_g))
                p_g2 = loc + R @ Vector((sc[0] * rad_g * math.cos(a2),
                                         sc[1] * rad_g * math.sin(a2),
                                         sc[2] * lat_g))
                d_g = p_g2 - p_g
                if d_g.length < 1e-6:
                    continue
                d_g.normalize()
                alt = 1.0 if lj % 2 == 0 else -1.0
                nrm = (R @ Vector((rad_g * math.cos(a) / sc[0],
                                   rad_g * math.sin(a) / sc[1],
                                   lat_g / sc[2]))).normalized()
                dl = (d_g + nrm.cross(d_g) * (0.60 * alt)).normalized()
                lp = [(p_g + dl * (0.015 * f) - nrm * 0.0016, rr)
                      for (f, rr) in ((-0.9, 0.18), (-0.25, 0.95),
                                      (0.35, 0.80), (1.0, 0.10))]
                pauldron_r.append(curve_obj(f"_pauldR_garl{lj}", [lp],
                                            0.0044, mat_gold))
        # fixer r5 blocker #11 ("crumpled foil leaves"): ONE bold gadroon
        # rib per plate instead of three busy channels — a smooth forged
        # bowl with a crisp rolled rim + one purposeful rib (the leaf-wrap
        # crinkle itself was the material's hammered bump — cut in 03).
        for li, (lat, bev) in enumerate(((0.46, 0.0058),)):
            rad = math.sqrt(max(1.0 - lat * lat, 0.0)) * 0.975
            ring = []
            for j in range(29):
                a = 2 * math.pi * j / 28.0
                local = Vector((sc[0] * rad * math.cos(a),
                                sc[1] * rad * math.sin(a),
                                sc[2] * lat * 0.975))
                ring.append((loc + R @ local, 1.0))
            pauldron_r.append(curve_obj(f"_pauldR_eng{i}_{li}", [ring],
                                        bev, mat_gold))
        # (p5r2 blocker #2: rivet stud spheres DELETED — they floated off the
        # tilted plates and read as stray gold droplets in empty space)
    # MESO: crest ridge over the top plate — a meridian rib front-to-back
    loc0, sc0, tilt0, _ = plates[0]
    R0 = Euler((0, math.radians(tilt0), 0), "XYZ").to_matrix()
    crest = []
    for j in range(15):
        bb = math.pi * j / 14.0
        local = Vector((0.0, sc0[1] * math.cos(bb),
                        sc0[2] * math.sin(bb))) * 0.980   # fused (p5r2)
        crest.append((loc0 + R0 @ local, 1.0 - 0.35 * abs(math.cos(bb))))
    pauldron_r.append(curve_obj("_pauldR_crest", [crest], 0.0085, mat_gold))
    # fixer r2 blocker #2: SEAT the pauldron stack — a closed under-bowl
    # (full ellipsoid just inside the top plate) fills the hollow interior
    # so no open shell edge / void shows at the armpit junction from below.
    pauldron_r.append(uv_sphere(
        "_pauldR_under", loc0 - Vector((0.0, 0.0, 0.018)),
        (sc0[0] * 0.90, sc0[1] * 0.90, sc0[2] * 0.85), mat_gold))
    # haute-piece (fixer r1 #4): a low upstanding neck-guard ridge along the
    # INNER edge of the top plate (Godfrey/knight-set language) — a short
    # proud arc between pauldron and gorget, deflecting toward the neck.
    # (haute-piece DELETED after two render passes — both cuts read as
    # claw-hooks floating off the plate, not a rolled neck-guard. Restraint
    # over bling: the crest ridge + rim lips carry the design language.)

    # -- sternum ornament: RE-OUTFIT r3 — the old skin-hugging filigree
    # (clavicle bar / scrolls / leaves) floated over the new breastplate and
    # read as a wire tangle. DELETED; the cuirass carries a medial ridge +
    # edge trims instead (engraving lives in the Mat_Gold normal detail).

    # -- forearm guards (solidified — no visible open-tube interior) ------------
    # fixer r2 blocker #4: vambrace SLIMMED (0.092/0.074 -> 0.085/0.068) so
    # the forearm doesn't read blobby, plus a third rolled ring at the wrist
    # for clear rerebrace/couter/vambrace segmentation.
    f_dir = (WRIST_R - ELBOW_R).normalized()
    g0 = ELBOW_R + f_dir * 0.015
    # phase4 fixer r2 major #5 ("stray blue fragments at the wrist"): the
    # vambrace now OVERSHOOTS the wrist by 30mm so it overlaps the gauntlet
    # cuff — no blue-underlayer body sliver can peek between the plates.
    g1 = WRIST_R + f_dir * 0.030
    guard_r = cylinder_between("_guardR", g0, g1, 0.085, 0.068, mat_gold)
    sol = guard_r.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.007
    sol.offset = -1.0
    apply_mods(guard_r)
    rib = []
    q = f_dir.to_track_quat("Z", "Y").to_matrix()
    for j in range(21):
        a = 2 * math.pi * j / 20.0
        rib.append((g1 + q @ Vector((0.071 * math.cos(a),
                                     0.071 * math.sin(a), 0)), 1.0))
    guard_rib_r = curve_obj("_guardRibR", [rib], 0.010, mat_gold)
    # MESO: bracer detail — elbow ring + mid ridge ring + wrist cuff, SUNK
    # into the guard cone so they emerge as fused raised ridges.
    guard_len = (g1 - g0).length
    guard_extra = []
    for ri, (tpos, bev) in enumerate(((0.02, 0.009), (0.52, 0.0065),
                                      (0.97, 0.0080))):
        c = g0 + f_dir * (guard_len * tpos)
        r_local = 0.085 + (0.068 - 0.085) * tpos   # cone radius at tpos
        rr = r_local - 0.003                       # centre sunk 3mm inside
        ring = []
        for j in range(21):
            a = 2 * math.pi * j / 20.0
            ring.append((c + q @ Vector((rr * math.cos(a),
                                         rr * math.sin(a), 0)), 1.0))
        guard_extra.append(curve_obj(f"_guardRingR{ri}", [ring], bev, mat_gold))

    # =======================================================================
    # RE-OUTFIT: near-full ORNATE GOLD PLATE (SPEC updated). Body-shell
    # plates guarantee fit; smoothing turns skin into forged plate; solidify
    # + chamfer give real thickness/beveled edges; trim ribs rim each plate.
    # =======================================================================

    # -- CUIRASS: breastplate+backplate wrap (chest FULLY covered) ----------
    def keep_breast(c):
        if not (2.095 < c.z < 2.660):
            return False
        ax = abs(c.x)
        if c.z > 2.56 and (c.x * c.x + (c.y - 0.21) ** 2) < 0.155 ** 2:
            return False                       # neck hole (gorget covers)
        if c.z > 2.60:
            return ax < 0.36                   # trap slope, up to the neck
        if c.z > 2.30:
            # chest/blade wall — wider at the BACK (shoulder blades)
            return ax < (0.42 if c.y > 0.19 else 0.37)
        return ax < 0.42
    # locate the nipple bumps (frontmost vert per pec box) and SUPPRESS them
    # in the shell — they read straight through the plate as golden skin
    nips = []
    for sx in (1, -1):
        cand = [v.co.copy() for v in body.data.vertices
                if 0.09 < sx * v.co.x < 0.20 and 2.26 < v.co.z < 2.40
                and v.co.y < 0.10]
        if cand:
            nips.append((min(cand, key=lambda c: c.y), 0.045))
    # fixer r2 blocker #2: trim=0.0052 — every cuirass boundary (neckline,
    # armholes, waist) now carries a rolled rim rib, so no raw open shell
    # edge shows and the plate reads bordered/finished in silhouette.
    # phase4 fixer r1 blocker #3 ("torso barrel hugely over-inflated"):
    # cuirass standoff cut 0.026 -> 0.018 + tighter clearance; the emblem/
    # ridge conform offsets below shift by the same 8mm to stay seated.
    # Trim ribs slightly bolder (rolled-rim read at Cam_Full).
    parts += body_shell(body, "_cuirass", mat_gold, keep_breast,
                        offset=0.018, thickness=0.011, smooth_iters=30,
                        trim=0.0060, trim_smooth=8, clearance_fac=0.36,
                        suppress=nips, conform=False)
    # plackart / ab lames — two overlapping lower-torso plates
    parts += body_shell(
        body, "_plackartA", mat_gold,
        lambda c: 2.015 < c.z < 2.205 and abs(c.x) < 0.42,
        offset=0.011, thickness=0.008, smooth_iters=16, trim=0.0045,
        trim_smooth=8, conform=False)
    parts += body_shell(
        body, "_plackartB", mat_gold,
        lambda c: 1.900 < c.z < 2.100 and abs(c.x) < 0.42,
        offset=0.009, thickness=0.007, smooth_iters=16, trim=0.0045,
        trim_smooth=8, conform=False)
    # medial ridge down the breastplate front (gothic plate language).
    # r15: the BVH-projected filigree (lances/volutes) rendered as loose
    # spaghetti near plate edges — DELETED. Engraving detail belongs to the
    # Mat_Gold normal/bump maps (03_materials), which deform with the mesh
    # and survive the GLB export (SPEC: surface detail as normal maps).
    ridge = []
    for k in range(12):
        z = 2.555 - k * (2.555 - 2.03) / 11.0
        ridge.append((Vector((0.0, surf_y(0.0, z) - 0.0185, z)),
                      1.0 - 0.30 * (k / 11.0)))
    parts.append(curve_obj("_cuirass_ridge", [ridge], 0.0065, mat_gold))
    # fixer r2 blocker #2: EMBOSSED BREASTPLATE MOTIF — a restrained sun-disc
    # at the sternum (two concentric rings + 8 short rays), each rib sunk
    # ~1.5mm into the plate face so it emerges as a fused raised relief that
    # reads in silhouette and specular breaks (Elden Ring goldsmith work,
    # not surface paint). Rides surf_y like the medial ridge.
    # phase4 fixer r2 major #3 ("emblem shallow, lost in the noise"): the
    # whole medallion ENLARGED ~25% and its relief deepened (bolder bevels,
    # sunk 1mm further into the plate) so it ANCHORS the breastplate.
    # phase4 fixer r3 major #3 ("emblem reads as a wagon wheel"): the inner
    # 0.115 ring + 8 spokes ARE gone — a ring with radial spokes IS a wheel.
    # The emblem is now a GOLDEN ORDER LAUREL device:
    #   - central boss (sun disc),
    #   - a DENSE LAUREL WREATH ring (the only ring — carried by leaves,
    #     not a bare hoop),
    #   - 12 tapered ORDER RAYS radiating OUTWARD from the wreath (they
    #     start OUTSIDE the ring, so nothing reads as spokes),
    # all sunk ~2mm deeper into the plate for bolder relief.
    # p4 r5 major #3 ("soft blobby sunflower"): the whole device gets
    # CRISPER, DEEPER relief — bigger hard-bevelled central boss (with a
    # raised rim ring so it reads as a struck medallion, not a bump),
    # larger/prouder leaves, bolder rays.
    mzc = 2.360                                    # sternum centre height
    parts.append(uv_sphere("_cuirass_boss",
                           Vector((0.0, surf_y(0.0, mzc) - 0.0272, mzc)),
                           (0.052, 0.026, 0.052), mat_gold))
    # hard rim ring around the boss — the crisp medallion edge
    ringb = []
    for j in range(41):
        a = 2 * math.pi * j / 40.0
        x = 0.056 * math.sin(a)
        z = mzc + 0.056 * math.cos(a)
        ringb.append((Vector((x, surf_y(x, z) - 0.0262, z)), 1.0))
    parts.append(curve_obj("_cuirass_boss_rim", [ringb], 0.0048,
                           mat_gold, cyclic=True))
    # wreath stem ring (mostly hidden under the leaves)
    ring2 = []
    for j in range(41):
        a = 2 * math.pi * j / 40.0
        x = 0.128 * math.sin(a)
        z = mzc + 0.128 * math.cos(a) * 0.90
        ring2.append((Vector((x, surf_y(x, z) - 0.0246, z)), 1.0))
    parts.append(curve_obj("_cuirass_motif_outer", [ring2], 0.0068,
                           mat_gold, cyclic=True))
    # dense laurel leaves climbing both sides of the wreath (11 per side,
    # larger + deeper relief than r2)
    for sx in (1.0, -1.0):
        for li in range(11):
            aw = 2.92 - 0.262 * li               # bottom -> near top
            wr = 0.128 + (0.008 if li % 2 == 0 else -0.006)
            xc = sx * wr * math.sin(aw)
            zc = mzc + wr * math.cos(aw) * 0.90
            # leaf tangent along the wreath circle, tilted slightly outward
            tx = sx * math.cos(aw)
            tz = -math.sin(aw) * 0.90
            tl = math.hypot(tx, tz)
            tx, tz = tx / tl, tz / tl
            s = 0.030                             # p4 r5: bigger crisp leaves
            lpts = []
            for (f, rr) in ((-0.9, 0.16), (-0.25, 0.95), (0.35, 0.78),
                            (1.0, 0.08)):
                x = xc + tx * s * f
                z = zc + tz * s * f
                lpts.append((Vector((x, surf_y(x, z) - 0.0254, z)), rr))
            parts.append(curve_obj(
                f"_wreath{'R' if sx > 0 else 'L'}{li}", [lpts], 0.0086,
                mat_gold))
    # 12 Order rays radiating OUTWARD from the wreath (long/short
    # alternation — the Elden Ring sun-burst language, not wheel spokes)
    for j in range(12):
        a = 2 * math.pi * j / 12.0 + math.pi / 12.0
        r_in = 0.172
        r_out = 0.245 if j % 2 == 0 else 0.206
        if abs(math.cos(a)) > 0.86 and math.cos(a) > 0:
            r_out = min(r_out, 0.190)             # clear the neckband above
        ray = []
        for k in range(4):
            rr = r_in + (r_out - r_in) * k / 3.0
            x = rr * math.sin(a)
            z = mzc + rr * math.cos(a) * 0.90
            ray.append((Vector((x, surf_y(x, z) - 0.0242, z)),
                        1.0 - 0.60 * (k / 3.0)))
        parts.append(curve_obj(f"_cuirass_ray{j}", [ray], 0.0072, mat_gold))
    # phase4 fixer r2 major #3 ("random crackle, not laurel filigree"):
    # STRUCTURED LAUREL GARLAND BANDS as real raised goldsmith relief —
    # alternating tapered leaf cords riding a guide line, conformed to the
    # plate via surf_y. Three purposeful bands over a now mostly-clean
    # polished field (the shader's crackle union is cut in 03_materials):
    #   1. neckline garland (inside the collar border)
    #   2. waist garland (above the belt line)
    def _chest_garland(tag, z_of, r_of, n_leaf, a0, a1, sunk, ls):
        made = 0
        for li in range(n_leaf):
            t = li / max(n_leaf - 1, 1)
            a = a0 + (a1 - a0) * t
            x = r_of(a) * math.sin(a)
            z = z_of(a)
            # tangent along the band
            a2 = a + 0.02
            x2 = r_of(a2) * math.sin(a2)
            z2 = z_of(a2)
            d3 = Vector((x2 - x, 0.0, z2 - z))
            if d3.length < 1e-6:
                continue
            d3.normalize()
            alt = 1.0 if li % 2 == 0 else -1.0
            # tapered laurel leaf: 4 control points along a tilted dir.
            # (iter-2: tilt cut 0.60 -> 0.28 — the steep tilt drove leaf
            # tips through the curved plate and they rendered as buried
            # crack-shards, not a garland.)
            dl = (d3 + Vector((0.0, 0.0, 0.28 * alt))
                  if abs(d3.z) < 0.5 else
                  d3 + Vector((math.copysign(0.28 * alt, x if x else 1.0),
                               0.0, 0.0)))
            dl.normalize()
            lp = []
            for (f, rr) in ((-0.9, 0.18), (-0.25, 0.95), (0.35, 0.80),
                            (1.0, 0.10)):
                xx = x + dl.x * ls * f
                zz = z + dl.z * ls * f
                lp.append((Vector((xx, surf_y(xx, zz) - sunk, zz)), rr))
            parts.append(curve_obj(f"_garland_{tag}{li}", [lp], 0.0048,
                                   mat_gold))
            made += 1
        return made
    # phase4 fixer r3: the r2 neck/waist garland leaf cords rendered as
    # scattered half-buried SHARDS on the curved plate faces (debris, not
    # laurel) — DELETED. Plate-face laurel ornament now lives in Mat_Gold's
    # structured LAUREL SCROLL BANDS (03_materials, deep-cut + cavity
    # grime); the physical wreath stays only on the emblem, where it
    # conforms cleanly to the sternum face.
    _ = _chest_garland  # helper retained for future conformal bands
    print("[02_details] chest garlands removed (p4 r3 — shader bands)")
    # (refine iter-2: the clavicle volute spirals rendered as detached
    # floating wire hooks off the curved upper chest — same failure mode as
    # the r15 BVH filigree. DELETED; upper-chest scrollwork stays in the
    # procedural Mat_Gold engraving.)
    # engraved border band around the neckline: a sunk rib inside the
    # collar opening that fuses into the plate as a chased border line
    nb = []
    for j in range(25):
        a = math.pi * (j / 24.0) - math.pi / 2.0   # front semicircle
        x = 0.150 * math.sin(a)
        z = 2.545 + 0.028 * math.cos(a)
        nb.append((Vector((x, surf_y(x, min(z, 2.60)) - 0.0190, z)), 1.0))
    parts.append(curve_obj("_cuirass_neckband", [nb], 0.0042, mat_gold))

    # -- GORGET: 3 stacked collar lames around the neck ---------------------
    # body-fitted telescoping collar: 4 lames narrowing up the neck, the
    # lower two riding OVER the cuirass collar (r17: the analytic ellipse
    # gorget let the cuirass poke through as floating tabs)
    gor_rings = []
    NG = 64
    for (gz, clr) in ((2.575, 0.038), (2.645, 0.034),
                      (2.705, 0.020), (2.745, 0.013)):
        cy, rad = body_radial(body, gz, NG, win=0.04, xmax=0.30)
        ring = []
        for j in range(NG):
            a = 2 * math.pi * j / NG
            r = rad[j] + clr
            ring.append(Vector((r * math.sin(a), cy + r * math.cos(a), gz)))
        gor_rings.append(ring)
    parts.append(loft_band("_gorget", gor_rings, mat_gold, thickness=0.009))
    cy, rad = body_radial(body, 2.746, NG, win=0.04, xmax=0.30)
    gtop = [(Vector(((rad[j] + 0.015) * math.sin(2 * math.pi * j / NG),
                     cy + (rad[j] + 0.015) * math.cos(2 * math.pi * j / NG),
                     2.747)), 1.0) for j in range(NG)]
    parts.append(curve_obj("_gorget_rim", [gtop], 0.0060, mat_gold,
                           cyclic=True))

    # (fixer r2 blocker #4: the OLD analytic-ellipse FAULDS block that used
    # to live here built a SECOND set of _fauld0-3 shells interleaved with
    # the body-fitted set below — the doubled scalloped hems z-fought and
    # rendered as wavy "melted wax" edges. DELETED: the body-fitted block
    # below is the only fauld builder now.)

    # -- under-skirt: rigid gold liner so lame/tasset gaps never show skin --
    # (body-fitted: cross-sections sampled from the real body, r5)
    # r3 iter-3 (blocker #2 "torn/jagged crotch"): clearance 0.010 -> 0.019
    # so this smooth forged drum sits OUTSIDE the pelvis shell (offset 0.008)
    # and MASKS its wandering boundary — the visible crotch surface is now a
    # deliberate smooth plate, finished with a hem rib.
    NSF = 96
    us_rings = []
    for uz in (1.980, 1.820, 1.640, 1.460, 1.340, 1.255, 1.212):
        cy, rad = body_radial(body, uz, NSF)
        ring = []
        for j in range(NSF):
            a = 2 * math.pi * j / NSF
            r = rad[j] + 0.019
            ring.append(Vector((r * math.sin(a), cy + r * math.cos(a), uz)))
        us_rings.append(ring)
    parts.append(loft_band("_underskirt", us_rings, mat_gold,
                           thickness=0.006))
    cy, rad = body_radial(body, 1.213, NSF)
    us_hem = [(Vector(((rad[j] + 0.021) * math.sin(2 * math.pi * j / NSF),
                       cy + (rad[j] + 0.021) * math.cos(2 * math.pi * j / NSF),
                       1.215)), 1.0) for j in range(NSF)]
    parts.append(curve_obj("_underskirt_hem", [us_hem], 0.0048, mat_gold,
                           cyclic=True))

    # -- FAULDS: 4 overlapping hip lames (rigid, fluted, scalloped), each
    # ring FITTED to the sampled body cross-section + growing clearance ------
    # p4 r5 major #6 ("stacked loose rings with visible gaps between
    # lames"): per-lame OVERLAP DEEPENED (each lame's top now rides well
    # under the hem of the lame above) and the radial clearance step cut,
    # so no dark gap band shows between lames.
    FAULDS = [
        # z0, z1, base clearance (grows down each lame: layered look)
        (1.975, 1.845, 0.020),
        (1.900, 1.725, 0.025),
        (1.795, 1.600, 0.030),
        (1.680, 1.480, 0.035),
    ]
    # phase4 fixer r3 major #4 ("faulds read as ribbed stovepipe cylinders"):
    # the cos(10a) fluting + uniform ring hems WERE the stovepipe. Each lame
    # is now a clean OVERLAPPING ARTICULATED plate: no fluting, a gothic
    # V-POINT dipping at the front centreline, a slight per-lame width
    # taper (each lame visibly narrower at its hem than its top — the
    # imbricated draw), a bolder chamfer, and a rolled hem rib that follows
    # the V. The growing per-lame clearance keeps the visible overlap steps.
    for bi, (z0, z1, clr) in enumerate(FAULDS):
        rings = []
        nz = 5
        for i in range(nz):
            t = i / (nz - 1)
            zz = z0 + (z1 - z0) * t
            cy, rad = body_radial(body, zz, NSF)
            ring = []
            for j in range(NSF):
                a = 2 * math.pi * j / NSF
                # front-centre emphasis: the lame bows slightly proud at the
                # front (forged draw), tapers ~3mm inward toward its hem
                front = max(0.0, math.cos(a - math.pi))
                r = rad[j] + clr + 0.010 * t - 0.003 * t \
                    + 0.004 * front * (0.3 + 0.7 * t)
                zj = zz
                if i == nz - 1:                    # gothic V-point hem
                    zj -= 0.016 * (front ** 3.0)
                ring.append(Vector((r * math.sin(a), cy + r * math.cos(a),
                                    zj)))
            rings.append(ring)
        parts.append(loft_band(f"_fauld{bi}", rings, mat_gold,
                               thickness=0.0085, bevel=0.0036))
        # rolled hem rib follows the V-point, slightly proud
        cy, rad = body_radial(body, z1, NSF)
        trim_pts = []
        for j in range(NSF):
            a = 2 * math.pi * j / NSF
            front = max(0.0, math.cos(a - math.pi))
            r = rad[j] + clr + 0.007 + 0.004 * front + 0.004
            zj = z1 - 0.016 * (front ** 3.0)
            trim_pts.append((Vector((r * math.sin(a),
                                     cy + r * math.cos(a), zj)), 1.0))
        parts.append(curve_obj(f"_fauld{bi}_rim", [trim_pts], 0.0052,
                               mat_gold, cyclic=True))

    # -- TASSETS: hanging thigh plates, body-fitted drum ----------------------
    z_top, z_bot = 1.545, 1.175
    n_a, n_z = 9, 7
    trows = []
    for i in range(n_z):
        t = i / (n_z - 1)
        zz = z_top + (z_bot - z_top) * t
        cy, rad = body_radial(body, zz, NSF)
        trows.append((zz, cy, rad))

    def _trow_at(tf):
        """Interpolated (zz, cy, rad[]) at fraction tf of the tasset span."""
        f = tf * (n_z - 1)
        i0 = min(int(f), n_z - 2)
        u = f - i0
        z0, cy0, r0 = trows[i0]
        z1, cy1, r1 = trows[i0 + 1]
        return (z0 + (z1 - z0) * u, cy0 + (cy1 - cy0) * u,
                [r0[j] + (r1[j] - r0[j]) * u for j in range(NSF)])

    def tasset(name, phi_c, wf=1.0):
        """fixer r4 blocker #8 ("boxy rectangular thigh tassets"): each
        tasset is now THREE overlapping curved SCALE-LAMES that follow the
        thigh — a short imbricated stack, each lame proud of the one above,
        each with a rounded hem + rolled rim rib. Row radii stay RIGID
        (max body radius over the lame's angular span — the r3 crotch-bridge
        fix is preserved), and each lame keeps a convex bow so nothing reads
        as a flat slab."""
        out = []
        n_lr = 4                            # rows per lame
        for L in range(3):
            # p4 r5 major #6: deeper lame overlap (span 0.44 -> 0.54,
            # stride 0.28 -> 0.24) — no dark slit shows between scales
            t0f, t1f = L * 0.24, L * 0.24 + 0.54   # overlapping spans
            lverts = []
            hem_pts = []
            for i in range(n_lr):
                tf = t0f + (t1f - t0f) * i / (n_lr - 1)
                zz, cy, rad = _trow_at(tf)
                half_w = math.radians(26.5) * wf * (1.0 - 0.22 * tf)
                ks = [int(((math.pi - (phi_c + half_w
                                       * (jj / (n_a - 1) * 2 - 1)))
                           % (2 * math.pi)) / (2 * math.pi) * NSF) % NSF
                      for jj in range(n_a)]
                rr_max = max(rad[k] for k in ks)
                for j in range(n_a):
                    u = j / (n_a - 1) * 2.0 - 1.0
                    phi = phi_c + half_w * u
                    a = (math.pi - phi) % (2 * math.pi)
                    bow = 0.015 * (1.0 - u * u)
                    # p4 r5 major #6: radial step per lame 0.0075 -> 0.0050
                    r = rr_max + 0.024 + 0.010 * tf + 0.0050 * L + bow
                    zj = zz
                    if i == n_lr - 1:       # rounded scale hem per lame
                        zj += 0.014 * (u * u) - 0.006
                    p = Vector((r * math.sin(a), cy + r * math.cos(a), zj))
                    lverts.append(p)
                    if i == n_lr - 1:
                        hem_pts.append((p + Vector((
                            0.004 * math.sin(a), 0.004 * math.cos(a),
                            -0.002)), 1.0 - 0.30 * abs(u)))
            faces = []
            for i in range(n_lr - 1):
                for j in range(n_a - 1):
                    q = i * n_a + j
                    faces.append((q, q + 1, q + n_a + 1, q + n_a))
            ob = mesh_obj(f"{name}_lame{L}", lverts, faces, mat_gold)
            sol = ob.modifiers.new("Solid", "SOLIDIFY")
            sol.thickness = 0.009
            sol.offset = 0.0
            _chamfer(ob, 0.0032)
            apply_mods(ob)
            shade_smooth(ob)
            out.append(ob)
            # rolled hem rim rib on every lame edge (imbricated scale read)
            out.append(curve_obj(f"{name}_rim{L}", [hem_pts], 0.0040,
                                 mat_gold))
        return out

    # r3 iter-2: FRONT tasset widened (0.75 -> 1.05) — the narrow crotch
    # plate left two jagged void slots against its neighbours
    for k, phi_deg in enumerate((0, 52, 104, 156, -52, -104, -156)):
        parts += tasset(f"_tasset{k}", math.radians(phi_deg),
                        wf=1.05 if phi_deg == 0 else 1.0)

    # -- plate belt at the fauld top (body-fitted) ----------------------------
    cy, rad = body_radial(body, 1.972, NSF)
    belt_pts = []
    for j in range(NSF):
        a = 2 * math.pi * j / NSF
        r = rad[j] + 0.016
        belt_pts.append((Vector((r * math.sin(a), cy + r * math.cos(a),
                                 1.972)), 1.0))
    parts.append(curve_obj("_beltplate", [belt_pts], 0.020, mat_gold,
                           cyclic=True))
    parts.append(uv_sphere("_beltclasp", Vector((0.0, 0.012, 1.972)),
                           (0.044, 0.020, 0.052), mat_gold))
    # STUDDED belt (SPEC): dome studs proud of the belt cord, evenly spaced
    # around the ring, skipping the front clasp span
    n_stud = 0
    for j in range(0, NSF, 6):
        a = 2 * math.pi * j / NSF
        if abs(a - math.pi) < 0.42:              # clasp sits at the front
            continue
        r = rad[j] + 0.016 + 0.011
        parts.append(uv_sphere(
            f"_beltstud{n_stud}",
            Vector((r * math.sin(a), cy + r * math.cos(a), 1.972)),
            (0.0135, 0.0135, 0.0165), mat_gold, seg=12, rings=8))
        n_stud += 1

    # -- pelvis shell: closes the pubic/crotch triangles behind the tassets --
    # fixer r3 blocker #2: the raw shell boundary rendered as a TORN/JAGGED
    # hem at the crotch. The boundary loop is now heavily smoothed and rimmed
    # with a rolled trim rib (trim=0.0050) so the front panel hem reads as a
    # deliberate finished plate edge.
    # (r3 iter-3: offset dropped 0.012 -> 0.008 and trim REMOVED — this
    # shell is now a pure skin-coverage liner tucked INSIDE the underskirt
    # drum; its wandering boundary must never be the visible surface)
    parts += body_shell(
        body, "_pelvisplate", mat_gold,
        lambda c: 1.26 < c.z < 1.68 and abs(c.x) < 0.27,
        offset=0.008, thickness=0.007, smooth_iters=22, smooth_fac=0.5,
        bevel=0.0024, conform=False)

    # -- RIGHT-LEG plate (mirrored to the left below) ------------------------
    leg_r = []
    # cuisse (thigh plate) — forged smooth, no thigh muscle print-through
    leg_r += body_shell(
        body, "_cuisseR", mat_gold,
        lambda c: 0.96 < c.z < 1.58 and c.x > 0.025,
        offset=0.013, thickness=0.008, smooth_iters=18, trim=0.0050,
        conform=False)
    # REFINE (ornate pass): chased ring bands around each cuisse — the
    # thigh plates carry goldsmith banding like the greaves/vambraces
    for sgn, ctag in ((1, "R"), (-1, "L")):
        for bi, bz in enumerate((1.10, 1.24)):
            ccx, ccy, crad = _limb_radial(body, bz, sgn, 40, win=0.05)
            band = []
            for j in range(41):
                a = 2 * math.pi * j / 40.0
                rr = crad[int(j % 40)] + 0.0125
                band.append((Vector((ccx + rr * math.sin(a),
                                     ccy + rr * math.cos(a), bz)), 1.0))
            parts.append(curve_obj(f"_cuisseband{ctag}{bi}", [band],
                                   0.0038, mat_gold, cyclic=True))
    # poleyn (knee cop): fixer r3 blocker #2 — the old hand-placed sphere
    # shell sat too small/deep and the knees read as bare gold gaps. Now a
    # real articulated build_poleyn() per side (with the greaves below).
    # RE-OUTFIT fixer r1: greaves + sabatons are now PARAMETRIC rigid forms
    # (lofted envelope sections) — built per-side below, NOT mirrored, so
    # nothing here. See build_greave() / build_sabaton().

    # -- arm-root collars: plate the armpit/deltoid ring itself --------------
    # (besagew discs floated and still left red in the skincheck — a shell
    # extracted from the arm-root region hugs the crease from every angle)
    for sgn, tag in ((1, "R"), (-1, "L")):
        # fixer r2 blocker #2: trim=0.0040 rolls every armroot boundary so
        # the pauldron-armpit junction shows finished rims, not open shell
        # edges / jagged gaps.
        parts += body_shell(
            body, f"_armroot{tag}", mat_gold,
            lambda c, sgn=sgn: (2.26 < c.z < 2.67
                                and 0.26 < sgn * c.x < 0.56),
            offset=0.011, thickness=0.008, smooth_iters=20, smooth_fac=0.5,
            bevel=0.0024, trim=0.0040, conform=False)

    # -- RIGHT-ARM plate: rerebrace (upper arm) + couter (elbow) -------------
    arm_r = []
    # fixer r2 blocker #4: rerebrace SLIMMED (0.165/0.118 -> 0.150/0.108) —
    # the fat upper-arm cylinder made the whole arm read stubby/balloon.
    # fixer r4 blocker #8: anchors ride the arm stretch (same transform as
    # the mesh) so the plates track the lengthened arm.
    rb0 = _arm_stretch(Vector((0.535, 0.228, 2.470)))
    rb1 = _arm_stretch(Vector((0.755, 0.148, 2.200)))
    rdir = (rb1 - rb0).normalized()
    rq = rdir.to_track_quat("Z", "Y").to_matrix()
    rlen = (rb1 - rb0).length
    # p4 r5 major #6 ("smooth inflated balloon sleeve"): the single smooth
    # tapered tube is replaced by THREE OVERLAPPING ARTICULATED LAMES —
    # each a short tapered cylinder segment riding proud of the one below
    # (imbricated toward the elbow), with real thickness, chamfered edges
    # and a rolled hem ring per lame. The silhouette now steps like a real
    # rerebrace harness instead of reading as one inflated sleeve.
    RERE_LAMES = ((0.00, 0.42, 0.0060), (0.32, 0.72, 0.0030),
                  (0.62, 1.00, 0.0000))
    for li, (t0, t1, lift) in enumerate(RERE_LAMES):
        p0 = rb0 + rdir * (rlen * t0)
        p1 = rb0 + rdir * (rlen * t1)
        r0 = 0.150 + (0.108 - 0.150) * t0 + lift
        r1 = 0.150 + (0.108 - 0.150) * t1 + lift
        lam = cylinder_between(f"_rerebraceR{li}", p0, p1, r0, r1, mat_gold)
        sol = lam.modifiers.new("Solid", "SOLIDIFY")
        sol.thickness = 0.007
        sol.offset = -1.0
        _chamfer(lam, 0.0028)
        apply_mods(lam)
        arm_r.append(lam)
        # rolled hem ring at each lame's lower (elbow-side) edge
        cc = rb0 + rdir * (rlen * (t1 - 0.02))
        rr = 0.150 + (0.108 - 0.150) * (t1 - 0.02) + lift + 0.002
        ring = [(cc + rq @ Vector((rr * math.cos(2 * math.pi * j / 24.0),
                                   rr * math.sin(2 * math.pi * j / 24.0),
                                   0)), 1.0) for j in range(24)]
        arm_r.append(curve_obj(f"_rereRingR{li}", [ring], 0.0062, mat_gold,
                               cyclic=True))
    # top collar ring seating the harness under the pauldron
    cc = rb0 + rdir * (rlen * 0.06)
    rr = 0.150 + (0.108 - 0.150) * 0.06 + 0.0060 + 0.002
    ring = [(cc + rq @ Vector((rr * math.cos(2 * math.pi * j / 24.0),
                               rr * math.sin(2 * math.pi * j / 24.0),
                               0)), 1.0) for j in range(24)]
    arm_r.append(curve_obj("_rereRingRtop", [ring], 0.0075, mat_gold,
                           cyclic=True))
    arm_r += body_shell(
        body, "_elbowR", mat_gold,
        lambda c: (c - ELBOW_R).length < 0.150,
        offset=0.0090, thickness=0.006, smooth_iters=16, smooth_fac=0.5,
        bevel=0.0022, conform=False)
    arm_r.append(uv_sphere("_elbowPlugR",
                           _arm_stretch(Vector((0.740, 0.058, 2.175))),
                           (0.060, 0.048, 0.088), mat_gold))
    # upper-forearm shell: the extensor bulge pokes past the conical
    # vambrace (redray: x .86-.93, z 2.10-2.18) — plate the bulge itself
    # (fixer r4: box widened to cover the stretched forearm)
    arm_r += body_shell(
        body, "_forearmR", mat_gold,
        lambda c: 0.73 < c.x < 1.00 and 2.03 < c.z < 2.26,
        offset=0.009, thickness=0.006, smooth_iters=12, smooth_fac=0.45,
        bevel=0.0024, conform=False)
    arm_r.append(sphere_shell("_couterR",
                              _arm_stretch(Vector((0.770, 0.168, 2.180))),
                              (0.105, 0.105, 0.115),
                              (math.radians(-30), math.radians(75), 0),
                              mat_gold, keep_z=-0.05, thickness=0.009))
    # p4 r5 major #6: COUTER FAN — two smaller overlapping fan lames above
    # the elbow cop (toward the rerebrace), the classic gothic elbow
    # articulation; the arm now reads rerebrace -> fan -> couter -> vambrace
    for fi, (foff, fsc) in enumerate(((0.055, 0.088), (0.105, 0.072))):
        fc = _arm_stretch(Vector((0.770, 0.168, 2.180))) - rdir * foff
        arm_r.append(sphere_shell(f"_couterFanR{fi}", fc,
                                  (fsc, fsc, fsc * 1.08),
                                  (math.radians(-30), math.radians(75), 0),
                                  mat_gold, keep_z=-0.02, thickness=0.008))

    # -- GAUNTLETS: plate shells over BOTH hands (asymmetric curl) -----------
    ghx = 0.795 + _HAND_SH.x               # fixer r4: stretched-hand region
    ghz = 2.12 + _HAND_SH.z
    # fixer r5 blocker #11: shell offset/thickness up ~30% — the gauntlet
    # must read as forged plate over the hand, never a gold-dipped glove
    parts += body_shell(
        body, "_gauntletR", mat_gold,
        lambda c: c.x > ghx and c.z < ghz,
        offset=0.0075, thickness=0.0065, smooth_iters=5, smooth_fac=0.4,
        bevel=0.0024)
    parts += body_shell(
        body, "_gauntletL", mat_gold,
        lambda c: c.x < -ghx and c.z < ghz,
        offset=0.0075, thickness=0.0065, smooth_iters=5, smooth_fac=0.4,
        bevel=0.0024)
    # fixer r3 major #4 ("skinny gold-dipped anatomical fingers"): ARTICULATED
    # gauntlet detail — a knuckle-plate ring at the metacarpal line, segmented
    # finger LAME rings down the finger mass, and a flared wrist cuff. All
    # fitted from the real hand cross-sections (nothing hand-placed).
    for sgn, tag in ((1.0, "R"), (-1.0, "L")):
        W = Vector((WRIST_R.x * sgn, WRIST_R.y, WRIST_R.z))
        klm = body.get(f"godwyn_knuckle_{tag.lower()}")
        if klm is None:
            print(f"[02_details] WARNING: knuckle landmark {tag} missing — "
                  "gauntlet lames skipped", file=sys.stderr)
            continue
        K = Vector(klm)
        hand = [v.co.copy() for v in body.data.vertices
                if sgn * v.co.x > ghx and v.co.z < ghz]
        d = (K - W).normalized()
        beyond = sorted((v for v in hand if (v - K).dot(d) > 0.0),
                        key=lambda v: (v - K).dot(d))
        if len(beyond) > 20:                     # refine d toward fingertips
            tipc = sum(beyond[-len(beyond) // 5:], Vector()) \
                / (len(beyond) // 5)
            d = (tipc - K).normalized()
        u = d.cross(Vector((0, 0, 1)))
        u = u.normalized() if u.length > 1e-5 else Vector((0, 1, 0))
        w = d.cross(u).normalized()

        # back-of-hand direction: perpendicular from the hand axis to the
        # stored knuckle landmark (which 02 placed on the BACK of the hand)
        gd_out = K - (W + d * ((K - W).dot(d)))
        gd_out = gd_out.normalized() if gd_out.length > 1e-5 \
            else Vector((0, -1, 0))
        phi0 = math.atan2(gd_out.dot(w), gd_out.dot(u))

        def _hand_ring(name, origin, s_off, clr, bev, width=0.011,
                       r_cap=0.070, arc=None):
            # r3 iter-2: radii use the 80th-PERCENTILE extent (max caught the
            # spread thumb and rendered giant floating hoops) and are HARD
            # CAPPED — a slightly-sunk ring reads as a fused plate joint.
            # fixer r4 major: arc=half-span (radians) builds a BACK-HALF arc
            # centred on gd_out instead of a full hoop — per-phalanx scale
            # plates over the finger backs, not sausage rings.
            cs = [v for v in hand if abs((v - origin).dot(d) - s_off) < width]
            if len(cs) < 8:
                return None
            c = sum(cs, Vector()) / len(cs)
            c = origin + d * s_off + (c - origin - d * s_off
                                      - d * (c - origin - d * s_off).dot(d))
            eu = sorted(abs((v - c).dot(u)) for v in cs)
            ew = sorted(abs((v - c).dot(w)) for v in cs)
            ru = min(eu[int(len(eu) * 0.8)] + clr, r_cap)
            rw = min(ew[int(len(ew) * 0.8)] + clr, r_cap)
            ring = []
            if arc is None:
                for j in range(21):
                    a = 2 * math.pi * j / 20.0
                    ring.append((c + u * (ru * math.cos(a))
                                 + w * (rw * math.sin(a)), 1.0))
                return curve_obj(name, [ring], bev, mat_gold, cyclic=True)
            for j in range(13):
                a = phi0 - arc + 2.0 * arc * j / 12.0
                fadew = 1.0 - 0.45 * abs(j / 12.0 - 0.5) * 2.0
                ring.append((c + u * (ru * math.cos(a))
                             + w * (rw * math.sin(a)), fadew))
            return curve_obj(name, [ring], bev, mat_gold)
        # knuckle plate + 5 overlapping phalanx scale-lames (back-half arcs)
        # + full-ring flared cuff rows
        # fixer r5 blocker #11: finger lames THICKENED ~40% (bev + clearance)
        # — the thin rings rendered as bent-twig fingers in close-up
        # phase4 fixer r2 major #6 ("lumpy claw"): the finger lames now
        # TAPER — each successive lame's radius cap shrinks toward the
        # fingertips so the plates read as articulated tapering fingers,
        # not a uniform mitt.
        for nm, org, s_off, clr, bev, arc, rcap in (
                (f"_gauntlet{tag}_knuckle", K, 0.000, 0.0062, 0.0080, 1.45,
                 0.068),
                (f"_gauntlet{tag}_lame0", K, 0.024, 0.0055, 0.0067, 1.30,
                 0.062),
                (f"_gauntlet{tag}_lame1", K, 0.044, 0.0052, 0.0064, 1.25,
                 0.057),
                (f"_gauntlet{tag}_lame2", K, 0.064, 0.0050, 0.0062, 1.20,
                 0.052),
                (f"_gauntlet{tag}_lame3", K, 0.084, 0.0046, 0.0056, 1.15,
                 0.047),
                (f"_gauntlet{tag}_lame4", K, 0.102, 0.0042, 0.0050, 1.10,
                 0.042),
                (f"_gauntlet{tag}_cuff", W, 0.028, 0.0075, 0.0090, None,
                 0.070),
                (f"_gauntlet{tag}_cuffF", W, 0.006, 0.0105, 0.0078, None,
                 0.070)):
            ob = _hand_ring(nm, org, s_off, clr, bev, r_cap=rcap, arc=arc)
            if ob is not None:
                parts.append(ob)
        # KNUCKLE GADLINGS (fixer r4 blocker #11): four small pyramidal studs
        # across the knuckle row — the classic gothic gauntlet accent.
        for gi, goff in enumerate((-0.048, -0.016, 0.016, 0.048)):
            gp = K + u * goff + gd_out * 0.0075
            parts.append(uv_sphere(f"_gauntlet{tag}_gadling{gi}", gp,
                                   (0.0105, 0.0105, 0.0085), mat_gold,
                                   seg=12, rings=8))
        print(f"[02_details] gauntlet{tag}: knuckle cop + 5 phalanx lames "
              f"+ 4 gadlings + flared cuff "
              f"(d=({d.x:.2f},{d.y:.2f},{d.z:.2f}))")

    # -- GREAVES + SABATONS: parametric rigid forms, built per side ----------
    # (fixer r1 blockers #1/#2 — envelope lofts, never body-conforming)
    for sgn, tag in ((1, "R"), (-1, "L")):
        parts += build_greave(body, mat_gold, sgn, tag)
        parts += build_sabaton(body, mat_gold, sgn, tag)
        parts += build_poleyn(body, mat_gold, sgn, tag)

    # mirror the one-sided pieces to the left
    right_side = pauldron_r + [guard_r, guard_rib_r] + guard_extra \
        + leg_r + arm_r
    mirrored = [mirror_x(ob, ob.name + "_L") for ob in right_side]
    parts += right_side + mirrored

    return join(parts, "Godwyn_Armor")


# ---------------------------------------------------------------------------
# TABARD (refine pass: the blue is INTEGRATED INTO the armor — SPEC updated,
# @DOUJ reference. The back CAPE is GONE. The blue is now:
#   - a hanging front TABARD / SURCOAT panel, waist belt -> floor (primary)
#   - two side panels + a trailing back panel hanging from the same belt
#   - a blue UNDERLAYER band showing beneath the gold underskirt hem,
#     between the tassets (cloth peeking between the plates)
# Every panel edge carries GOLD LAUREL EMBROIDERY: a border cord, a
# meandering vine, and tapered leaf cords. One unified gold-and-blue
# ensemble — never a cape. Renamed Godwyn_Cape -> Godwyn_Tabard; the
# 03_materials / 03b / 04_rig / 07_export contracts follow.)
# ---------------------------------------------------------------------------

def _hang_panel(name, body, mat, a_c, w_top, w_hem, z_top, z_hem, clr_top,
                clr_body, seed_ph, toe_flare=0.0, hem_drop=0.0,
                span_half=0.52):
    """One hanging cloth panel: a FLAT CHORD strip facing direction a_c
    (angle from +y about the body axis), NOT a wrap-around arc — iter-2
    fix: angular panels wrapped the hips and the four of them fused into a
    blue SKIRT; flat chords read as separate hanging tabard panels with
    the gold tassets showing between them.

    Each row's standoff r is the MAXIMUM body radius over the panel's
    whole angular window (span_half) + clearance, with a running maximum
    down the hang — the cloth falls as a straight chord OVER the belt /
    faulds / tassets (real drape, and tassets can never poke through).
    Graded pleats, hem weight and a scalloped hem keep it cloth. toe_flare
    kicks the lowest rows outward so the hem breaks over the sabatons.
    Returns (mesh_object, edge_paths) — edge paths feed the embroidery.
    """
    NU, NV = 26, 44
    NR = 72                                   # radial sampling resolution
    dvec = Vector((math.sin(a_c), math.cos(a_c), 0.0))   # panel facing
    tvec = Vector((math.cos(a_c), -math.sin(a_c), 0.0))  # panel tangent
    k0 = int(((a_c - span_half) % (2 * math.pi)) / (2 * math.pi) * NR)
    nk = max(2, int(span_half * 2 / (2 * math.pi) * NR))
    verts = []
    paths = {"L0": [], "L1": [], "R0": [], "R1": [], "hem0": [], "hem1": []}
    r_run = None
    cy0 = None
    for i in range(NV):
        t = i / (NV - 1)
        z = z_top + (z_hem - z_top) * t
        cy, rad = body_radial(body, max(z, 0.30), NR)
        if cy0 is None:
            cy0 = cy
        rmax = max(rad[(k0 + kk) % NR] for kk in range(nk + 1))
        clr = clr_top + (clr_body - clr_top) * min(1.0, t / 0.10)
        row_r = rmax + clr
        if r_run is None:
            r_run = row_r
        else:
            # cloth hangs off the widest plate above; relaxes ~0.8mm/row
            r_run = max(row_r, r_run - 0.0008)
        halfw = 0.5 * (w_top + (w_hem - w_top) * (t ** 1.15))
        for j in range(NU):
            u = j / (NU - 1) * 2.0 - 1.0
            # graded pleats over an asymmetrically warped u (no two folds
            # share a width — same language as the r5 cape fix)
            uw = u + 0.13 * math.sin(2.1 * u + seed_ph)
            sA = math.sin((9.0 - 4.0 * t) * uw + seed_ph + 0.8 * t)
            # phase4 fixer r2 major #5 ("rigid board-like planes with
            # angular kicks"): pleat profile SOFTENED (0.60 -> 0.85
            # exponent = rounded fold crowns, not creased planes)
            pleat = math.copysign(abs(sA) ** 0.85, sA)
            r = r_run \
                + 0.026 * (0.12 + 0.88 * t) * pleat \
                + 0.015 * (t ** 1.4) * math.sin(3.1 * uw - 1.1 + seed_ph) \
                + 0.008 * (t ** 1.6) * math.sin(11.0 * uw + 4.2 * t + seed_ph)
            # hem weight: the bottom band compresses into deeper folds
            hemf = max(0.0, (t - 0.78) / 0.22)
            r += 0.015 * hemf * math.sin(8.5 * uw + 1.7 + seed_ph)
            # sabaton clearance: hem breaks outward over the foot plates
            # (p4 r2: gentler ramp — the hard 1.6-power kick splayed the
            # hem into rigid angled boards at the floor)
            r += toe_flare * (max(0.0, (0.50 - z) / 0.50) ** 2.4)
            # side edges curl back toward the body (finished cloth border,
            # breaks the perfectly flat board read)
            r -= 0.030 * (abs(u) ** 2.5)
            # hem curls slightly INWARD near the floor (cloth settling on
            # itself — p4 r2 major #5, kills the splayed-plane read)
            r -= 0.020 * (max(0.0, (t - 0.90) / 0.10) ** 1.5)
            zj = z
            if t > 0.86:                       # scalloped hem (softer, p4 r2)
                zj -= (0.020 + hem_drop) * ((t - 0.86) / 0.14) \
                    * (0.5 + 0.5 * math.sin(4.2 * uw + seed_ph))
            p = Vector((0.0, cy0, 0.0)) + dvec * r + tvec * (halfw * u)
            p.z = zj
            verts.append(p)
            if j == 0:
                paths["L0"].append(p.copy())
            elif j == 2:
                paths["L1"].append(p.copy())
            elif j == NU - 3:
                paths["R1"].append(p.copy())
            elif j == NU - 1:
                paths["R0"].append(p.copy())
            if i == NV - 1:
                paths["hem0"].append(p.copy())
            elif i == NV - 4:
                paths["hem1"].append(p.copy())
    faces = []
    for i in range(NV - 1):
        for j in range(NU - 1):
            q = i * NU + j
            faces.append((q, q + 1, q + NU + 1, q + NU))
    ob = mesh_obj(name, verts, faces, mat)
    # phase4 fixer r2 major #4: a "TabardUV" panel-space UV layer (u across
    # the width, v down the hang) — Mat_Tabard draws the laurel EMBROIDERY
    # BORDER as texture in this space (stitched pattern, not piping cords).
    uvl = ob.data.uv_layers.new(name="TabardUV")
    for poly in ob.data.polygons:
        for lo in poly.loop_indices:
            vi = ob.data.loops[lo].vertex_index
            i, j = divmod(vi, NU)
            uvl.data[lo].uv = (j / (NU - 1), i / (NV - 1))
    sol = ob.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.0085
    apply_mods(ob)
    shade_smooth(ob)
    return ob, paths


def _leaf(name, p, d, alt, mat, s=0.019, bev=0.0048):
    """One tapered laurel-leaf cord at p, along direction d, tilted to the
    alt side (alternating leaves = a garland, not beads on a string)."""
    d = d.normalized()
    if abs(d.z) < 0.5:                          # horizontal run: tilt up/down
        dl = (d + Vector((0.0, 0.0, 0.55 * alt))).normalized()
    else:                                       # vertical run: tilt sideways
        perp = Vector((d.y, -d.x, 0.0))
        perp = perp.normalized() if perp.length > 1e-6 else Vector((1, 0, 0))
        dl = (d + perp * (0.55 * alt)).normalized()
    pts = [(p - dl * (s * 0.9), 0.20), (p - dl * (s * 0.25), 0.95),
           (p + dl * (s * 0.35), 0.80), (p + dl * s, 0.10)]
    return curve_obj(name, [pts], bev, mat)


def _embroider(tag, paths, mat_gold):
    """Gold laurel embroidery for one panel: border cords on the true edges
    (L0/R0/hem0), a finer meandering vine + alternating leaf cords riding
    the inset paths (L1/R1/hem1). Everything sits ON the cloth (the inset
    paths are real panel vertices), so nothing floats.

    phase4 fixer r2 major #4 ("rope-like piping cords, not embroidery"):
    the physical vine + leaf cords are GONE — the laurel motif is now a
    TEXTURE band drawn by Mat_Tabard in the panel's TabardUV space (real
    stitched-pattern read). Only ONE slim finished-edge cord remains on
    the true panel edges so the cloth border reads bound, not raw."""
    def _out(p):
        d = Vector((p.x, p.y - 0.07, 0.0))
        if d.length < 1e-5:
            return p.copy()
        return p + d.normalized() * 0.0028
    out = []
    for key in ("L0", "R0", "hem0"):
        pts = paths[key]
        if len(pts) < 4:
            continue
        out.append(curve_obj(f"_embr_{tag}_{key}",
                             [[(_out(p), 1.0) for p in pts]], 0.0030,
                             mat_gold))
    return out


def build_tabard(mat_cloth, mat_gold, body):
    """The integrated blue: front surcoat + side/back trailing panels off
    the waist belt, a blue underlayer band beneath the gold underskirt hem,
    gold laurel embroidery on every edge. Replaces the deleted back cape."""
    parts = []

    # -- FRONT tabard/surcoat panel: the primary blue element ---------------
    # phase4 fixer r1 minor #7 ("blue wraps so much it drifts toward a
    # skirt/robe read"): front panel NARROWED (0.30/0.42 -> 0.24/0.30) and
    # side panels narrowed + pushed further to the sides so the engraved
    # cuisses/greaves read clearly between the blue panels at Cam_Full.
    front, fp = _hang_panel("_tabard_front", body, mat_cloth,
                            a_c=math.pi, w_top=0.24, w_hem=0.30,
                            z_top=2.005, z_hem=0.055,
                            clr_top=0.030, clr_body=0.075,
                            seed_ph=0.7, toe_flare=0.028)
    parts.append(front)
    parts += _embroider("F", fp, mat_gold)

    # -- narrow side panels: trail from the hips between the tassets --------
    for tag, a_c, ph in (("SL", math.pi + 1.48, 2.3),
                         ("SR", math.pi - 1.48, 4.1)):
        pan, pp = _hang_panel(f"_tabard_{tag}", body, mat_cloth,
                              a_c=a_c, w_top=0.12, w_hem=0.16,
                              z_top=1.995, z_hem=0.14,
                              clr_top=0.028, clr_body=0.072,
                              seed_ph=ph, toe_flare=0.008, span_half=0.28)
        parts.append(pan)
        parts += _embroider(tag, pp, mat_gold)

    # -- trailing back panel: hangs from the BELT (not the shoulders — this
    # is a surcoat tail, deliberately narrower than the armored back) -------
    back, bp = _hang_panel("_tabard_back", body, mat_cloth,
                           a_c=0.0, w_top=0.22, w_hem=0.28,
                           z_top=1.990, z_hem=0.045,
                           seed_ph=5.2, toe_flare=0.022, hem_drop=0.012,
                           clr_top=0.028, clr_body=0.072)
    parts.append(back)
    parts += _embroider("B", bp, mat_gold)

    # -- blue UNDERLAYER band: cloth showing beneath the gold underskirt hem
    # (z 1.215) and between the hanging tassets — the "blue between the
    # plates" accent. Sits INSIDE the gold drum above the hem (clr 0.0145 <
    # 0.019), flares below it, fluted + scalloped like hanging cloth. ------
    NSF = 96
    rings = []
    uz_rows = (1.30, 1.24, 1.18, 1.12, 1.06, 1.02)
    for i, uz in enumerate(uz_rows):
        t = i / (len(uz_rows) - 1)
        cy, rad = body_radial(body, uz, NSF)
        ring = []
        for j in range(NSF):
            a = 2 * math.pi * j / NSF
            r = rad[j] + 0.0145 + 0.011 * max(0.0, t - 0.35) \
                + 0.006 * (t ** 1.5) * math.sin(12 * a + 0.7)
            zj = uz
            if i == len(uz_rows) - 1:
                zj -= 0.018 * (0.5 + 0.5 * math.sin(12 * a + 0.7))
            ring.append(Vector((r * math.sin(a), cy + r * math.cos(a), zj)))
        rings.append(ring)
    ul = loft_band("_underlayer_blue", rings, mat_cloth, thickness=0.005)
    # p4 r2: park the underlayer at panel-centre UV so Mat_Tabard's
    # embroidery border band (drawn near u/v edges) never touches it
    uvl = ul.data.uv_layers.new(name="TabardUV")
    for lo in range(len(ul.data.loops)):
        uvl.data[lo].uv = (0.5, 0.5)
    parts.append(ul)

    ob = join(parts, "Godwyn_Tabard")
    # slot-name contract with 03_materials (same idea as Godwyn_Hair): the
    # join mixes blue cloth + gold embroidery slots; 03 replaces IN-SLOT.
    ob["godwyn_slot_names"] = [m.name if m else "" for m in
                               ob.data.materials]
    print(f"[02_details] Godwyn_Tabard slots: {list(ob['godwyn_slot_names'])}")
    return ob





# ---------------------------------------------------------------------------
# HAIR
# ---------------------------------------------------------------------------

def build_hair(mat_hair, mat_gold, body, eye_data=None, mat_hairdeep=None):
    """
    Layered hair rooted on the REAL MPFB2 'scalp' vertex group (blocker #1):
      - thin under-layer duplicated from the scalp faces themselves (follows
        the skull exactly, natural irregular hairline, no helmet brim),
      - ~150 tapered strand clumps rooted at scalp verts, hugging the skull
        then flowing down the back past the shoulder blades,
      - two plaited braids that EMERGE from temple scalp points and lie
        against the body (right: front of shoulder; left: down the back).
    No strand crosses in front of the face.
    """
    parts = []
    HC = HEAD_C
    me = body.data

    scalp_idx = sorted(_group_verts(body, "scalp"))
    scalp = [(me.vertices[i].co.copy(), me.vertices[i].normal.copy())
             for i in scalp_idx]
    assert scalp, "scalp vertex group empty — cannot root hair"
    print(f"[02_details] hair roots available: {len(scalp)} scalp verts")

    # -- under-layer: scalp faces offset along their normals -----------------------
    scalp_set = set(scalp_idx)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    keep_faces = [f for f in bm.faces
                  if all(v.index in scalp_set for v in f.verts)]
    doomed = [f for f in bm.faces if f not in set(keep_faces)]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.normal_update()
    # fixer r2 blocker #3 ("solid plastic helmet shell"): the cap is now a
    # COMBED SHADOW LAYER, not the visible hair surface — subdivided once,
    # displaced with irregular front-to-back comb ridges (so any exposed
    # sliver reads as strand mass), and shaded with the DARKER under-hair
    # material so gaps between locks read as shadow depth, never plastic.
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                              use_grid_fill=True)
    bm.normal_update()
    # RE-OUTFIT fixer r3 blocker #1 ("chunky ridged cap = sculpted clay"):
    # ridge amplitude cut ~55% — the cap is a barely-displaced SHADOW layer
    # now; the visible hair surface is the dense strand pass below.
    # fixer r4 blocker #7 ("cross-hatch scratches on the crown"): the sine
    # ridge displacement WAS the crosshatch — amplitude cut to near-zero;
    # the dense root-tuft pass below is the visible crown surface now.
    for v in bm.verts:
        ridge = math.sin(v.co.x * 260.0 + v.co.y * 40.0)
        v.co = v.co + v.normal * (0.0012 + 0.0003 * ridge)
    cme = bpy.data.meshes.new("_haircap")
    bm.to_mesh(cme)
    bm.free()
    cap = bpy.data.objects.new("_haircap", cme)
    link_obj(cap)
    cme.materials.append(mat_hairdeep or mat_hair)
    sol = cap.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.007
    apply_mods(cap)
    shade_smooth(cap)
    parts.append(cap)

    # -- strand clumps: skull-hugging, flowing down the back -----------------------
    def outside_skull(p, margin):
        """Push p outside the skull ellipsoid by margin."""
        rx, ry, rz = 0.180, 0.225, 0.214   # r3: tracks the 1.06x head scale
        rel = p - HC
        e = Vector((rel.x / rx, rel.y / ry, rel.z / rz))
        if e.length < 1e-6:
            return p
        scale = max(e.length, 1.0 + margin)
        return HC + Vector((e.normalized().x * rx, e.normalized().y * ry,
                            e.normalized().z * rz)) * scale

    # More, finer strands (major #4: rope-noodle read) — bevel radius halved,
    # strand count doubled, skull margin cut so front strands lie flat against
    # the crown instead of arcing into a laurel-wreath silhouette.
    # r4 major #4: strands must HUG the skull (margin 0.015 -> 0.005 killed
    # the padded-roll silhouette), vary in width AND length, and part away
    # from a visible centre parting line.
    # MESO PASS (clumping + flow): the r4 300 uniform strands read as stringy
    # noodles. Hair now grows as ~55 LOCKS — one guide path per lock, 3-5
    # sub-strands hugging each guide with per-lock width, length jitter and a
    # lateral flow wave that grows toward the tips (S-flow, not straight rope).
    # p5r1 blocker #2 ("ropes/dreadlocks"): more locks for full scalp
    # coverage, wider per-lock radius spread + deeper per-sub radius jitter
    # so neighbouring locks OVERLAP at differing diameters (clumped hair,
    # not uniform tubes), and a harder taper to a near-point tip.
    # p5r2 major #4 ("spaghetti ropes"): strands split into THREE WIDTH
    # CLASSES (thin filler / mid / thick clump ribbons) so overlapping locks
    # read at differing diameters, roots pushed OUTWARD (margin 0.010 —
    # nothing intersects the temple/face), harder taper to a point.
    # p5b fixer r3 blocker #2 ("rope noodles over a bald cap"): lock count
    # +60% for full scalp coverage (no smooth crown), harder taper profile.
    # RE-OUTFIT fixer r3 blocker #1 ("sculpted clay / sparse noodles"):
    # lock count +50% (150 -> 225) and every width class THINNED (the 13.5mm
    # thick tubes were the visible noodles) — many thin overlapping locks.
    # fixer r4 blocker #7 ("smooth clay ribbons"): MORE locks, every width
    # class thinned again, harder tip taper — silhouette breaks into strands.
    # fixer r5 blocker #7 ("clay ribbons / dreadlock cords"): 2.1x lock
    # count at ~1/3 the width per class, harder tip taper, deeper clump
    # jitter — the silhouette must break into STRANDS of hair.
    # phase4 fixer r1 blocker #2 ("smooth clay/plastic ribbons"): MORE locks
    # at thinner widths, WIDER length variation (some locks stop at the
    # shoulder blades, some fall to the waist) so the silhouette breaks up
    # root-to-tip instead of reading as one shell of ropes.
    # phase4 fixer r2 blocker #2 ("thin wiry strands over a visible scalp
    # shell"): INVERTED strategy — FEWER, MUCH THICKER clumped locks
    # (bevel 3-6mm, tight clump radius) that overlap into a closed hair
    # mass with full scalp coverage; the wiry 1-2mm strands were reading
    # as a black wire net over a bald cap.
    # phase4 fixer r3 blocker #2 ("uniform blunt bob"): locks now draw their
    # end heights from a WIDE layered distribution (some stop at the
    # shoulder blades, some fall to the waist) and each lock carries its own
    # curvature so the silhouette breaks into layered hair, not one shell.
    # phase4 fixer r4 blocker #2 ("clay-strand wig: uniform stringy ribbons,
    # straight strings, visible scalp"): (a) MORE locks (260 -> 320) so the
    # fringe/part close over the cap; (b) WIDTH classes spread apart — broad
    # clump ribbons (8.5mm) plus thin breakaway strands (2.6mm) instead of
    # near-uniform 3-6mm cords; (c) each sub-strand is RESAMPLED to 9 points
    # with TWO-frequency lateral wave + depth wave that grow along the
    # length, so locks undulate and wave instead of hanging as straight
    # dreadlock strings.
    def _sample_guide(guide, t):
        ft = t * (len(guide) - 1)
        i = min(int(ft), len(guide) - 2)
        return guide[i].lerp(guide[i + 1], ft - i)

    # p4 r5 blocker #2 ("clay-rope/dreadlock wig — visible individual rope
    # profiles"): the 8.5mm thick class WAS the visible rope. All width
    # classes pulled toward each other and DOWN (2.2/3.8/5.6mm) with MORE
    # locks + deeper wave amplitudes, so the mass reads as blended sheets of
    # hair with thin breakaways, not countable tubes.
    strands_thin, strands_mid, strands_thick = [], [], []
    n_locks = 380
    step = max(1, len(scalp) // n_locks)
    part_sgn = 1.0
    n_subs_total = 0
    for k in range(0, len(scalp), step):
        root, n = scalp[k]
        # comb away from the centre parting (crown verts near x=0 flip a coin)
        if abs(root.x) > 0.012:
            part_dir = math.copysign(1.0, root.x)
        else:
            part_dir = part_sgn = -part_sgn
        sway = part_dir * random.uniform(0.015, 0.09)
        # layered length classes: 25% short (nape), 50% mid, 25% long
        u_len = random.random()
        if u_len < 0.25:
            end_z = random.uniform(2.05, 2.35)
        elif u_len < 0.75:
            end_z = random.uniform(1.45, 2.05)
        else:
            end_z = random.uniform(0.95, 1.45)
        lock_r = random.uniform(0.006, 0.019)      # p4 r4: WIDE clump spread
        wave_a = random.uniform(0.020, 0.055)      # p4 r5: deeper S-flow
        wave_p = random.uniform(0.0, 2 * math.pi)
        wave_a2 = random.uniform(0.008, 0.020)     # p4 r5: stronger curl
        wave_p2 = random.uniform(0.0, 2 * math.pi)
        p0 = root - n * 0.004     # roots SUBMERGED below the scalp
        # guide: slide along the skull toward the nape, hugging it but with
        # a clear clearance margin (p5r2: temple/face clipping)
        nape = Vector((root.x * 0.55 + sway * 0.3, 0.30, 2.82))
        guide = [p0,
                 outside_skull(p0.lerp(nape, 0.45), 0.010),
                 outside_skull(Vector((root.x * 0.45 + sway * 0.5, 0.40, 2.58)),
                               0.008),
                 Vector((root.x * 0.35 + sway, 0.46 + random.uniform(0, 0.04),
                         (2.5 + end_z) / 2)),
                 Vector((root.x * 0.28 + sway * 1.5,
                         0.44 + random.uniform(0, 0.07), end_z))]
        rad_profile = ((0.9, 1.05, 0.90, 0.45, 0.012))
        bucket = (strands_thin if lock_r < 0.0095
                  else strands_mid if lock_r < 0.0145 else strands_thick)
        for _ in range(random.randint(3, 5)):
            ang = random.uniform(0.0, 2 * math.pi)
            rr = lock_r * random.uniform(0.15, 1.0)
            off = Vector((math.cos(ang) * rr, math.sin(ang) * rr * 0.6, 0.0))
            r = random.uniform(0.35, 1.15)         # deeper diameter jitter
            tipz = end_z + random.uniform(-0.10, 0.06)
            ph_j = random.uniform(-0.6, 0.6)       # per-sub phase jitter
            pts = []
            n_samp = 9
            for gi in range(n_samp):
                t = gi / (n_samp - 1.0)
                gp = _sample_guide(guide, t)
                # radius profile interpolated over the original 5-knot curve
                fr = t * 4.0
                ri = min(int(fr), 3)
                rad = (rad_profile[ri]
                       + (rad_profile[ri + 1] - rad_profile[ri]) * (fr - ri))
                # two-frequency wave: broad S-flow + finer curl, both growing
                # toward the tips, in x AND depth (y)
                wav = (math.sin(t * math.pi * 2.2 + wave_p + ph_j) * wave_a
                       + math.sin(t * math.pi * 5.3 + wave_p2) * wave_a2) * t
                wav_y = math.sin(t * math.pi * 3.7 + wave_p2 + ph_j) \
                    * wave_a2 * 0.9 * t
                p = gp + off * (0.15 + 0.85 * t) + Vector((wav, wav_y, 0.0))
                if gi == n_samp - 1:
                    p = Vector((p.x, p.y, tipz))
                pts.append((p, rad * r))
            bucket.append(pts)
            n_subs_total += 1
    for sname, slist, bev in (("_strands_thin", strands_thin, 0.0022),
                              ("_strands_mid", strands_mid, 0.0038),
                              ("_strands_thick", strands_thick, 0.0056)):
        if slist:
            parts.append(curve_obj(sname, slist, bev, mat_hair, resolution=8))
    print(f"[02_details] back hair: {n_subs_total} strands in ~{n_locks} "
          f"locks, 3 width classes ({len(strands_thin)}/{len(strands_mid)}/"
          f"{len(strands_thick)})")

    # -- SPARSE FLYAWAYS (phase4 fixer r3 blocker #2): the r2 0.7mm loops
    # were deleted as black wire tangles; a SMALL number of 1.8mm arcs
    # (thick enough to catch light) now lift off the crown/back mass so the
    # silhouette reads as hair, not a carved shell.
    flyaways = []
    fly_src = [scalp[k] for k in range(0, len(scalp),
                                       max(1, len(scalp) // 36))]
    for root, n in fly_src:
        if n.z > 0.72:
            continue      # crown-top flyaways rendered as antennae spikes
        sway_f = math.copysign(1.0, root.x if abs(root.x) > 0.01
                               else random.uniform(-1, 1))
        lift = random.uniform(0.010, 0.026)
        p0 = root - n * 0.002
        m1 = p0 + n * lift + Vector((sway_f * 0.01, 0.02, 0.01))
        m2 = p0 + n * lift * 0.7 + Vector((sway_f * random.uniform(0.02, 0.05),
                                           random.uniform(0.05, 0.12),
                                           random.uniform(-0.10, -0.02)))
        flyaways.append([(p0, 0.8), (m1, 0.6), (m2, 0.08)])
    if flyaways:
        parts.append(curve_obj("_flyaways", flyaways, 0.0018, mat_hair,
                               resolution=6))
        print(f"[02_details] sparse flyaways: {len(flyaways)}")

    # -- TEMPLE FALLS (phase4 fixer r2 blockers #1+#2): thick clumped locks
    # rooted at the temple/side hairline that fall STRAIGHT DOWN framing
    # the face (outside the face silhouette — |x| >= 0.105 at every control
    # point) to the jaw/shoulder. They close the bare temple gap AND shrink
    # the enormous-forehead read, like the approved concept's side falls.
    # phase4 fixer r3 blocker #2 ("sides fall as a uniform blunt bob that
    # hugs the jaw like a helmet"): temple falls now vary WIDELY in length
    # (jaw / shoulder / chest classes), curvature and sweep — some locks
    # bow outward mid-fall, some sweep back toward the mass — so the side
    # silhouette breaks into layered locks instead of a helmet bob.
    temple = []
    y_mid = sum(co.y for co, _ in scalp) / len(scalp)
    side_roots = [(co, n) for co, n in scalp
                  if abs(co.x) > 0.095 and co.y < y_mid + 0.02]
    for root, n in side_roots:
        sgn_t = math.copysign(1.0, root.x)
        for _ in range(3):    # p4 r4: denser side coverage
            xw = max(abs(root.x) + random.uniform(0.010, 0.030), 0.105)
            u_len = random.random()
            if u_len < 0.35:
                end_z = random.uniform(2.42, 2.62)     # jaw-length layer
            elif u_len < 0.80:
                end_z = random.uniform(2.18, 2.42)     # shoulder layer
            else:
                end_z = random.uniform(1.95, 2.18)     # chest-length lock
            bow = random.uniform(-0.012, 0.030)        # mid-fall curvature
            sweep = random.uniform(0.0, 0.06)          # backward sweep
            p0 = root - n * 0.003
            m1 = Vector((sgn_t * (xw + 0.020),
                         root.y + random.uniform(0.00, 0.03),
                         root.z - 0.055))
            m2 = Vector((sgn_t * (xw + 0.012 + bow),
                         root.y + random.uniform(0.03, 0.07) + sweep * 0.6,
                         (root.z - 0.05 + end_z) * 0.5))
            m3 = Vector((sgn_t * (xw + bow * 0.4),
                         root.y + random.uniform(0.05, 0.10) + sweep,
                         end_z))
            r = random.uniform(0.6, 1.1)
            temple.append([(p0, 0.9 * r), (m1, 1.0 * r), (m2, 0.8 * r),
                           (m3, 0.10)])
    if temple:
        # p4 r5 blocker #2: temple-fall ropes thinned 4.2 -> 3.2mm
        parts.append(curve_obj("_templefalls", temple, 0.0032, mat_hair,
                               resolution=8))
        print(f"[02_details] temple falls: {len(temple)} locks over "
              f"{len(side_roots)} side roots")

    # -- ROOT TUFTS (p5r2 major #4): short directional clumps across the whole
    # scalp so the cap solidify seam never reads as a bald ridge on top.
    # p5b r3 blocker #2: EVERY scalp vert roots a tuft (step 2 -> 1) and the
    # tufts are longer/thicker — the crown must read as combed hair mass,
    # never a smooth cap.
    # r5: TWO finer tufts per scalp vert (half width, double density) — the
    # crown must read as individual combed strands, not clay ridges
    tufts = []
    for k in range(0, len(scalp), 1):
        root, n = scalp[k]
        for _ in range(2):
            part_dir = math.copysign(1.0, root.x) if abs(root.x) > 0.010 \
                else random.choice((-1.0, 1.0))
            sway = part_dir * random.uniform(0.012, 0.034)
            p0 = root - n * 0.002
            m1 = outside_skull(Vector((root.x + sway * 0.5, root.y + 0.045,
                                       root.z - 0.006)), 0.005)
            m2 = outside_skull(Vector((root.x + sway, root.y + 0.100,
                                       root.z - 0.024)), 0.006)
            r = random.uniform(0.5, 1.1)
            tufts.append([(p0, 0.9 * r), (m1, 0.8 * r), (m2, 0.10 * r)])
    # p4 r2 blocker #2: tufts THICKENED 2.1 -> 3.4mm — the crown surface
    # must close over the cap (no smooth shell visible between strands)
    # p4 r5 blocker #2: back down to 2.6mm — the fat tufts were part of
    # the clay-rope crown read; density (2 per vert) keeps the cap closed
    parts.append(curve_obj("_roottufts", tufts, 0.0026, mat_hair,
                           resolution=6))
    print(f"[02_details] root tufts: {len(tufts)} (cap seam cover)")

    # -- FRINGE (r3 major #3): irregular parted strands over the hairline ------
    # The bare cap edge read as a bald-cap band across the forehead. Root a
    # row of short strands at the FRONT scalp verts and sweep them back over
    # the crown with random parting so the hairline reads as combed hair.
    y_front = min(co.y for co, _ in scalp)
    front_row = [(co, n) for co, n in scalp if co.y < y_front + 0.045]

    # -- HAIRLINE FORWARD (phase4 fixer r3 blocker #1: "hairline sits far
    # too high leaving a huge bare forehead"): synthesize a NEW row of
    # hairline roots 25-30mm FORWARD-AND-DOWN of the scalp group's front
    # edge, seated on the skull ellipsoid. The advance is strongest at the
    # centre of the forehead and fades to ZERO at the temples (|x|>~0.075),
    # leaving a natural masculine TEMPLE RECESSION on each side.
    hairline_roots = []
    for root, n in front_row:
        ax = abs(root.x)
        centre_f = max(0.0, 1.0 - (ax / 0.075) ** 2)   # 1 centre .. 0 temple
        if centre_f <= 0.05:
            continue
        adv = 0.028 * centre_f                          # up to 28mm forward
        p = Vector((root.x, root.y - adv, root.z - adv * 0.55))
        p = outside_skull(p, 0.001)                     # seat on the skull
        hairline_roots.append((p, n))
    print(f"[02_details] hairline advanced: {len(hairline_roots)} new roots "
          f"(max +28mm centre, temple recession preserved)")
    # r4 major #4: the r3 fringe arced UP over the crown (z +0.022 with a
    # 7-9mm skull margin) and read as a padded roll / wig headband. Strands
    # now lie FLAT against the skull (margin ~3mm, no upward arc) and comb
    # laterally away from a centre parting.
    # p4 r5 blocker #2 ("cap-like fringe hugging the forehead / helmet
    # edge"): FEWER, FINER fringe strands with varied sweep length and a
    # ragged length jitter so the hairline reads as a skin-to-hair
    # transition (individual combed hairs), never a solid cap edge.
    fringe = []
    for root, n in front_row + hairline_roots:
        for _ in range(3):
            part_dir = math.copysign(1.0, root.x) if abs(root.x) > 0.010 \
                else random.choice((-1.0, 1.0))
            sway = part_dir * random.uniform(0.012, 0.044)
            r = random.uniform(0.35, 1.0)
            sweep = random.uniform(0.14, 0.30)     # varied comb-back length
            p0 = root - n * 0.003
            mid = outside_skull(
                Vector((root.x * 0.9 + sway, root.y + sweep * 0.42,
                        root.z + 0.004)), 0.003)
            back = outside_skull(
                Vector((root.x * 0.7 + sway * 2.0, root.y + sweep,
                        root.z - 0.006)), 0.004)
            fringe.append([(p0, 0.85 * r), (mid, 1.0 * r), (back, 0.40 * r)])
    if fringe:
        # p4 r5: fringe bevel 3.2 -> 2.1mm (fine hairline, not a helmet rim)
        parts.append(curve_obj("_fringe", fringe, 0.0021, mat_hair,
                               resolution=8))
        print(f"[02_details] hairline fringe: {len(fringe)} strands over "
              f"{len(front_row)} front roots")

    # -- FRONT FALLS: DELETED (fixer r4 blocker #7). Three rounds running,
    # the fall clumps produced stray "noodle" strands dangling across the
    # face/jaw on camera (r2 scribbles, r3 chin noodles, r4 jaw noodles).
    # The braid + the dense back-hair mass carry the design; nothing may
    # hang in front of the gorget/face volume.

    # -- braids: 3-strand helix, rooted at temple scalp points ----------------------
    # phase4 fixer r2 blocker #2 ("braid reads as wicker rope"): the helix
    # radius now sits BELOW the strand radius so the three plait strands
    # visibly MERGE into one another (smooth interleaved lobes, not three
    # separated wicker tubes); denser sampling + slower twist.
    def braid(name, path, rad_helix, rad_strand):
        n = 56

        def sample(t):
            ft = t * (len(path) - 1)
            i = min(int(ft), len(path) - 2)
            return path[i].lerp(path[i + 1], ft - i)

        splines = []
        for ph in range(3):
            pts = []
            for i in range(n):
                t = i / (n - 1)
                c = sample(t)
                tang = sample(min(t + 0.03, 1.0)) - c
                if tang.length < 1e-6:
                    tang = Vector((0, 0, -1))
                tang.normalize()
                side = tang.cross(Vector((0, 1, 0)))
                if side.length < 1e-6:
                    side = Vector((1, 0, 0))
                side.normalize()
                up = tang.cross(side).normalized()
                # r4 major #4: more twists + wider helix vs strand radius so
                # the alternating plait lobes read at full-body distance
                a = 2 * math.pi * (ph / 3.0) + t * math.pi * 5.0
                off = side * math.cos(a) * rad_helix + up * math.sin(a) * rad_helix
                pts.append((c + off, 1.0 - 0.65 * t))
            splines.append(pts)
        return curve_obj(name, splines, rad_strand, mat_hair, resolution=10)

    # ONE asymmetric side braid (r3 major #3: it hid behind the shoulder and
    # never read on camera). Thicker plait, rooted above the RIGHT temple,
    # sweeping over the ear then falling down the FRONT of the right shoulder
    # onto the chest — clearly visible in the full and face frames.
    # p5r1 blocker #2: the braid used to run far down the chest and stuck
    # out rigidly in the deform test. It now sweeps over the ear and ends
    # at the shoulder/clavicle pocket, blending into the front falls.
    # p5r2 major #4: braid THICKER + pulled clear of the temple so the plait
    # lobes actually read on Cam_Face/Cam_Full (the r4 braid vanished into
    # the falls).
    # phase4 fixer r3 blocker #2 ("no braids read at all"): TEMPLE BRAIDS,
    # one per side, rooted at the temple hairline and SWEPT BACK over the
    # ear into the back-hair mass (the spec's partially-braided look). The
    # helix radius is raised back toward the strand radius (0.85x) so the
    # three plait strands read as interleaved lobes instead of merging
    # into one smooth rope.
    # phase4 fixer r4 blocker #2 ("the braids do not read at all from
    # Cam_Face"): the temple braids now fall FORWARD — down the side of the
    # face in front of the ear, hanging at the jaw/neck line and ending at
    # the clavicle with a gold tie bead. Every control point stays outside
    # the face silhouette (|x| >= 0.145 through the face band) and clear of
    # the cheek (y <= -0.02 at jaw height), like the classic FromSoft
    # temple-plait framing the face.
    root_r = max(scalp, key=lambda cn: cn[0].x)[0]
    braid_r = braid("_braidR",
                    [root_r,
                     Vector((root_r.x * 1.05, root_r.y - 0.02, root_r.z - 0.01)),
                     Vector((0.195, 0.02, 2.96)),        # over the temple
                     Vector((0.175, -0.035, 2.88)),      # front of the ear
                     Vector((0.158, -0.060, 2.74)),      # jaw/neck line
                     Vector((0.150, -0.055, 2.64))],     # to the collarbone
                    0.0118, 0.0138)  # p4 r3: readable plait lobes
    parts.append(braid_r)
    # gold tie bead where the braid ends at the clavicle
    parts.append(uv_sphere("_braidTie", Vector((0.150, -0.055, 2.633)),
                           (0.026, 0.026, 0.021), mat_gold))
    root_l = min(scalp, key=lambda cn: cn[0].x)[0]
    braid_l = braid("_braidL",
                    [root_l,
                     Vector((root_l.x * 1.05, root_l.y - 0.02, root_l.z - 0.01)),
                     Vector((-0.195, 0.02, 2.96)),
                     Vector((-0.175, -0.035, 2.87)),
                     Vector((-0.158, -0.060, 2.72)),
                     Vector((-0.150, -0.055, 2.62))],
                    0.0118, 0.0138)
    parts.append(braid_l)
    parts.append(uv_sphere("_braidTieL", Vector((-0.150, -0.055, 2.613)),
                           (0.026, 0.026, 0.021), mat_gold))

    # -- BACK BRAID (p5b fixer r3 blocker #2): a THICK 3-strand plait down
    # the centre of the back so the spec's "partial braid" actually reads.
    # Rooted at the crown-back scalp, riding over the back-hair mass.
    root_b = max(scalp, key=lambda cn: cn[0].y)[0]
    braid_b = braid("_braidBack",
                    [root_b,
                     Vector((root_b.x * 0.6, root_b.y + 0.10, root_b.z - 0.06)),
                     Vector((0.020, 0.46, 2.72)),
                     Vector((0.030, 0.52, 2.45)),
                     Vector((0.045, 0.54, 2.15)),
                     Vector((0.050, 0.50, 1.85)),
                     Vector((0.040, 0.45, 1.55))],
                    0.0155, 0.0185)   # p4 r3: readable plait lobes
    parts.append(braid_b)
    parts.append(uv_sphere("_braidTieB", Vector((0.040, 0.45, 1.545)),
                           (0.034, 0.034, 0.026), mat_gold))

    # -- EYEBROWS (p5r1 blocker #1): real brow geometry ------------------------
    # Thin lofted brow strands riding the sculpted brow ridge, joined into
    # Godwyn_Hair (head-parented by 04 — deforms with the skull). Each brow
    # is a fan of short tapered strands following an arched path.
    if eye_data:
        me_b = body.data
        face_verts = [v.co.copy() for v in me_b.vertices
                      if v.co.z > 2.80 and v.co.y < HEAD_C.y]

        def face_y(x, z, default=-0.05):
            best, bd = default, 1e9
            for co in face_verts:
                d = (co.x - x) ** 2 + (co.z - z) ** 2
                if d < bd:
                    bd, best = d, co.y
            return best

        # p5r2 blocker #3: brows rebuilt as TAPERED CLUMPED STRANDS lying ON
        # the ridge (not flat ribbons floating above the brow line). More,
        # shorter, overlapping strands; each hugs face_y with a 2mm offset;
        # inner strands angle up-out, outer strands sweep laterally (real
        # brow hair growth pattern); slight per-strand jitter for clumping.
        # p5b fixer r3 blocker #1: 13 thin strands read as sparse floating
        # scribbles. Rebuilt as a DENSE flat ribbon-clump fan (22 wider,
        # flatter strands per brow, tighter jitter, ~2mm shrinkwrap offset)
        # hugging the sculpted ridge — a solid masculine brow.
        # RE-OUTFIT fixer r3 blocker #1 ("patchy painted strips floating on
        # the brow"): TWO overlapping layers of much finer strands — a dense
        # 44-strand base fan hugging the ridge (1.5mm offset — ON the skin,
        # never floating) plus a 20-strand shorter top layer for volume at
        # the brow head. Thin bevel (0.0022) so individual hairs read instead
        # of flat ribbons.
        brows = []
        for c, r in eye_data:
            sgn = math.copysign(1.0, c.x) if abs(c.x) > 1e-4 else 1.0
            z_b = c.z + r * 1.40                 # ON the ridge, not above it
            # fixer r5 blocker #7 ("painted strip eyebrows"): denser fan of
            # FINER hairs that bow further proud of the skin — 3D tufts
            # phase4 fixer r3 blocker #1 ("brows are sparse painted
            # strokes"): a THIRD row joins the fan (groomed multi-row brow)
            # and the base row densifies.
            # p4 r5 blocker #1 ("flat painted-on brow strips"): the fan goes
            # FINER + DENSER — more hairs per layer at ~half the bevel below,
            # so the brow resolves as individual tapered hairs at Cam_Face.
            for layer, (n_s, l_fac, z_off) in enumerate(
                    ((120, 1.00, 0.0), (70, 0.62, 0.004),
                     (46, 0.40, 0.008))):
                for si in range(n_s):
                    t0 = si / (n_s - 1.0)        # 0=inner .. 1=outer root
                    jz = random.uniform(-0.0012, 0.0012)
                    jx = random.uniform(-0.0025, 0.0025) * r
                    # root along the brow arc
                    rx = c.x + sgn * (-0.25 + 1.55 * t0) * r + jx
                    rz = (z_b + 0.13 * math.sin(math.pi * t0) * r
                          - 0.04 * t0 * r + jz + z_off * r)
                    # growth: inner hairs angle up-out, outer sweep lateral
                    # p4 r2 blocker #1 ("sparse painted-on crossed brow
                    # strands"): jitter TIGHTENED — a groomed, coherent
                    # brow mass, not crossing scribbles.
                    ang = (1.0 - t0) * 0.50 + 0.08 \
                        + random.uniform(-0.025, 0.025)
                    length = r * (0.62 - 0.20 * abs(t0 - 0.35)) * l_fac \
                        * random.uniform(0.85, 1.12)   # p4 r4: ragged tips
                    pts = []
                    for pi_ in range(4):
                        tt = pi_ / 3.0
                        x = rx + sgn * math.cos(ang) * length * tt
                        z = rz + math.sin(ang) * length * tt * (1.0 - 0.5 * tt)
                        # fixer r4 blocker #7 ("flat painted-strip brows
                        # sitting ON the skin"): each hair ROOTS on the skin
                        # then BOWS proud of it mid-strand — a real 3D tuft
                        # with per-hair lift jitter, not a decal.
                        # phase4 fixer r4 blocker #1 ("thin painted-on
                        # eyebrows"): bow lift +70% + per-hair jitter — each
                        # tuft arcs clearly PROUD of the skin so the brow
                        # reads as 3D hair mass, never a decal strip.
                        # p4 r5 blocker #1: lift REDUCED — the 5mm proud bow
                        # rendered as a dark strip floating off the ridge;
                        # fine hairs now hug the brow bone.
                        lift = (0.0028 + random.uniform(0.0, 0.0012)) \
                            * math.sin(math.pi * min(tt * 1.25, 1.0))
                        y = face_y(x, z) - 0.0010 - lift
                        w = 1.0 - 0.82 * tt      # strong taper to the tip
                        pts.append((Vector((x, y, z)), max(w, 0.08)))
                    brows.append(pts)
        # fixer r2 blocker #3: brows shade with the DARKER hair material —
        # blonde strips at brow scale read as painted-on; a deeper tone
        # separates them from the skin and reads as real brow hair.
        # phase4 fixer r1 blocker #1 ("painted strip eyebrows"): bevel up
        # 0.0017 -> 0.0023 so each hair carries real volume + shadow.
        # p4 r3: bevel 0.0023 -> 0.0026 (fuller groomed brow mass)
        # p4 r5 blocker #1 ("painted strips"): bevel HALVED 0.0026 -> 0.0013
        # — with the denser fan above, the brow reads as fine hair geometry
        # along the ridge, never a flat decal strip.
        parts.append(curve_obj("_brows", brows, 0.0013,
                               mat_hairdeep or mat_hair, resolution=8))
        print(f"[02_details] eyebrows built: {len(brows)} strands over "
              f"{len(eye_data)} brow ridges")

    return join(parts, "Godwyn_Hair")


# ---------------------------------------------------------------------------
# SWORD (origin at the grip; local +Z = blade direction)
# ---------------------------------------------------------------------------

def build_sword(mat_gold, mat_blade, grip_point=None, grip_axis=None,
                palm_n=None):
    parts = []
    # grip: gold-wrapped cylinder with a waist
    gverts, gfaces = [], []
    seg = 20
    grings = [(-0.115, 0.031), (-0.06, 0.027), (0.0, 0.0255),
              (0.07, 0.027), (0.140, 0.031)]
    for (z, r) in grings:
        for j in range(seg):
            a = 2 * math.pi * j / seg
            gverts.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    for i in range(len(grings) - 1):
        for j in range(seg):
            a = i * seg + j
            b = i * seg + (j + 1) % seg
            gfaces.append((a, b, b + seg, a + seg))
    grip = mesh_obj("_grip", gverts, gfaces, mat_gold)
    shade_smooth(grip)
    parts.append(grip)
    # pommel: sphere + drop finial
    parts.append(uv_sphere("_pommel", Vector((0, 0, -0.150)),
                           (0.042, 0.042, 0.036), mat_gold))
    parts.append(uv_sphere("_finial", Vector((0, 0, -0.192)),
                           (0.016, 0.016, 0.024), mat_gold))
    # crossguard: swept quillons + filigree curls + centre bloc
    quill = []
    for s in (1, -1):
        quill.append([(Vector((0, 0, 0.152)), 1.0),
                      (Vector((s * 0.085, 0, 0.150)), 0.95),
                      (Vector((s * 0.165, 0, 0.168)), 0.8),
                      (Vector((s * 0.220, 0, 0.205)), 0.55)])
        quill.append([(Vector((s * 0.055, 0, 0.145)), 0.55),
                      (Vector((s * 0.095, 0, 0.118)), 0.5),
                      (Vector((s * 0.065, 0, 0.098)), 0.4),
                      (Vector((s * 0.040, 0, 0.118)), 0.3)])
    parts.append(curve_obj("_quillons", quill, 0.020, mat_gold))
    parts.append(uv_sphere("_guardbloc", Vector((0, 0, 0.152)),
                           (0.062, 0.030, 0.042), mat_gold))
    # blade: phase4 fixer r2 minor #7 ("needle-thin rapier read"). An
    # 8-point cross-section: full ~11cm width at the guard with a proper
    # distal taper, thicker spine, and a CENTRAL FULLER groove on both
    # flats (the mid points dip below the spine shoulders). The roll fix
    # in the placement below keeps the FLAT facing the camera so the
    # width actually reads.
    bl0, bl1 = 0.165, 1.72   # base z, tip z (blade ~1.55m)
    rings = 12
    bverts, bfaces = [], []
    NBS = 8
    for i in range(rings):
        t = i / (rings - 1)
        z = bl0 + (bl1 - bl0) * t
        w = 0.108 * ((1 - t) ** 0.72) + 0.010 * (1 - t)
        th = 0.019 * (1 - t) + 0.0042
        if i == rings - 1:
            w, th = 0.002, 0.002
        # 8 points: edge, fuller shoulder, spine dip (fuller), shoulder...
        bverts += [Vector((w / 2, 0, z)),
                   Vector((w * 0.24, th * 0.44, z)),
                   Vector((0, th * 0.30, z)),          # fuller dip
                   Vector((-w * 0.24, th * 0.44, z)),
                   Vector((-w / 2, 0, z)),
                   Vector((-w * 0.24, -th * 0.44, z)),
                   Vector((0, -th * 0.30, z)),         # fuller dip
                   Vector((w * 0.24, -th * 0.44, z))]
    for i in range(rings - 1):
        for j in range(NBS):
            a = i * NBS + j
            b = i * NBS + (j + 1) % NBS
            bfaces.append((a, b, b + NBS, a + NBS))
    bverts.append(Vector((0, 0, bl1 + 0.050)))          # point
    tipbase = (rings - 1) * NBS
    for j in range(NBS):
        bfaces.append((tipbase + j, tipbase + (j + 1) % NBS,
                       len(bverts) - 1))
    blade = mesh_obj("_blade", bverts, bfaces, mat_blade)
    shade_smooth(blade)
    parts.append(blade)

    sword = join(parts, "Godwyn_Sword")
    # origin is already at the grip centre (geometry authored around 0,0,0)

    # -- place ON the curled-finger grip axis, blade angled down-out ----------------
    if grip_point is None:
        grip_point = HAND_R + Vector((0.02, -0.02, 0.0))
        blade_dir = Vector((0.25, -0.33, -0.905)).normalized()
    else:
        blade_dir = Vector(grip_axis).normalized()
        if blade_dir.z > 0:            # blade points DOWN
            blade_dir = -blade_dir
        # bias down-out so the tip clears the leg/robe (effortless low hang)
        blade_dir = (blade_dir + Vector((0.30, -0.18, -0.55))).normalized()
    # phase4 fixer r2 minor #7: ROLL the blade about its axis so the wide
    # FLAT (local X) spans the world X/front plane — the old track-quat
    # roll showed the camera the 1.3cm edge, which read as a rapier.
    z_ax = blade_dir.normalized()
    x_ax = Vector((1.0, 0.0, 0.0)) - z_ax * z_ax.x
    if x_ax.length < 1e-5:
        x_ax = Vector((0.0, 0.0, 1.0)) - z_ax * z_ax.z
    x_ax.normalize()
    y_ax = z_ax.cross(x_ax).normalized()
    rot_m = Matrix((x_ax, y_ax, z_ax)).transposed()
    sword.rotation_euler = rot_m.to_euler()
    sword.location = grip_point
    # persist grip data so 04 can re-derive the POSED grip transform
    sword["grip_point"] = list(grip_point)
    sword["grip_axis"] = list(blade_dir)
    if palm_n is not None:
        sword["palm_normal"] = list(palm_n)
    return sword


# ---------------------------------------------------------------------------
# PREVIEW RENDERS
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# FACE EXPRESSION BLENDSHAPES (animatability invariant)
#
# MPFB2 face-unit expression targets, loaded as LIVE shape keys (value 0.0)
# on Godwyn_Body after all vertex sculpting is done. Targets are indexed
# against the full MPFB basemesh; 01_base_human stored each surviving vert's
# original index in the 'godwyn_orig_idx' int attribute, and the cumulative
# unit->mesh scale in body['godwyn_expr_scale']. These keys ship into the
# .blend/.glb so the face stays animatable (SPEC: neutral-sorrowful).
# ---------------------------------------------------------------------------

EXPR_UNIT_DIR_GLOBS = [
    "~/.config/blender/*/extensions/user_default/mpfb/data/targets/expression/units/caucasian",
]

# blendshape name -> [(face unit target file stem, weight), ...]
# p5r1 minor #9: BrowSorrow widened — inner-up PLUS whole-brow-up and a
# touch of upper-lid so the sorrow reads across brow + lid + forehead.
GODWYN_EXPRESSIONS = [
    ("Expr_BrowSorrow",    [("eyebrows-left-inner-up", 1.0),
                            ("eyebrows-right-inner-up", 1.0),
                            ("eyebrows-left-up", 0.55),
                            ("eyebrows-right-up", 0.55),
                            ("eye-left-opened-up", 0.30),
                            ("eye-right-opened-up", 0.30)]),
    ("Expr_BrowDown",      [("eyebrows-left-down", 1.0),
                            ("eyebrows-right-down", 1.0)]),
    ("Expr_EyeClose_L",    [("eye-left-closure", 1.0)]),
    ("Expr_EyeClose_R",    [("eye-right-closure", 1.0)]),
    ("Expr_MouthOpen",     [("mouth-open", 1.0),
                            ("mouth-parling", 0.4)]),
    ("Expr_MouthCornerUp", [("mouth-corner-puller", 0.8)]),
    ("Expr_MouthSorrow",   [("mouth-depression", 1.0),
                            ("mouth-retraction", 0.35)]),
]

# p5r1 minor #9: MPFB face units are authored for subtle human-scale FACS
# motion — on a 3.2m hero rendered at full-body distance a 0.7 drive moved
# the brow ~8.6mm and was unreadable. Amplify all expression deltas so a
# 0.6-0.7 drive produces a clearly visible expression in-game.
EXPR_GAIN = 3.2

HEAD_ENLARGE_FACTOR = 1.06  # keep in sync with enlarge_head() default


def _expr_unit_dir():
    import glob as _glob
    for pat in EXPR_UNIT_DIR_GLOBS:
        hits = sorted(_glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[0]
    raise FileNotFoundError("MPFB expression unit targets not found")


def _read_target_deltas(path):
    """Parse a .target(.gz) file -> {orig_index: Vector delta} in MakeHuman
    units, converted to Blender axes (file columns are X Z Y with -Y)."""
    import gzip
    opener = gzip.open if path.endswith(".gz") else open
    deltas = {}
    with opener(path, "rt") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith('"'):
                continue
            p = line.split()
            deltas[int(p[0])] = Vector((float(p[1]), -float(p[3]), float(p[2])))
    return deltas


def add_expression_blendshapes(body):
    me = body.data
    scale = body.get("godwyn_expr_scale")
    attr = me.attributes.get("godwyn_orig_idx")
    if scale is None or attr is None:
        print("[02_details] WARNING: expr scale/index attr missing — "
              "blendshapes skipped (re-run 01_base_human)", file=sys.stderr)
        return
    scale = float(scale) * HEAD_ENLARGE_FACTOR   # all units are face-local
    orig_to_cur = {attr.data[i].value: i for i in range(len(me.vertices))}

    unit_dir = _expr_unit_dir()

    # idempotent: drop any prior expression keys (pristine restore usually
    # already removed them, but be safe on partial reruns)
    if me.shape_keys:
        for kb in list(me.shape_keys.key_blocks):
            if kb.name.startswith("Expr_"):
                body.shape_key_remove(kb)
    if not me.shape_keys:
        body.shape_key_add(name="Basis", from_mix=False)

    for expr_name, units in GODWYN_EXPRESSIONS:
        kb = body.shape_key_add(name=expr_name, from_mix=False)
        kb.value = 0.0
        moved = 0
        for stem, w in units:
            path = os.path.join(unit_dir, stem + ".target.gz")
            if not os.path.exists(path):
                path = os.path.join(unit_dir, stem + ".target")
            if not os.path.exists(path):
                print(f"[02_details] WARNING: expr unit '{stem}' missing — "
                      "skipped", file=sys.stderr)
                continue
            for oi, d in _read_target_deltas(path).items():
                ci = orig_to_cur.get(oi)
                if ci is None:      # vert was a deleted helper — skip
                    continue
                kb.data[ci].co += d * (scale * w * EXPR_GAIN)
                moved += 1
        print(f"[02_details] blendshape {expr_name}: {moved} vert offsets")

    n_keys = len(me.shape_keys.key_blocks) - 1
    assert n_keys == len(GODWYN_EXPRESSIONS), "expression key count mismatch"
    print(f"[02_details] GATE: {n_keys} live face expression blendshapes")


def render_previews(scene):
    def add_light(name, energy, size, color, loc, rot):
        li = bpy.data.lights.new(name, "AREA")
        li.energy = energy
        li.size = size
        li.color = color
        ob = bpy.data.objects.new(name, li)
        ob.location = loc
        ob.rotation_euler = rot
        bpy.context.scene.collection.objects.link(ob)

    add_light("Preview_Key", 1800, 2.5, (1.0, 0.95, 0.85),
              (3.5, -4.5, 4.5), (math.radians(55), 0, math.radians(35)))
    add_light("Preview_Fill", 600, 4.0, (0.75, 0.85, 1.0),
              (-4.0, -3.0, 2.5), (math.radians(70), 0, math.radians(-50)))
    add_light("Preview_Rim", 1000, 2.0, (1.0, 0.92, 0.7),
              (0.5, 4.5, 4.0), (math.radians(-55), 0, math.radians(175)))

    if scene.world is None:
        scene.world = bpy.data.worlds.new("PreviewWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.035, 0.035, 0.04, 1.0)
        bg.inputs[1].default_value = 1.0

    cam_data = bpy.data.cameras.new("Preview_Cam")
    cam_data.lens = 85
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("Preview_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam

    def aim(target):
        d = Vector(target) - Vector(cam.location)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    shots = [
        ("front",  (0.0, -8.0, 1.7),  (0, 0, 1.62), 768, 1280),
        ("threeq", (5.0, -6.2, 2.0),  (0, 0, 1.62), 768, 1280),
        ("back",   (0.8, 8.0, 2.0),   (0, 0.2, 1.65), 768, 1280),
        ("lower",  (1.6, -4.4, 1.05), (0, 0.05, 1.00), 960, 960),
        ("bust",   (1.1, -2.7, 2.75), (0, 0.08, 2.45), 960, 960),
        ("sword",  (2.7, -2.4, 1.95), (1.10, -0.42, 1.60), 960, 960),
    ]
    fast = os.environ.get("GODWYN_FAST") == "1"
    if fast:
        shots = [sh for sh in shots
                 if sh[0] in ("front", "threeq", "lower", "bust")]
    for name, loc, target, rx, ry in shots:
        cam.location = loc
        aim(target)
        G.configure_cycles(scene, samples=40 if fast else 64,
                           resolution_x=rx,
                           resolution_y=ry, use_denoiser=True)
        assert scene.cycles.device == "GPU", "GPU not set — INV-2 violated"
        out = os.path.join(WIP_DIR, f"p2_{name}.png")
        G.render_to_path(out, scene)
        if not os.path.exists(out) or os.path.getsize(out) < 4096:
            print(f"[02_details] FATAL: bad render {out}", file=sys.stderr)
            sys.exit(1)
        print(f"[02_details] Preview OK: {out} ({os.path.getsize(out):,} bytes)")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[02_details] Phase 2 — armor, robe, hair, sword")
    print("=" * 60)

    bpy.ops.wm.open_mainfile(filepath=BLEND)
    gpu = G.enable_gpu()   # after file load (open resets scene settings)
    print(f"[02_details] GPU backend: {gpu}")
    assert "Godwyn_Body" in bpy.data.objects, "Godwyn_Body missing — run 01 first"
    body = bpy.data.objects["Godwyn_Body"]

    # -- idempotent: remove any prior phase-2+ objects / rigs / preview gear --------
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("Godwyn_Armor", "Godwyn_Robe", "Godwyn_Cape",
                               "Godwyn_Tabard", "Godwyn_Hair",
                               "Godwyn_Sword", "Godwyn_Eyes", "Godwyn_Armature",
                               "Godwyn_VoidCrack", "Preview_", "Beauty_",
                               "Light_", "Cam_", "_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    # strip any prior rig state off the body (rerun-after-04 safety)
    body.parent = None
    for mod in list(body.modifiers):
        body.modifiers.remove(mod)
    for mname in ("Mat_Gold", "Mat_Robe", "Mat_Cape", "Mat_Tabard",
                  "Mat_Hair",
                  "Mat_HairDeep", "Mat_Blade",
                  "Mat_SkinPreview", "Mat_ClayPreview",
                  "Mat_EyeSclera", "Mat_EyeIris", "Mat_EyePupil"):
        m = bpy.data.materials.get(mname)
        if m:
            bpy.data.materials.remove(m)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.lights,
                 bpy.data.cameras):
        for blk in list(coll):
            if blk.users == 0:
                coll.remove(blk)

    # -- materials (preview-grade; Phase 3 refines to full SPEC shading) ------------
    mat_gold = G.make_metallic_material("Mat_Gold", (0.82, 0.65, 0.15, 1.0),
                                        roughness=0.32)
    mat_tabard = G.make_diffuse_material("Mat_Tabard", (0.08, 0.12, 0.35, 1.0),
                                         roughness=0.85)
    mat_hair = G.make_diffuse_material("Mat_Hair", (0.60, 0.42, 0.13, 1.0),
                                       roughness=0.4)
    # fixer r2 blocker #3: darker under-hair/brow material — the haircap and
    # brows use this so scalp gaps read as shadow and brows read as hair.
    # 03_materials rebuilds "Mat_HairDeep" IN-SLOT (like the eye materials).
    mat_hairdeep = G.make_diffuse_material("Mat_HairDeep",
                                           (0.30, 0.20, 0.055, 1.0),
                                           roughness=0.55)
    mat_blade = G.make_metallic_material("Mat_Blade", (0.60, 0.66, 0.80, 1.0),
                                         roughness=0.18)
    mat_skin = G.make_diffuse_material("Mat_SkinPreview", (0.95, 0.90, 0.82, 1.0),
                                       roughness=0.6)
    # eye preview materials — slot ORDER (sclera/iris/pupil) is the contract
    # with 03_materials, which rebuilds these same names into the same slots
    mat_sclera = G.make_diffuse_material("Mat_EyeSclera", (0.90, 0.89, 0.86, 1.0),
                                         roughness=0.30)
    mat_iris = G.make_diffuse_material("Mat_EyeIris", (0.55, 0.36, 0.10, 1.0),
                                       roughness=0.25)
    mat_pupil = G.make_diffuse_material("Mat_EyePupil", (0.01, 0.009, 0.008, 1.0),
                                        roughness=0.15)
    # calm the fabric's specular wash so the deep blue reads under hard light
    try:
        pb = mat_tabard.node_tree.nodes["Principled BSDF"]
        pb.inputs["Specular IOR Level"].default_value = 0.03
        # damp the lib default sheen: on the new crisp pleat walls a 0.15
        # white sheen streaked edge-on valleys into slit-like highlights
        for sk in ("Sheen Weight", "Sheen"):
            if sk in pb.inputs:
                pb.inputs[sk].default_value = 0.04
                break
    except (KeyError, AttributeError):
        pass
    body.data.materials.clear()
    body.data.materials.append(mat_skin)

    # -- pristine-body stash: body-mesh edits (lids, finger curls) must NOT
    #    accumulate across reruns (INV-6). First run stashes an untouched
    #    copy; later runs restore vertex positions from it before editing.
    # (refine_face now DELETES the helper eyeballs, so vertex counts change:
    #  restore must swap the whole mesh datablock back, not just positions.)
    pristine = bpy.data.meshes.get("Godwyn_Body_Pristine")
    if pristine is not None:
        old = body.data
        body.data = pristine.copy()
        body.data.name = "Godwyn_Body_Mesh"
        if old.users == 0:
            bpy.data.meshes.remove(old)
        print("[02_details] body mesh restored from Godwyn_Body_Pristine (rerun)")
    else:
        pristine = body.data.copy()
        pristine.name = "Godwyn_Body_Pristine"
        pristine.use_fake_user = True
        print("[02_details] pristine body mesh stashed")

    # -- ARM STRETCH (fixer r4 blocker #8: stubby arms) -----------------------
    # +9% along-axis about each shoulder. Runs FIRST so every later sculpt/
    # armor/landmark pass sees the heroic proportions. Landmark globals are
    # transformed through the same function.
    global ELBOW_R, WRIST_R, HAND_R
    n_arm = 0
    for v in body.data.vertices:
        sgnx = 1.0 if v.co.x >= 0.0 else -1.0
        if sgnx * v.co.x < 0.44 or v.co.z > 2.66:
            continue                       # torso/shoulder mass stays put
        S = Vector((sgnx * _ARM_S.x, _ARM_S.y, _ARM_S.z))
        ax = Vector((sgnx * _ARM_AXIS.x, _ARM_AXIS.y, _ARM_AXIS.z))
        rel = v.co - S
        dax = rel.dot(ax)
        if dax <= 0.02 or (rel - ax * dax).length > 0.24:
            continue                       # not on the arm axis tube
        v.co = _arm_stretch(v.co)
        n_arm += 1
    ELBOW_R = _arm_stretch(ELBOW_R)
    WRIST_R = _arm_stretch(WRIST_R)
    HAND_R = _arm_stretch(HAND_R)
    body.data.update()
    print(f"[02_details] arm stretch x{ARM_K:.2f}: {n_arm} verts; "
          f"WRIST_R now ({WRIST_R.x:.3f},{WRIST_R.y:.3f},{WRIST_R.z:.3f})")

    # -- body refinements -----------------------------------------------------
    sculpt_torso(body)                    # p5r1 #5: BEFORE the sampler so the
    init_surface_sampler(body)            # filigree conforms to the new chest
    enlarge_head(body)                    # r3 minor #8: rebalance vs shoulders
    eye_data = refine_face(body)          # blockers #1/#3: eyes + lips/brow/ears

    # -- fixer r2 blocker #4: the hands read oversized/mitten-like. Scale
    # each hand ~13% toward its own centroid with a fade band at the wrist
    # (f=0 at the wrist boundary keeps the forearm seamless). Runs BEFORE
    # curl_fingers/build_armor so the grip + gauntlet shells follow.
    hx0 = 0.795 + _HAND_SH.x               # fixer r4: thresholds follow the
    hz0 = 2.12 + _HAND_SH.z                # rigidly-translated hand
    for sgn in (1.0, -1.0):
        hand_v = [v for v in body.data.vertices
                  if sgn * v.co.x > 0.86 + _HAND_SH.x and v.co.z < hz0]
        if not hand_v:
            continue
        cen = Vector()
        for v in hand_v:
            cen += v.co
        cen /= len(hand_v)
        n_scaled = 0
        for v in body.data.vertices:
            if sgn * v.co.x > hx0 and v.co.z < hz0 + 0.02:
                f = min(1.0, (sgn * v.co.x - hx0) / 0.065)
                # fixer r5 blocker #11 ("fingers render as thin bent
                # twigs"): shrink relaxed 13% -> 8% — the r2 mitten fix
                # over-corrected once the plate lames were fitted over it
                # phase4 fixer r1 blocker #3 ("hands read as tiny dark
                # blobs"): shrink INVERTED to a +7% enlargement.
                # phase4 fixer r2 major #6 ("oversized blobby mitts"): the
                # +7% overshot — net scale now -2% (≈ -8.5% vs the r1 hands)
                # so the gauntlets read proportioned; the plate shells and
                # tapered finger lames are fitted after and follow.
                v.co = cen + (v.co - cen) * (1.0 - 0.02 * f)
                n_scaled += 1
        print(f"[02_details] hand scale (sgn={sgn:+.0f}): {n_scaled} verts "
              f"scaled -2% (p4 r2) about {tuple(round(c, 3) for c in cen)}")
    body.data.update()

    grip_point, grip_axis, palm_n = curl_fingers(body, "R", 86.0)  # firm grip (#6)
    curl_fingers(body, "L", 32.0)                       # relaxed left hand

    # -- fixer r4 blocker #11 (round 2): SHRINK THE CALVES *BEFORE* the armor
    # build. The straight-taper greave fits over whatever calf it samples —
    # fitted over the raw anatomical calf it ballooned into a funnel cone.
    # Shrinking first lets the rigid taper come out slim AND fully clear of
    # the (now much smaller) anatomy.
    leg_axis = {}
    for sgn in (1, -1):
        cx, cy, _ = _limb_radial(body, 0.70, sgn, 24, win=0.06)
        leg_axis[sgn] = (cx, cy)
    n_shrunk = 0
    for v in body.data.vertices:
        z = v.co.z
        if 0.24 < z < 1.06 and abs(v.co.x) > 0.02:
            f = min((z - 0.24) / 0.06, (1.06 - z) / 0.06, 1.0)
            cx, cy = leg_axis[1 if v.co.x > 0 else -1]
            v.co.x = cx + (v.co.x - cx) * (1.0 - 0.40 * f)
            v.co.y = cy + (v.co.y - cy) * (1.0 - 0.40 * f)
            n_shrunk += 1
    body.data.update()
    print(f"[02_details] calf verts shrunk under greaves (pre-armor): "
          f"{n_shrunk}")

    # -- build ------------------------------------------------------------------------
    armor = build_armor(mat_gold, body)
    tabard = build_tabard(mat_tabard, mat_gold, body)
    hair = build_hair(mat_hair, mat_gold, body, eye_data, mat_hairdeep)
    # record the joined slot order for 03_materials' in-slot replacement
    # (clear_materials() nulls the slots by name, so the names must ride
    # along as a custom property — same idea as the eye-slot contract)
    hair["godwyn_slot_names"] = [m.name if m else "" for m in
                                 hair.data.materials]
    print(f"[02_details] Godwyn_Hair slots: {list(hair['godwyn_slot_names'])}")
    sword = build_sword(mat_gold, mat_blade, grip_point, grip_axis, palm_n)
    eyes = build_eyes(eye_data, mat_sclera, mat_iris, mat_pupil, mat_skin)

    # -- fixer r1 blocker #1: MASK the bare feet — the sabatons fully enclose
    # the feet, so the body's foot polys (toes!) are deleted outright. This
    # guarantees zero toe poke-through in any pose. Runs AFTER build_armor
    # (the sabaton lofts sample these verts) and BEFORE the expression
    # blendshapes (which remap via the godwyn_orig_idx attribute).
    # (fixer r4: the calf shrink now runs BEFORE build_armor — see above —
    # so the straight-taper greaves fit the shrunk anatomy.)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    doomed = [v for v in bm.verts if v.co.z < 0.20]
    n_foot = len(doomed)
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    print(f"[02_details] body foot verts deleted under sabatons: {n_foot}")

    # -- fixer r5 blocker #8: HEROIC PROPORTION PASS ---------------------------
    # Head -5% x (soft ramp above the neck), legs +9% (z*LEG_K below the hip
    # plane), whole figure renormalized to 3.2m. Applied to body + every
    # conforming assembly TOGETHER so all plates stay seated. Runs BEFORE
    # add_expression_blendshapes (shape-key basis must be final coords).
    for ob in (body, armor, tabard, hair, eyes):
        narrow = ob in (body, hair, eyes)   # head-attached geometry only
        for v in ob.data.vertices:
            co = v.co
            if narrow and co.z > 2.62:
                f = min(1.0, (co.z - 2.62) / 0.14)
                co = Vector((co.x * (1.0 - 0.05 * f), co.y, co.z))
            v.co = _prop_remap(co)
        ob.data.update()
    # sword: RIGID (grip sits above the leg-stretch kink; a piecewise z-map
    # would bend the straight blade) — uniform-scale geometry, remap origin
    for v in sword.data.vertices:
        v.co *= PROP_S
    sword.data.update()
    sword.location = _prop_remap(Vector(sword.location))
    sword["grip_point"] = list(_prop_remap(Vector(sword["grip_point"][:])))
    # landmark custom props ride the same transform (03 warmth masks, 04
    # finger chains); palm_normal/grip_axis are directions — unchanged
    for k in ("godwyn_knuckle_r", "godwyn_knuckle_l", "godwyn_lip_c",
              "godwyn_nose_tip", "godwyn_cheek_l", "godwyn_cheek_r",
              "godwyn_ear_l", "godwyn_ear_r",
              "godwyn_eye_l", "godwyn_eye_r"):
        if k in body.keys():
            body[k] = list(_prop_remap(Vector(body[k][:])))
    zmax = max(v.co.z for v in body.data.vertices)
    print(f"[02_details] heroic proportion pass: legs x{LEG_K:.2f} below "
          f"z={LEG_Z0:.3f}, renorm x{PROP_S:.4f}, head -5% x; "
          f"body zmax={zmax:.3f}")

    col = G.get_or_create_collection("Godwyn")
    for ob in (armor, tabard, hair, sword, eyes):
        G.move_to_collection(ob, col)

    # -- face expression blendshapes (AFTER all body vertex edits) ----------------
    add_expression_blendshapes(body)

    # -- gate assertions -----------------------------------------------------------------
    for name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Tabard", "Godwyn_Hair",
                 "Godwyn_Sword", "Godwyn_Eyes"):
        assert name in bpy.data.objects, f"{name} missing"
        assert bpy.data.objects[name].users_collection[0].name == "Godwyn", \
            f"{name} not in Godwyn collection"
    # design gate: sabaton + greave geometry must exist inside the armor join
    amin_z = min(v.co.z for v in armor.data.vertices)
    assert amin_z < 0.02, f"sabatons missing: armor min z {amin_z:.3f}"
    print("[02_details] GATE: Body/Armor/Tabard/Hair/Sword all in 'Godwyn'")

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"[02_details] Saved {BLEND}")

    render_previews(bpy.context.scene)
    print("=" * 60)
    print("[02_details] Phase 2 build complete")
    print("=" * 60)


main()
