"""
02_details.py — Phase 2: DRESS + HAIR + SWORD for Godwyn the Golden.

Builds on the MPFB2 anatomical body from 01_base_human.py
(models/godwyn_phase1.blend, object "Godwyn_Body", 3.2m, faces -Y).

Adds four objects to the "Godwyn" collection (idempotent — deletes any
prior versions by name, rebuilds, saves back to the same .blend):

  Godwyn_Armor  partial gold: layered pauldrons (3 plates each side),
                sternum/chest filigree (bevel curves hugging the pecs),
                forearm guards, neck gorget ring. Chest EXPOSED — no
                breastplate.
  Godwyn_Robe   deep-blue flowing lower robe (waist->shin, sinusoidal
                folds, hem high enough that bare feet read) + back cape
                + gold waist trim.
  Godwyn_Hair   long golden-blonde: scalp cap + ~300 fine flowing strands
                down the back + ONE asymmetric side braid (right temple,
                merging into the loose hair). Reads as hair, not a wreath.
  Godwyn_Sword  longsword — gold grip/pommel/filigree crossguard, subtle
                blue-tinged tapered blade. OBJECT ORIGIN AT THE GRIP.
                Gripped firmly in the right hand, tip toward the ground.
  Godwyn_Eyes   solid eyeball spheres (sclera + protruding cornea) seated
                in the opened sockets; banded sclera/iris/pupil materials.

PHASE-1 rules honoured: NO crown, NO markings, barefoot, exposed chest.
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
from mathutils import Vector, Euler

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


def surface_ribbon(name, path, half_w, mat, off=0.0075, thick=0.011):
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
# FACE — open the eyelids + seat the MPFB2 eyeball helpers (blocker #2)
# ---------------------------------------------------------------------------

def enlarge_head(body, factor=1.06, z_lo=2.70, z_hi=2.86):
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
            if dz > 0.002:      # upper lid: lift + tuck back
                v.co.z += 0.0062 * fall
                v.co.y += 0.0024 * fall
            elif dz < -0.002:   # lower lid: drop slightly
                v.co.z -= 0.0034 * fall
                v.co.y += 0.0015 * fall
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
            # r4 blocker #1: MUCH stronger lip volume — the r3 4-6mm reads
            # as flat mannequin plane on a 2x-scale head. Real mouth now.
            if dz_lip >= 0:                         # upper lip
                out = 0.0075 * lat
                # philtrum: subtle central dip on the upper lip
                if abs(v.co.x - c.x) < half_w * 0.14:
                    out *= 0.45
                v.co.y -= out
                v.co.z += 0.0010 * lat              # slight cupid's-bow lift
            else:                                   # lower lip: fuller
                v.co.y -= 0.0095 * lat
                v.co.z -= 0.0012 * lat
            # mouth SEAM: recess a thin band where the lips meet so the
            # part reads as a dark line (visible mouth, blocker #1)
            if abs(dz_lip) < 0.0045:
                seam = (1.0 - abs(dz_lip) / 0.0045) * lat
                v.co.y += 0.0052 * seam
            # r3 (major #6): relax the mouth corners slightly upward-neutral
            if abs(v.co.x - c.x) > half_w * 0.70:
                v.co.z += 0.0018
                v.co.y += 0.0008
        print(f"[02_details] lips sculpted (r4 volume+seam): {len(lip_idx)} "
              f"verts, c=({c.x:.3f},{c.y:.3f},{c.z:.3f})")

        # -- CHIN: forward mass below the lower lip (jawline relief) ----------
        chin_c = Vector((0.0, c.y, c.z - 0.052))
        for v in me.vertices:
            dx = abs(v.co.x - chin_c.x)
            dz = abs(v.co.z - chin_c.z)
            if dx > half_w * 1.05 or dz > 0.040 or v.co.y > c.y + 0.03:
                continue
            fall = (max(0.0, 1.0 - dx / (half_w * 1.05))
                    * max(0.0, 1.0 - dz / 0.040)) ** 1.2
            v.co.y -= 0.0060 * fall
        print("[02_details] chin mass raised (r4 jawline relief)")

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
                v.co.y -= 0.0290 * prof * lat       # forward nose mass
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
                    v.co.y -= 0.0068 * fall        # forward volume (r4: more)
                    v.co.z += 0.0014 * fall        # lifted, youthful mass
            print("[02_details] cheeks filled + cheekbones raised (r3 #6)")
    else:
        print("[02_details] WARNING: 'lips' group missing — lips skipped",
              file=sys.stderr)

    # -- BROW: soft ROUNDED ridge above each eye (r3 #6: less stern) -----------
    for c, r in eye_data:
        for v in me.vertices:
            dx = abs(v.co.x - c.x)
            dz = v.co.z - c.z
            if dx > r * 2.5 or not (r * 0.9 < dz < r * 2.6):
                continue
            if v.co.y > c.y + 0.012:
                continue
            fx = max(0.0, 1.0 - dx / (r * 2.5)) ** 0.8   # wider, gentler
            fz = math.sin(math.pi * (dz - r * 0.9) / (r * 1.7))
            v.co.y -= 0.0044 * fx * max(0.0, fz)   # r4: stronger relief
    print("[02_details] brow ridge raised above both eyes (r4 relief)")

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
    for k, (c, r) in enumerate(eye_data):
        R = r * 1.10                       # inflate: lids must overlap the ball
        # ADVANCE the ball: the helper centroid sits deep in the skull — at
        # +0.003 the sphere was ~15mm recessed behind the lid aperture and
        # the sockets rendered as shadowed black slits.
        centre = c + Vector((0.0, -0.011, 0.0))
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=36, radius=R)
        me = bpy.data.meshes.new(f"_eye{k}")
        bm.to_mesh(me)
        bm.free()
        for v in me.vertices:
            d = v.co.normalized()
            ang = math.degrees(d.angle(fwd))
            if ang < 30.0:                 # cornea bulge, smooth falloff
                v.co += d * (R * 0.09 * math.cos(math.radians(ang * 3.0)))
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
            poly.material_index = 2 if ang < 12.0 else (1 if ang < 30.0 else 0)
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
        for lname, z_lo, z_hi in ((f"_lidU{k}", 0.24, 0.88),
                                  (f"_lidD{k}", -0.72, -0.36)):
            Rl = R * 1.16                  # clear the cornea bulge
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=36, v_segments=24,
                                      radius=Rl)
            doomed = [v for v in bm.verts
                      if not (z_lo < v.co.z / Rl < z_hi and v.co.y < 0.30 * Rl)]
            bmesh.ops.delete(bm, geom=doomed, context="VERTS")
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
            and (v.co - wrist).length < 0.50 and sgn * v.co.x > 0.80]
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
    print(f"[02_details] {side} fingers curled {max_deg:.0f}deg: "
          f"knuckle s0={s0:.3f} "
          f"palm_n=({palm_n.x:.2f},{palm_n.y:.2f},{palm_n.z:.2f}) "
          f"grip=({grip_point.x:.3f},{grip_point.y:.3f},{grip_point.z:.3f})")
    return grip_point, axis, palm_n


# ---------------------------------------------------------------------------
# ARMOR
# ---------------------------------------------------------------------------

def build_armor(mat_gold):
    parts = []
    # -- layered pauldrons: 3 overlapping plates, EACH with a rim lip ----------
    pauldron_r = []
    plates = [
        # (loc, scale, y-tilt deg, keep_z) — r4 minor #6: inner rims sunk
        # 18mm inward / 12mm down so every plate CONTACTS the deltoid
        # instead of floating off the shoulder.
        (Vector((0.452, 0.18, 2.613)), (0.210, 0.230, 0.155), 22, -0.15),
        (Vector((0.517, 0.18, 2.508)), (0.190, 0.212, 0.105), 42, -0.05),
        (Vector((0.557, 0.17, 2.413)), (0.168, 0.190, 0.085), 58, -0.05),
    ]
    for i, (loc, sc, tilt, kz) in enumerate(plates):
        pauldron_r.append(sphere_shell(
            f"_pauldR{i}", loc, sc, (0, math.radians(tilt), 0),
            mat_gold, keep_z=kz))
        # rim lip around EVERY plate edge (layered-plate read, minor #9)
        R = Euler((0, math.radians(tilt), 0), "XYZ").to_matrix()
        rim_spline = []
        for j in range(17):
            a = 2 * math.pi * j / 16.0
            local = Vector((sc[0] * math.cos(a), sc[1] * math.sin(a),
                            sc[2] * max(kz, -0.02)))
            rim_spline.append((loc + R @ local, 1.0))
        pauldron_r.append(curve_obj(f"_pauldR_rim{i}", [rim_spline],
                                    0.013 - 0.002 * i, mat_gold))

    # -- sternum filigree (r3 major #5): flat surface-conformed RIBBONS ---------
    # Every vertex hugs the sampled chest surface — no more floating handlebar.
    # The clavicle sweep now runs OUT to the pauldron inner edges (a real
    # strap connection) and a diamond sternum motif rings the central stem.
    def cf(x, z, off=0.007):
        return Vector((x, surf_y(x, z) - off, z))

    # r4 minor #6: POLISHED STERNUM PLATE — a small convex gold plate the
    # filigree ribbons visibly anchor to (no more gold scribbles painted on
    # bare skin). Dome axis rotated to face -Y (the character's front).
    plate_y = surf_y(0.0, 2.40)
    parts.append(sphere_shell(
        "_fil_plate", Vector((0.0, plate_y + 0.008, 2.40)),
        (0.080, 0.115, 0.030), (math.radians(90), 0, 0),
        mat_gold, keep_z=0.30, thickness=0.008))

    # clavicle strap: pauldron edge -> across the upper chest -> pauldron edge
    # (r4: thicker/beveled via the new surface_ribbon defaults)
    parts.append(surface_ribbon("_fil_clav", [
        (-0.385, 2.435, 0.55), (-0.30, 2.475, 0.75), (-0.20, 2.515, 0.9),
        (-0.10, 2.535, 1.0), (0.00, 2.525, 1.1), (0.10, 2.535, 1.0),
        (0.20, 2.515, 0.9), (0.30, 2.475, 0.75), (0.385, 2.435, 0.55)],
        0.019, mat_gold))
    # central stem, clavicle down INTO the sternum plate, on to solar plexus
    parts.append(surface_ribbon("_fil_stem", [
        (0.0, 2.525, 1.0), (0.0, 2.44, 0.95), (0.0, 2.30, 0.9),
        (0.0, 2.16, 0.8), (0.0, 2.06, 0.5)], 0.016, mat_gold))
    # diamond sternum motif ringing the plate — mirrored, symmetric
    for s in (1, -1):
        parts.append(surface_ribbon(f"_fil_dia{'RL'[s < 0]}", [
            (0.0, 2.46, 0.5), (s * 0.055, 2.375, 0.8), (0.0, 2.29, 0.5)],
            0.011, mat_gold))
        # gentle S-sweep following the under-pec line, tapering out
        parts.append(surface_ribbon(f"_fil_pec{'RL'[s < 0]}", [
            (s * 0.015, 2.27, 0.8), (s * 0.09, 2.235, 0.9),
            (s * 0.16, 2.245, 0.6), (s * 0.195, 2.30, 0.35),
            (s * 0.185, 2.345, 0.2)], 0.014, mat_gold))
    # bosses where stem meets collar / at the drop (kept shallow to the skin)
    parts.append(uv_sphere("_fil_boss", cf(0.0, 2.525, 0.006),
                           (0.030, 0.016, 0.030), mat_gold))
    parts.append(uv_sphere("_fil_drop", cf(0.0, 2.045, 0.005),
                           (0.018, 0.012, 0.030), mat_gold))

    # -- forearm guards (solidified — no visible open-tube interior) ------------
    f_dir = (WRIST_R - ELBOW_R).normalized()
    g0 = ELBOW_R + f_dir * 0.06
    g1 = WRIST_R - f_dir * 0.015
    guard_r = cylinder_between("_guardR", g0, g1, 0.092, 0.074, mat_gold)
    sol = guard_r.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.007
    sol.offset = -1.0
    apply_mods(guard_r)
    rib = []
    q = f_dir.to_track_quat("Z", "Y").to_matrix()
    for j in range(21):
        a = 2 * math.pi * j / 20.0
        rib.append((g1 + q @ Vector((0.077 * math.cos(a),
                                     0.077 * math.sin(a), 0)), 1.0))
    guard_rib_r = curve_obj("_guardRibR", [rib], 0.010, mat_gold)

    # mirror the one-sided pieces to the left
    right_side = pauldron_r + [guard_r, guard_rib_r]
    mirrored = [mirror_x(ob, ob.name + "_L") for ob in right_side]
    parts += right_side + mirrored

    return join(parts, "Godwyn_Armor")


# ---------------------------------------------------------------------------
# ROBE (lower garment + cape + gold waist trim)
# ---------------------------------------------------------------------------

def build_robe(mat_robe, mat_gold):
    parts = []
    # -- flowing skirt: lofted rings, waist -> hem -------------------------------
    # Asymmetric vertical folds + slight lateral sweep so the silhouette FLOWS
    # instead of belling (major #6). Hem raised so the bare feet read (#10).
    NR, NS = 17, 84
    verts, faces = [], []
    for i in range(NR):
        t = i / (NR - 1)
        z = WAIST_Z - t * (WAIST_Z - HEM_Z)
        rx = 0.318 + (0.480 - 0.318) * (t ** 1.15)
        ry = 0.228 + (0.475 - 0.228) * (t ** 1.15)
        cy = 0.200 + 0.135 * (t ** 2)                 # train drift back
        cx = 0.055 * (t ** 1.6)                       # asymmetric lateral sweep
        amp = 0.006 + 0.105 * (t ** 1.6)              # folds grow to the hem
        for j in range(NS):
            a = 2 * math.pi * j / NS
            w = 1.0 + amp / max(rx, 0.001) * (
                math.sin(9 * a + 2.2 * t)
                + 0.55 * math.sin(5 * a + 1.4 + 2.6 * t)      # asymmetric
                + 0.30 * math.sin(3 * a - 0.7 - 1.1 * t))
            # inward folds must never dip inside the leg envelope
            w = max(w, 0.965)
            verts.append(Vector((cx + rx * w * math.sin(a),
                                 cy + ry * w * math.cos(a), z)))
    for i in range(NR - 1):
        for j in range(NS):
            a = i * NS + j
            b = i * NS + (j + 1) % NS
            faces.append((a, b, b + NS, a + NS))
    skirt = mesh_obj("_skirt", verts, faces, mat_robe)
    sol = skirt.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.010
    apply_mods(skirt)
    shade_smooth(skirt)
    parts.append(skirt)

    # -- trailing back cape from behind the shoulders ------------------------------
    NU, NV = 26, 20
    cverts, cfaces = [], []
    for i in range(NV):
        t = i / (NV - 1)
        z = 2.58 - t * (2.58 - 0.28)
        half_w = 0.40 + 0.34 * (t ** 1.2)
        y0 = 0.415 + 0.52 * (t ** 1.6)                # longer backward train
        xoff = 0.07 * (t ** 1.5)                      # asymmetric side drift
        for j in range(NU):
            u = j / (NU - 1) * 2 - 1                  # -1..1 across
            y = y0 + 0.075 * t * math.sin(6.5 * u + 1.7 * t) \
                + 0.045 * t * math.sin(3.2 * u - 0.9 + 2.4 * t) \
                - 0.04 * (1 - u * u) * (t ** 0.8)
            cverts.append(Vector((xoff + half_w * u, y, z)))
    for i in range(NV - 1):
        for j in range(NU - 1):
            a = i * NU + j
            cfaces.append((a, a + 1, a + NU + 1, a + NU))
    cape = mesh_obj("_cape", cverts, cfaces, mat_robe)
    sol = cape.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.010
    apply_mods(cape)
    shade_smooth(cape)
    parts.append(cape)

    # -- gold waist trim (belt) -----------------------------------------------------
    belt = []
    for j in range(41):
        a = 2 * math.pi * j / 40.0
        belt.append((Vector((0.310 * math.sin(a), 0.20 + 0.218 * math.cos(a),
                             WAIST_Z + 0.012)), 1.0))
    parts.append(curve_obj("_belt", [belt], 0.019, mat_gold))
    parts.append(uv_sphere("_clasp", Vector((0.0, -0.045, WAIST_Z + 0.015)),
                           (0.045, 0.020, 0.055), mat_gold))

    return join(parts, "Godwyn_Robe")


# ---------------------------------------------------------------------------
# HAIR
# ---------------------------------------------------------------------------

def build_hair(mat_hair, mat_gold, body):
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
    for v in bm.verts:
        v.co = v.co + v.normal * 0.0015  # nearly flush: reads as colored
    cme = bpy.data.meshes.new("_haircap")  # scalp, not a helmet/band ridge
    bm.to_mesh(cme)
    bm.free()
    cap = bpy.data.objects.new("_haircap", cme)
    link_obj(cap)
    cme.materials.append(mat_hair)
    sol = cap.modifiers.new("Solid", "SOLIDIFY")
    sol.thickness = 0.004
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
    strands = []
    n_strands = 300
    step = max(1, len(scalp) // n_strands)
    part_sgn = 1.0
    for k in range(0, len(scalp), step):
        root, n = scalp[k]
        # comb away from the centre parting (crown verts near x=0 flip a coin)
        if abs(root.x) > 0.012:
            part_dir = math.copysign(1.0, root.x)
        else:
            part_dir = part_sgn = -part_sgn
        sway = part_dir * random.uniform(0.01, 0.09)
        end_z = random.uniform(1.22, 2.10)    # r4: wider length variation
        r = random.uniform(0.35, 1.0)         # r4: wider width variation
        p0 = root - n * 0.004     # roots SUBMERGED below the scalp — the
                                  # flush cap no longer hides root end-caps
        # slide along the skull toward the nape, hugging it TIGHTLY
        nape = Vector((root.x * 0.55 + sway * 0.3, 0.30, 2.82))
        p1 = outside_skull(p0.lerp(nape, 0.45), 0.005)
        p2 = Vector((root.x * 0.45 + sway * 0.5, 0.40, 2.58))
        p3 = Vector((root.x * 0.35 + sway, 0.46 + random.uniform(0, 0.04),
                     (2.5 + end_z) / 2))
        tip = Vector((root.x * 0.28 + sway * 1.5,
                      0.44 + random.uniform(0, 0.07), end_z))
        strands.append([(p0, 0.9 * r), (p1, 1.05 * r), (p2, 0.95 * r),
                        (p3, 0.7 * r), (tip, 0.08 * r)])
    parts.append(curve_obj("_strands", strands, 0.008, mat_hair, resolution=8))

    # -- FRINGE (r3 major #3): irregular parted strands over the hairline ------
    # The bare cap edge read as a bald-cap band across the forehead. Root a
    # row of short strands at the FRONT scalp verts and sweep them back over
    # the crown with random parting so the hairline reads as combed hair.
    y_front = min(co.y for co, _ in scalp)
    front_row = [(co, n) for co, n in scalp if co.y < y_front + 0.045]
    # r4 major #4: the r3 fringe arced UP over the crown (z +0.022 with a
    # 7-9mm skull margin) and read as a padded roll / wig headband. Strands
    # now lie FLAT against the skull (margin ~3mm, no upward arc) and comb
    # laterally away from a centre parting.
    fringe = []
    for root, n in front_row:
        for _ in range(2):
            part_dir = math.copysign(1.0, root.x) if abs(root.x) > 0.010 \
                else random.choice((-1.0, 1.0))
            sway = part_dir * random.uniform(0.012, 0.040)
            r = random.uniform(0.45, 1.0)
            p0 = root - n * 0.003
            mid = outside_skull(
                Vector((root.x * 0.9 + sway, root.y + 0.10, root.z + 0.004)),
                0.003)
            back = outside_skull(
                Vector((root.x * 0.7 + sway * 2.0, root.y + 0.24,
                        root.z - 0.006)), 0.004)
            fringe.append([(p0, 0.9 * r), (mid, 1.0 * r), (back, 0.50 * r)])
    if fringe:
        parts.append(curve_obj("_fringe", fringe, 0.0062, mat_hair,
                               resolution=8))
        print(f"[02_details] hairline fringe: {len(fringe)} strands over "
              f"{len(front_row)} front roots")

    # -- FRONT FALLS (r3 major #3): loose clumps over the shoulders/chest ------
    falls = []
    for sgn in (1.0, -1.0):
        temple = max(scalp, key=lambda cn: cn[0].x * sgn
                     - abs(cn[0].y - (HC.y - 0.10)) * 2.0)[0]
        # r4 major #3: fewer falls, every control point pulled ONTO the body
        # (the r3 p2 at y=0.10 let strands float detached in front of the
        # right shoulder). Tips sit 8mm proud of the sampled chest surface.
        n_fall = 4 if sgn > 0 else 7        # right side lighter (braid there)
        for i in range(n_fall):
            sway = random.uniform(-0.02, 0.02)
            r = random.uniform(0.5, 1.0)
            end_z = random.uniform(2.10, 2.30)
            x1 = sgn * (0.10 + random.uniform(0.0, 0.040))
            p0 = temple + Vector((sway * 0.5, random.uniform(0, 0.05),
                                  random.uniform(-0.02, 0.04)))
            p1 = outside_skull(Vector((p0.x * 1.05, p0.y + 0.05, 2.78)), 0.006)
            p2 = Vector((x1 * 1.12, 0.045 + sway, 2.52))      # past the ear
            p3 = Vector((x1, surf_y(x1, 2.32) - 0.012, 2.32))  # onto the chest
            tip = Vector((x1 * 0.92 + sway, surf_y(x1 * 0.92, end_z) - 0.008,
                          end_z))
            falls.append([(p0, 0.9 * r), (p1, 1.0 * r), (p2, 0.9 * r),
                          (p3, 0.65 * r), (tip, 0.10 * r)])
    parts.append(curve_obj("_falls", falls, 0.009, mat_hair, resolution=8))
    print(f"[02_details] front falls: {len(falls)} strands past the shoulders")

    # -- braids: 3-strand helix, rooted at temple scalp points ----------------------
    def braid(name, path, rad_helix, rad_strand):
        n = 34

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
                a = 2 * math.pi * (ph / 3.0) + t * math.pi * 6.5
                off = side * math.cos(a) * rad_helix + up * math.sin(a) * rad_helix
                pts.append((c + off, 1.0 - 0.65 * t))
            splines.append(pts)
        return curve_obj(name, splines, rad_strand, mat_hair, resolution=10)

    # ONE asymmetric side braid (r3 major #3: it hid behind the shoulder and
    # never read on camera). Thicker plait, rooted above the RIGHT temple,
    # sweeping over the ear then falling down the FRONT of the right shoulder
    # onto the chest — clearly visible in the full and face frames.
    root_r = max(scalp, key=lambda cn: cn[0].x)[0]
    braid_r = braid("_braidR",
                    [root_r,
                     Vector((root_r.x * 0.95, root_r.y + 0.09, root_r.z - 0.03)),
                     Vector((0.195, 0.22, 2.70)),        # over the ear
                     Vector((0.225, 0.02, 2.52)),        # front of the shoulder
                     Vector((0.235, surf_y(0.235, 2.34) - 0.030, 2.34)),
                     Vector((0.215, surf_y(0.215, 2.12) - 0.028, 2.12)),
                     Vector((0.195, surf_y(0.195, 1.96) - 0.026, 1.96))],
                    0.015, 0.0125)   # r4: helix ~= strand radius -> touching
                                     # alternating lobes (reads as a plait)
    parts.append(braid_r)
    # gold tie bead where the braid ends on the chest
    tie_at = Vector((0.195, surf_y(0.195, 1.95) - 0.026, 1.945))
    parts.append(uv_sphere("_braidTie", tie_at, (0.030, 0.030, 0.024), mat_gold))

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
    # blade: tapered diamond cross-section, subtle blue steel
    bl0, bl1 = 0.165, 1.72   # base z, tip z (blade ~1.55m)
    rings = 12
    bverts, bfaces = [], []
    for i in range(rings):
        t = i / (rings - 1)
        z = bl0 + (bl1 - bl0) * t
        w = 0.092 * ((1 - t) ** 0.85) + 0.010 * (1 - t)
        th = 0.013 * (1 - t) + 0.0035
        if i == rings - 1:
            w, th = 0.002, 0.002
        bverts += [Vector((w / 2, 0, z)), Vector((0, th / 2, z)),
                   Vector((-w / 2, 0, z)), Vector((0, -th / 2, z))]
    for i in range(rings - 1):
        for j in range(4):
            a = i * 4 + j
            b = i * 4 + (j + 1) % 4
            bfaces.append((a, b, b + 4, a + 4))
    bverts.append(Vector((0, 0, bl1 + 0.045)))          # point
    tipbase = (rings - 1) * 4
    for j in range(4):
        bfaces.append((tipbase + j, tipbase + (j + 1) % 4, len(bverts) - 1))
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
    sword.rotation_euler = blade_dir.to_track_quat("Z", "Y").to_euler()
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
        ("bust",   (1.1, -2.7, 2.75), (0, 0.08, 2.45), 960, 960),
        ("sword",  (2.7, -2.4, 1.95), (1.10, -0.42, 1.60), 960, 960),
    ]
    for name, loc, target, rx, ry in shots:
        cam.location = loc
        aim(target)
        G.configure_cycles(scene, samples=64, resolution_x=rx,
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
        if ob.name.startswith(("Godwyn_Armor", "Godwyn_Robe", "Godwyn_Hair",
                               "Godwyn_Sword", "Godwyn_Eyes", "Godwyn_Armature",
                               "Godwyn_VoidCrack", "Preview_", "Beauty_",
                               "Light_", "Cam_", "_")):
            bpy.data.objects.remove(ob, do_unlink=True)
    # strip any prior rig state off the body (rerun-after-04 safety)
    body.parent = None
    for mod in list(body.modifiers):
        body.modifiers.remove(mod)
    for mname in ("Mat_Gold", "Mat_Robe", "Mat_Hair", "Mat_Blade",
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
    mat_robe = G.make_diffuse_material("Mat_Robe", (0.08, 0.12, 0.35, 1.0),
                                       roughness=0.85)
    mat_hair = G.make_diffuse_material("Mat_Hair", (0.60, 0.42, 0.13, 1.0),
                                       roughness=0.4)
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
        mat_robe.node_tree.nodes["Principled BSDF"] \
            .inputs["Specular IOR Level"].default_value = 0.12
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

    # -- body refinements (need the surface sampler) -----------------------------------
    init_surface_sampler(body)
    enlarge_head(body)                    # r3 minor #8: rebalance vs shoulders
    eye_data = refine_face(body)          # blockers #1/#3: eyes + lips/brow/ears
    grip_point, grip_axis, palm_n = curl_fingers(body, "R", 86.0)  # firm grip (#6)
    curl_fingers(body, "L", 32.0)                       # relaxed left hand

    # -- build ------------------------------------------------------------------------
    armor = build_armor(mat_gold)
    robe = build_robe(mat_robe, mat_gold)
    hair = build_hair(mat_hair, mat_gold, body)
    sword = build_sword(mat_gold, mat_blade, grip_point, grip_axis, palm_n)
    eyes = build_eyes(eye_data, mat_sclera, mat_iris, mat_pupil, mat_skin)

    col = G.get_or_create_collection("Godwyn")
    for ob in (armor, robe, hair, sword, eyes):
        G.move_to_collection(ob, col)

    # -- gate assertions -----------------------------------------------------------------
    for name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Robe", "Godwyn_Hair",
                 "Godwyn_Sword", "Godwyn_Eyes"):
        assert name in bpy.data.objects, f"{name} missing"
        assert bpy.data.objects[name].users_collection[0].name == "Godwyn", \
            f"{name} not in Godwyn collection"
    print("[02_details] GATE: Body/Armor/Robe/Hair/Sword all in 'Godwyn'")

    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"[02_details] Saved {BLEND}")

    render_previews(bpy.context.scene)
    print("=" * 60)
    print("[02_details] Phase 2 build complete")
    print("=" * 60)


main()
