"""
01_base_human.py — Phase 1: REAL anatomical base human for Godwyn the Golden.

Replaces the old primitive+Skin-modifier blob (01_base_mesh.py) with an
MPFB2 (MakeHuman Plugin For Blender 2) anatomical human:
  - Object:      "Godwyn_Body"  (single mesh: face, hands+fingers, feet+toes)
  - Collection:  "Godwyn"
  - Height:      exactly 3.2 m, feet on ground (z=0), centred on origin
  - Shape:       male, young (~25), idealized/heroic-noble, athletic-lean
  - Pose:        MPFB2 neutral rest stance (posing is a later phase)
  - Barefoot, no clothing/armor/hair (later phases)

Idempotent: full scene reset then rebuild (INV-6). Deterministic: fixed
macro dict, seeded RNG (INV-5). Saves models/godwyn_phase1.blend and
renders clay GPU previews to renders/wip/phase1/ (INV-2: OptiX asserted).

Usage:
  blender --background --python ~/godwyn-boss-fight/scripts/01_base_human.py 2>&1
"""
import bpy
import sys
import os
import math
import random
import importlib
import mathutils

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
BLEND_OUT = os.path.join(REPO_ROOT, "models", "godwyn_phase1.blend")
WIP_DIR = os.path.join(REPO_ROOT, "renders", "wip", "phase1")
os.makedirs(WIP_DIR, exist_ok=True)
os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)

random.seed(1420)  # INV-5 (no RNG used today, but seeded for reproducibility)

TARGET_HEIGHT = 3.2  # metres (SPEC.txt: 3.2m, reads as a person not a landscape)

# ---------------------------------------------------------------------------
# GODWYN MACRO SHAPE (MakeHuman macro space, deterministic)
#   gender 1.0      -> fully male
#   age 0.5         -> ~25 years old (MakeHuman mapping) — young prime
#   muscle 0.62     -> athletic swordsman, NOT bodybuilder bulk
#   weight 0.47     -> lean
#   proportions 0.95-> idealized proportions (MakeHuman "perfect" end)
#   height 0.78     -> tall/heroic within the base space (absolute height is
#                      re-scaled to exactly 3.2m afterwards; this slider
#                      shapes the long-limbed heroic silhouette)
# ---------------------------------------------------------------------------
GODWYN_MACRO = {
    "gender": 1.0,
    "age": 0.45,
    # p5b fixer r3 blocker #3: the body still read slight/feminine — muscle
    # pushed near max (heroic demigod mass; 02_details adds the plate sculpt)
    "muscle": 0.92,
    "weight": 0.46,
    "proportions": 1.0,
    "height": 0.78,
    "cupsize": 0.5,
    "firmness": 0.5,
    "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0},
}

# ---------------------------------------------------------------------------
# GODWYN DETAIL TARGETS (MPFB2 target/morph system — MACRO DEFINITION pass)
#
# The macro dict alone leaves a soft "pill" read: no nose bridge, no brow,
# no cheekbones, undefined jaw, soft torso. These MakeHuman detail targets
# are loaded via TargetService.load_target() (real morph system, NOT raw
# vertex edits) and give Godwyn a DEFINED, noble, idealized face + an
# athletic swordsman body. Deterministic list; iterate weights visually.
#
# Names resolve via TargetService.target_full_path() (basename prefix match
# over mpfb/data/targets/**). Values are shape-key weights in [-1, 1].
# ---------------------------------------------------------------------------
GODWYN_DETAIL_TARGETS = [
    # ---- SKULL / HEAD FORM -------------------------------------------------
    ("head-scale-depth-incr",          0.30),  # deeper skull in profile
    ("head-rectangular",               0.30),  # masculine head plane
    ("head-scale-horiz-incr",          0.05),  # p5b r3: 0.15 made the face
                                               # read WIDE + flat — mostly out
    ("forehead-trans-backward",        0.15),  # slight noble forehead slope
    ("forehead-temple-incr",           0.10),
    # ---- BROW (real brow ridge — the "pill" killer) -------------------------
    ("eyebrows-trans-forward",         0.95),
    ("eyebrows-trans-down",            0.30),
    # ---- NOSE (straight Greek bridge, projected, refined tip) ---------------
    ("nose-greek-incr",                0.60),
    ("nose-scale-depth-incr",          0.50),
    ("nose-volume-incr",               0.20),
    ("nose-width2-decr",               0.30),
    ("nose-point-width-decr",          0.30),
    ("nose-hump-incr",                 0.08),
    # ---- CHEEKBONES ----------------------------------------------------------
    # phase4 fixer r4 blocker #1 ("flat wide facial planes"): cheekbone morphs
    # to FULL and inner-cheek hollow deepened — the malar plane break + the
    # narrowed midface must come from the morph system first, with 02's
    # sculpt pass layering on top.
    ("l-cheek-bones-incr",             1.00),
    ("r-cheek-bones-incr",             1.00),
    ("l-cheek-inner-decr",             0.62),
    ("r-cheek-inner-decr",             0.62),
    # ---- JAW / CHIN -----------------------------------------------------------
    ("chin-bones-incr",                0.80),  # wide masculine jawbones
    ("chin-prominent-incr",            0.50),
    ("chin-width-incr",                0.30),
    ("chin-height-incr",               0.15),
    # ---- LIPS (refined, defined cupid's bow) ----------------------------------
    ("mouth-cupidsbow-incr",           0.40),
    ("mouth-lowerlip-volume-incr",     0.20),
    ("mouth-upperlip-volume-incr",     0.15),
    # ---- BODY: athletic-defined swordsman -------------------------------------
    # p5 fixer r1 (major #5): morphs pushed HARDER — the exposed chest read
    # as a smooth flat plane. 02_details adds a landmark sculpt pass on top
    # (clavicles, sternum groove, rectus blocking) for the macro shapes.
    ("torso-vshape-incr",              0.70),
    ("torso-muscle-pectoral-incr",     1.00),
    ("torso-muscle-dorsi-incr",        0.90),  # p5b r3: V-taper vs hips
    ("stomach-tone-incr",              1.00),
    ("measure-waist-circ-decr",        0.28),
    ("l-upperarm-muscle-incr",         0.82),
    ("r-upperarm-muscle-incr",         0.82),
    ("l-upperarm-shoulder-muscle-incr", 0.90),
    ("r-upperarm-shoulder-muscle-incr", 0.90),
    ("l-lowerarm-muscle-incr",         0.85),  # p5b r3: thin-arm read
    ("r-lowerarm-muscle-incr",         0.85),
    ("neck-scale-horiz-incr",          0.20),  # warrior neck
]


def dynamic_import(pkg_suffix, key):
    """MPFB2 modules live under bl_ext.<repo>.mpfb — find by suffix."""
    for amod in list(sys.modules):
        if amod.endswith(pkg_suffix):
            m = importlib.import_module(amod)
            if hasattr(m, key):
                return getattr(m, key)
    raise ValueError(f"No module ending in '{pkg_suffix}' with attr '{key}'")


def main():
    print("=" * 60)
    print("[01_base_human] Phase 1 — MPFB2 anatomical base human")
    print("=" * 60)

    # -- GPU assert (INV-2) --------------------------------------------------
    active_gpu = G.enable_gpu()
    print(f"[01_base_human] GPU backend: {active_gpu}")

    # -- Idempotent reset (INV-6) --------------------------------------------
    G.reset_scene()

    # -- MPFB2 human ----------------------------------------------------------
    print("[01_base_human] Enabling MPFB2...")
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
    HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")

    print(f"[01_base_human] Creating human with macro: {GODWYN_MACRO}")
    body = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=dict(GODWYN_MACRO),
    )
    if body is None or body.type != "MESH":
        print("[01_base_human] FATAL: create_human failed", file=sys.stderr)
        sys.exit(1)
    body.name = "Godwyn_Body"
    body.data.name = "Godwyn_Body_Mesh"
    print(f"[01_base_human] Human created: verts={len(body.data.vertices)} "
          f"dims={tuple(round(d, 3) for d in body.dimensions)}")

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body

    # -- MACRO DEFINITION: MPFB2 detail targets (morph system, not raw verts) --
    TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")
    loaded = 0
    for tname, weight in GODWYN_DETAIL_TARGETS:
        path = TargetService.target_full_path(tname)
        if not path:
            print(f"[01_base_human] FATAL: target '{tname}' not found",
                  file=sys.stderr)
            sys.exit(1)
        TargetService.load_target(body, path, weight=weight, name=tname)
        loaded += 1
    print(f"[01_base_human] Detail targets loaded: {loaded} "
          f"(face definition + athletic body)")

    # -- Bake SHAPING morphs into the mesh (deterministic base geometry) ------
    # MPFB shapes the human via shape keys; bake the current macro+detail mix
    # so vertex coords ARE the shaped human (fixes landmark math + allows a
    # clean helper delete + export-friendly mesh). This bakes the BASE SHAPE
    # only — the morph values stay reachable in GODWYN_DETAIL_TARGETS above
    # (scripts are the reproducible source), and FACE EXPRESSION blendshapes
    # are added as live shape keys at the end of 02_details.py (animatable).
    if body.data.shape_keys:
        baked = body.shape_key_add(name="_GodwynBaked", from_mix=True)
        for kb in [k for k in body.data.shape_keys.key_blocks
                   if k.name != "_GodwynBaked"]:
            body.shape_key_remove(kb)
        for i, v in enumerate(body.data.vertices):
            v.co = baked.data[i].co
        body.shape_key_remove(body.data.shape_keys.key_blocks["_GodwynBaked"])
        print("[01_base_human] Shape keys baked into mesh")

    # -- Delete helper geometry, KEEPING the eyeball helpers ------------------
    # MPFB masks non-"body" helper verts with a Mask modifier. We hard-delete
    # them instead (clean export mesh), but keep helper-l-eye/helper-r-eye so
    # Godwyn has real eyeballs in his sockets.
    keep_groups = {"body", "helper-l-eye", "helper-r-eye"}
    keep_idx = {body.vertex_groups[g].index for g in keep_groups
                if g in body.vertex_groups}
    # Original-basemesh vertex indices, stored as a persistent int attribute
    # BEFORE any vertex deletion. 02_details uses this to remap MPFB face
    # expression targets (indexed against the full basemesh) onto the trimmed
    # mesh when it creates the live expression blendshapes.
    oidx = body.data.attributes.new("godwyn_orig_idx", "INT", "POINT")
    for i in range(len(body.data.vertices)):
        oidx.data[i].value = i
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(body.data)
    dvl = bm.verts.layers.deform.active
    doomed = []
    for v in bm.verts:
        dv = v[dvl]
        if not any(gi in dv and dv[gi] > 0.0 for gi in keep_idx):
            doomed.append(v)
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    for mod in list(body.modifiers):
        body.modifiers.remove(mod)
    print(f"[01_base_human] Helper geometry deleted (eyes kept) "
          f"-> verts={len(body.data.vertices)}")

    # Smooth shading for the clay read
    bpy.ops.object.shade_smooth()

    # -- Scale to exactly 3.2 m, feet at z=0, centred in x/y ------------------
    cur_h = body.dimensions.z
    sf = TARGET_HEIGHT / cur_h
    body.scale = (sf, sf, sf)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Re-anchor: min-z of geometry -> 0, x/y bbox centre -> 0 (apply-scale
    # friendly: transforms end applied, object at identity).
    mw = body.matrix_world
    xs, ys, zs = [], [], []
    for v in body.data.vertices:
        co = mw @ v.co
        xs.append(co.x); ys.append(co.y); zs.append(co.z)
    dx = (min(xs) + max(xs)) / 2.0
    dy = (min(ys) + max(ys)) / 2.0
    dz = min(zs)
    for v in body.data.vertices:
        v.co.x -= dx; v.co.y -= dy; v.co.z -= dz
    body.location = (0.0, 0.0, 0.0)

    # -- Heroic proportion pass (fixer r2 #8) ----------------------------------
    # Art direction: neck a touch long, shoulders slightly narrow for the
    # 1.4x-human idealized-warrior brief. Widen the clavicle/deltoid span
    # ~6% and shorten the neck ~3cm, then re-normalize height to 3.2m.
    s_heroic = heroic_proportions(body)

    # Cumulative target-delta scale: MakeHuman target units -> final mesh.
    # 0.1 = create_human(scale=0.1); sf = rescale to 3.2m; s_heroic = the
    # re-normalize above. 02_details multiplies expression target deltas by
    # this (times its own head-enlarge factor) when building blendshapes.
    body["godwyn_expr_scale"] = 0.1 * sf * s_heroic
    print(f"[01_base_human] expr delta scale = {body['godwyn_expr_scale']:.5f}")

    print(f"[01_base_human] Final dims: "
          f"{tuple(round(d, 3) for d in body.dimensions)} "
          f"(target height {TARGET_HEIGHT}m)")
    assert abs(body.dimensions.z - TARGET_HEIGHT) < 0.01, "height off-spec"

    # -- Single 'Godwyn' collection -------------------------------------------
    col = G.get_or_create_collection("Godwyn")
    G.move_to_collection(body, col)
    # MPFB sometimes parents/creates extras — sweep any stray meshes it made
    for obj in list(bpy.data.objects):
        if obj is not body and obj.type == "MESH" and "Human" in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)

    # -- Gate assertion --------------------------------------------------------
    assert "Godwyn_Body" in bpy.data.objects, "Godwyn_Body missing"
    assert bpy.data.objects["Godwyn_Body"].users_collection[0].name == "Godwyn"
    print("[01_base_human] GATE: Godwyn_Body exists in 'Godwyn' collection")

    # -- Save regenerable .blend ----------------------------------------------
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
    print(f"[01_base_human] Saved {BLEND_OUT}")

    # -- Clay preview renders (mandatory visual iteration) ---------------------
    render_previews(body)

    print("=" * 60)
    print("[01_base_human] Phase 1 build complete")
    print("=" * 60)


# ---------------------------------------------------------------------------
# HEROIC PROPORTIONS (fixer r2 #8)
# ---------------------------------------------------------------------------

def heroic_proportions(body):
    """
    Widen the shoulder/clavicle span ~6% (soft band through the deltoids)
    and shorten the neck ~3cm (everything above the neck base drops), then
    re-normalize total height back to exactly 3.2m. Deterministic; operates
    on final-scale vertex coords (body already 3.2m, feet at z=0).
    """
    me = body.data
    # 1) shoulder span: |x| scaled up inside a z band around the deltoids
    # p5b fixer r3 blocker #3: +6% still read narrow-shouldered/feminine —
    # pushed to +14% at the deltoid peak (director asked +20-30% total across
    # macro morphs + this band; muscle 0.92 supplies the rest of the mass).
    n_sh = 0
    for v in me.vertices:
        z = v.co.z
        ax = abs(v.co.x)
        if 2.28 < z < 2.82 and ax > 0.12:
            w = min(1.0, (ax - 0.12) / 0.20)             # ramp out from midline
            zc = max(0.0, 1.0 - abs(z - 2.56) / 0.28)    # soft band falloff
            v.co.x *= 1.0 + 0.14 * w * zc
            n_sh += 1
    # 1b) hips: narrow the pelvic span ~5% (kills the wide-hipped silhouette;
    # p5b fixer r3 blocker #3). Soft band through the hip/glute mass.
    n_hp = 0
    for v in me.vertices:
        z = v.co.z
        ax = abs(v.co.x)
        if 1.50 < z < 2.05 and ax > 0.05:
            w = min(1.0, (ax - 0.05) / 0.12)
            zc = max(0.0, 1.0 - abs(z - 1.78) / 0.28)
            v.co.x *= 1.0 - 0.05 * w * zc
            n_hp += 1
    # 2) neck: drop everything above the neck base by up to 3cm
    NB, DROP = 2.58, 0.030
    n_nk = 0
    for v in me.vertices:
        if v.co.z > NB:
            t = min(1.0, (v.co.z - NB) / 0.10)
            v.co.z -= DROP * t
            n_nk += 1
    me.update()
    # 3) re-normalize: feet back to z=0, height back to exactly 3.2m
    zmin = min(v.co.z for v in me.vertices)
    for v in me.vertices:
        v.co.z -= zmin
    zmax = max(v.co.z for v in me.vertices)
    s = TARGET_HEIGHT / zmax
    for v in me.vertices:
        v.co *= s
    me.update()
    print(f"[01_base_human] heroic proportions: shoulders +14% ({n_sh} verts), "
          f"hips -5% ({n_hp} verts), "
          f"neck -{DROP*1000:.0f}mm ({n_nk} verts), re-normalized x{s:.4f}")
    return s


# ---------------------------------------------------------------------------
# CLAY PREVIEW RIG
# ---------------------------------------------------------------------------

def _clay_material():
    mat = bpy.data.materials.get("Mat_ClayPreview")
    if mat is None:
        mat = bpy.data.materials.new("Mat_ClayPreview")
        mat.use_nodes = True
        p = mat.node_tree.nodes.get("Principled BSDF")
        if p:
            p.inputs["Base Color"].default_value = (0.78, 0.70, 0.62, 1.0)
            p.inputs["Roughness"].default_value = 0.85
    return mat


def _add_light(name, energy, size, color, loc, rot):
    li = bpy.data.lights.new(name, "AREA")
    li.energy = energy
    li.size = size
    li.color = color
    ob = bpy.data.objects.new(name, li)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _aim_camera(cam_obj, target):
    d = mathutils.Vector(target) - mathutils.Vector(cam_obj.location)
    cam_obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _vgroup_centroid(body, predicate):
    """Centroid of world-space verts passing predicate(co)."""
    mw = body.matrix_world
    pts = [mw @ v.co for v in body.data.vertices if predicate(mw @ v.co)]
    if not pts:
        return mathutils.Vector((0, 0, 1.6))
    return sum(pts, mathutils.Vector()) / len(pts)


def render_previews(body):
    scene = bpy.context.scene

    # Clay material on the body
    mat = _clay_material()
    body.data.materials.clear()
    body.data.materials.append(mat)

    # Neutral 3-point rig (preview only — NOT the dark-fantasy rig)
    _add_light("Preview_Key", 1500, 2.5, (1.0, 0.95, 0.85),
               (3.5, -4.5, 4.5), (math.radians(55), 0, math.radians(35)))
    _add_light("Preview_Fill", 500, 4.0, (0.75, 0.85, 1.0),
               (-4.0, -3.0, 2.5), (math.radians(70), 0, math.radians(-50)))
    _add_light("Preview_Rim", 800, 2.0, (1.0, 0.92, 0.7),
               (0.5, 4.5, 4.0), (math.radians(-55), 0, math.radians(175)))

    cam_data = bpy.data.cameras.new("Preview_Cam")
    cam_data.lens = 85
    cam_data.clip_end = 100.0
    cam = bpy.data.objects.new("Preview_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam

    # Landmark targets from geometry (pose-robust)
    mw = body.matrix_world
    max_x = max((mw @ v.co).x for v in body.data.vertices)
    hand_c = _vgroup_centroid(body, lambda c: c.x > max_x - 0.12)
    feet_c = _vgroup_centroid(body, lambda c: c.z < 0.15)
    head_z = TARGET_HEIGHT - 0.18  # approx head centre

    shots = [
        # (name, cam loc, target, resx, resy)
        ("front",   (0.0, -7.5, 1.7),  (0, 0, 1.65), 768, 1280),
        ("threeq",  (4.6, -6.0, 1.9),  (0, 0, 1.65), 768, 1280),
        ("face",    (0.30, -1.05, head_z + 0.02), (0, 0, head_z), 768, 768),
        ("hand",    (hand_c.x + 0.35, hand_c.y - 0.9, hand_c.z + 0.15),
                    tuple(hand_c), 768, 768),
        ("feet",    (0.7, -1.6, 0.45), tuple(feet_c), 768, 768),
    ]

    for name, loc, target, rx, ry in shots:
        cam.location = loc
        _aim_camera(cam, target)
        G.configure_cycles(scene, samples=64, resolution_x=rx,
                           resolution_y=ry, use_denoiser=True)
        assert scene.cycles.device == "GPU", "GPU not set — INV-2 violated"
        out = os.path.join(WIP_DIR, f"clay_{name}.png")
        G.render_to_path(out, scene)
        if not os.path.exists(out) or os.path.getsize(out) < 4096:
            print(f"[01_base_human] FATAL: bad render {out}", file=sys.stderr)
            sys.exit(1)
        print(f"[01_base_human] Preview OK: {out} "
              f"({os.path.getsize(out):,} bytes)")


main()
