"""
03_materials.py — Phase 3: Materials & Shaders — the golden luminous demigod.

Assigns EVERY Cycles material + builds the void world background, per
SPEC.txt 332-341 and build-plan Section 3 Phase 3 / Section 4 material table.

Materials authored:
  Mat_Skin        — Principled BSDF base (0.95,0.90,0.82) + SSS (pale, low
                    radius) + subtle Emission mix (1.0,0.88,0.45) @ ~2.5;
                    near-translucent demigod skin that self-illuminates without
                    blowing out (SPEC 334-336).
  Mat_Gold        — metallic=1, base (0.82,0.65,0.15), low-moderate roughness,
                    slight sheen, roughness-noise variation for faintly-worn
                    feel (SPEC 341).  Shared by Godwyn_Armor hilt/crossguard.
  Mat_Tabard        — deep blue (0.08,0.12,0.35), NO emission (SPEC 340),
                    cloth-ish roughness + slight sheen for fabric read.
  Mat_Blade       — steel + subtle blue tint, faint emission << skin (SPEC
                    317 "blue-tinged... not glowing heavily").
  Mat_Hair        — golden-blonde (0.75,0.58,0.08), lighter/less-saturated
                    than armor, anisotropic sheen.
  Void world      — near-black + faint vertical golden crack (already built by
                    lib_godwyn.build_void_bg; we extend it here with the
                    world shader and the crack plane).

All SPEC color values treated as linear sRGB per assumption A7.

INV-2: GPU enforced and asserted before render.
INV-3: SPEC-faithful colors, no deviation.
INV-6: Idempotent — clears previous material assignments before re-applying.
INV-7: Godwyn's skin emission is the scene's primary light source.

Run:
  blender --background --python scripts/03_materials.py
"""

import sys
import os
import math
import bpy

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

_REPO_ROOT   = os.path.dirname(_SCRIPT_DIR)
_WIP_DIR     = os.path.join(_REPO_ROOT, "renders", "wip")
_LOG_DIR     = os.path.join(_WIP_DIR, "logs")
_PREVIEW_OUT = os.path.join(_WIP_DIR, "03_beauty.png")
os.makedirs(_WIP_DIR, exist_ok=True)
os.makedirs(_LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# MATERIAL NAMES (used for idempotent clearing, INV-6)
# ---------------------------------------------------------------------------
MAT_NAMES = (
    "Mat_Skin",
    "Mat_Underlayer",
    "Mat_Gold",
    "Mat_Tabard",
    "Mat_Blade",
    "Mat_Hair",
    "Mat_HairDeep",
    "Mat_VoidCrack",
    "Mat_EyeSclera",
    "Mat_EyeIris",
    "Mat_EyePupil",
)

PREVIEW_MAT_PREFIXES = ("Prev_", "Mat_SkinPreview", "Mat_ClayPreview")

OBJECT_ASSIGNMENTS = {
    "Godwyn_Body":  "Mat_Skin",
    "Godwyn_Armor": "Mat_Gold",
    "Godwyn_Tabard": None,          # handled specially: blue cloth + gold
                                    # embroidery slots (godwyn_slot_names)
    "Godwyn_Hair":  None,           # handled specially: hair + deep under-hair
    "Godwyn_Sword": None,           # handled specially: hilt=gold, blade=blade
}


# ---------------------------------------------------------------------------
# IDEMPOTENT CLEAR (INV-6)
# ---------------------------------------------------------------------------

def clear_materials():
    """Remove any prior Phase-3 materials (by name) before rebuilding."""
    for name in MAT_NAMES:
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
            bpy.data.materials.remove(mat)
    # Also purge leftover preview materials from P1/P2
    for name in list(bpy.data.materials.keys()):
        if any(name.startswith(p) for p in PREVIEW_MAT_PREFIXES):
            bpy.data.materials.remove(bpy.data.materials[name])


# ---------------------------------------------------------------------------
# NODE HELPERS
# ---------------------------------------------------------------------------

def _new_node(nt, bl_idname, location=(0, 0)):
    n = nt.nodes.new(bl_idname)
    n.location = location
    return n


def _link(nt, from_node, from_socket, to_node, to_socket):
    nt.links.new(from_node.outputs[from_socket], to_node.inputs[to_socket])


# ---------------------------------------------------------------------------
# MICRO-DETAIL HELPERS (Phase 3 detail pass)
#
# All micro detail is driven by OBJECT-space coordinates (tri-planar-safe,
# no UV dependency — the custom armor/robe/hair have no clean UVs) and is
# delivered through the Material Output DISPLACEMENT socket with
# displacement_method='BUMP' (the default, game-safe path: Cycles converts
# the height signal to a shading-normal perturbation, zero geometry change,
# deforms with the mesh). For BEAUTY renders only, enable_adaptive_disp()
# flips selected materials to 'BOTH' + adaptive subdivision AFTER the .blend
# has been saved, so the stored/exported asset stays normal-map-based.
# ---------------------------------------------------------------------------

def _in_sock(node, ident):
    """Input socket by IDENTIFIER (Mix node has duplicate 'A'/'B' names)."""
    return next(s for s in node.inputs if s.identifier == ident)


def _out_sock(node, ident):
    return next(s for s in node.outputs if s.identifier == ident)


def _mix_color(nt, loc, col_a=None, col_b=None):
    """ShaderNodeMix in RGBA mode with identifier-safe color sockets."""
    n = _new_node(nt, "ShaderNodeMix", loc)
    n.data_type = "RGBA"
    if col_a is not None:
        _in_sock(n, "A_Color").default_value = col_a
    if col_b is not None:
        _in_sock(n, "B_Color").default_value = col_b
    return n


def _link_mix_fac(nt, from_node, from_socket, mix_node):
    nt.links.new(from_node.outputs[from_socket],
                 _in_sock(mix_node, "Factor_Float"))


def _link_mix_a(nt, from_node, from_socket, mix_node):
    nt.links.new(from_node.outputs[from_socket],
                 _in_sock(mix_node, "A_Color"))


def _link_mix_out(nt, mix_node, to_node, to_socket):
    nt.links.new(_out_sock(mix_node, "Result_Color"),
                 to_node.inputs[to_socket])


def _set_disp_method(mat, method="BUMP"):
    """Set displacement method across Blender API generations."""
    try:
        mat.displacement_method = method
    except AttributeError:
        try:
            mat.cycles.displacement_method = method
        except AttributeError:
            pass


def _math(nt, op, loc, v0=None, v1=None, v2=None):
    n = _new_node(nt, "ShaderNodeMath", loc)
    n.operation = op
    for i, v in enumerate((v0, v1, v2)):
        if v is not None:
            n.inputs[i].default_value = v
    return n


def _map_range(nt, loc, fmin, fmax, tmin, tmax, clamp=True):
    n = _new_node(nt, "ShaderNodeMapRange", loc)
    n.inputs["From Min"].default_value = fmin
    n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin
    n.inputs["To Max"].default_value = tmax
    try:
        n.clamp = clamp
    except AttributeError:
        pass
    return n


def _wire_displacement(nt, out, height_node, height_socket, scale_m,
                       loc=(520, -420)):
    """Height signal -> Displacement node -> Material Output.Displacement."""
    disp = _new_node(nt, "ShaderNodeDisplacement", loc)
    disp.inputs["Midlevel"].default_value = 0.5
    disp.inputs["Scale"].default_value = scale_m
    _link(nt, height_node, height_socket, disp, "Height")
    _link(nt, disp, "Displacement", out, "Displacement")
    return disp


def _stretched_noise(nt, tex_c, loc, mapping_scale, noise_scale, detail=5.0,
                     roughness=0.55):
    """
    Object-space noise stretched by a Mapping node — a LOW mapping scale on
    one axis elongates features ALONG that axis (scratches, brushed grain,
    hair strands).
    """
    mp = _new_node(nt, "ShaderNodeMapping", loc)
    mp.inputs["Scale"].default_value = mapping_scale
    ns = _new_node(nt, "ShaderNodeTexNoise", (loc[0] + 180, loc[1]))
    ns.inputs["Scale"].default_value = noise_scale
    ns.inputs["Detail"].default_value = detail
    ns.inputs["Roughness"].default_value = roughness
    _link(nt, tex_c, "Object", mp, "Vector")
    _link(nt, mp, "Vector", ns, "Vector")
    return ns


# ---------------------------------------------------------------------------
# MATERIAL BUILDERS
# ---------------------------------------------------------------------------

def _landmark(key, default):
    """Landmark stored by 02_details as a custom prop on Godwyn_Body."""
    body = bpy.data.objects.get("Godwyn_Body")
    if body is not None and key in body.keys():
        return tuple(body[key])
    return default


def _warmth_mask(nt, loc, points):
    """
    Object-space warmth mask (p5r1 #4): union (MAX) of soft radial falloffs
    around the given landmark points. Returns the node holding the 0..1
    mask in output 'Value'. Object coords == world coords for Godwyn_Body
    (identity transform, baked verts).
    """
    geo = _new_node(nt, "ShaderNodeNewGeometry", (loc[0] - 200, loc[1]))
    acc = None
    for i, (p, rad) in enumerate(points):
        d = _new_node(nt, "ShaderNodeVectorMath",
                      (loc[0], loc[1] - 160 * i))
        d.operation = "DISTANCE"
        d.inputs[1].default_value = p
        _link(nt, geo, "Position", d, 0)
        mr = _map_range(nt, (loc[0] + 180, loc[1] - 160 * i),
                        rad * 0.30, rad, 1.0, 0.0)
        nt.links.new(d.outputs["Value"], mr.inputs["Value"])
        if acc is None:
            acc = mr
            acc_sock = "Result"
        else:
            mx = _math(nt, "MAXIMUM", (loc[0] + 360, loc[1] - 160 * i))
            nt.links.new(acc.outputs[acc_sock], mx.inputs[0])
            nt.links.new(mr.outputs["Result"], mx.inputs[1])
            acc = mx
            acc_sock = "Value"
    return acc, acc_sock


def make_skin_material() -> bpy.types.Material:
    """
    Pale luminous demigod skin (SPEC 312, 334-336).

    Strategy: use Principled BSDF's native emission inputs (Blender 4+)
    so the emission is composited correctly inside the BSDF instead of
    being additive-summed with Add Shader (which blows out in dark scenes).
    Falls back to a MixShader (low fac) for older Blender builds so the
    skin glows but never overwhelms.

    SPEC target: luminous, pale, slight inner glow — NOT blown out to white.
    Emission strength 2.5 is the SPEC value but using it with Add Shader
    in a near-black void saturates to white; using it inside Principled BSDF
    or at fac 0.12 in a Mix keeps form visible.
    """
    mat = bpy.data.materials.new("Mat_Skin")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-1100, -200))

    # ---- MICRO: two-scale FINE NOISE pores (object coords, no UVs) ---------
    # p5r2 major #5 ("cracked porcelain"): the 42-scale DISTANCE_TO_EDGE
    # voronoi drew a polygonal crack network over the whole body — DELETED.
    # Pores are now a much finer voronoi pit field + two fine-noise scales,
    # at SUB-MILLIMETRE amplitude (0.0016m bump on a 3.2m figure).
    vor = _new_node(nt, "ShaderNodeTexVoronoi", (-900, -420))
    vor.inputs["Scale"].default_value = 260.0
    try:
        vor.inputs["Randomness"].default_value = 0.9
    except KeyError:
        pass
    _link(nt, tex_c, "Object", vor, "Vector")
    # pore mask: 1 at pore center, 0 outside (distance 0..0.30 -> 1..0)
    pore0 = _map_range(nt, (-700, -420), 0.0, 0.30, 1.0, 0.0)
    _link(nt, vor, "Distance", pore0, "Value")
    # phase4 fixer r4 blocker #1 ("zero pore/texture read at close-up"): a
    # SECOND, finer voronoi pit field at true pore scale (~1.5mm cells on
    # the 3.2m figure) unioned with the 260-scale field — the Cam_Face
    # close-up must show real skin micro-structure.
    vor2 = _new_node(nt, "ShaderNodeTexVoronoi", (-900, -520))
    vor2.inputs["Scale"].default_value = 680.0
    try:
        vor2.inputs["Randomness"].default_value = 0.95
    except KeyError:
        pass
    _link(nt, tex_c, "Object", vor2, "Vector")
    pore2 = _map_range(nt, (-700, -520), 0.0, 0.26, 1.0, 0.0)
    _link(nt, vor2, "Distance", pore2, "Value")
    pore_u = _math(nt, "MAXIMUM", (-600, -460))
    _link(nt, pore0, "Result", pore_u, 0)
    _link(nt, pore2, "Result", pore_u, 1)
    # p4 r5 blocker #1 ("uniform speckle noise"): REGION-VARIED micro
    # detail — a low-frequency zone noise modulates the pore field 0.30..1.0
    # so forehead/nose/cheek zones carry different pore densities instead of
    # one homogeneous speckle field over the whole head.
    zone_n = _new_node(nt, "ShaderNodeTexNoise", (-760, -460))
    zone_n.inputs["Scale"].default_value = 4.5
    zone_n.inputs["Detail"].default_value = 2.0
    _link(nt, tex_c, "Object", zone_n, "Vector")
    zone_m = _map_range(nt, (-680, -400), 0.30, 0.70, 0.30, 1.0)
    _link(nt, zone_n, "Fac", zone_m, "Value")
    pore = _math(nt, "MULTIPLY", (-560, -460))
    _link(nt, pore_u, "Value", pore, 0)
    _link(nt, zone_m, "Result", pore, 1)

    # Fine grain (sub-mm skin texture) — two octave scales
    fine = _new_node(nt, "ShaderNodeTexNoise", (-900, -640))
    fine.inputs["Scale"].default_value = 340.0
    fine.inputs["Detail"].default_value = 6.0
    _link(nt, tex_c, "Object", fine, "Vector")
    fine2 = _new_node(nt, "ShaderNodeTexNoise", (-900, -760))
    fine2.inputs["Scale"].default_value = 95.0
    fine2.inputs["Detail"].default_value = 4.0
    _link(nt, tex_c, "Object", fine2, "Vector")

    # Medium mottling (cm-scale tonal patches)
    med = _new_node(nt, "ShaderNodeTexNoise", (-900, -860))
    med.inputs["Scale"].default_value = 9.0
    med.inputs["Detail"].default_value = 4.0
    _link(nt, tex_c, "Object", med, "Vector")

    # Height = 0.5 - 0.20*pore + 0.18*(fine-0.5) + 0.10*(fine2-0.5)
    f_c = _math(nt, "SUBTRACT", (-700, -640));  _link(nt, fine, "Fac", f_c, 0); f_c.inputs[1].default_value = 0.5
    f2_c = _math(nt, "SUBTRACT", (-700, -760)); _link(nt, fine2, "Fac", f2_c, 0); f2_c.inputs[1].default_value = 0.5
    h1 = _math(nt, "MULTIPLY_ADD", (-500, -420), None, -0.32, 0.5)  # p4 r4
    _link(nt, pore, "Value", h1, 0)
    h2 = _math(nt, "MULTIPLY_ADD", (-320, -520), None, 0.18)
    _link(nt, f_c, "Value", h2, 0)
    _link(nt, h1, "Value", h2, 2)
    h3 = _math(nt, "MULTIPLY_ADD", (-140, -620), None, 0.10)
    _link(nt, f2_c, "Value", h3, 0)
    _link(nt, h2, "Value", h3, 2)
    # p5b fixer r3 major #6: pore bump amplitude DOUBLED (0.0016 -> 0.0032)
    # — at close-up the skin still read as smooth porcelain.
    # phase4 fixer r3 blocker #1 ("poreless plastic"): +30% again — the
    # pore field must break the specular at Cam_Face range.
    # phase4 fixer r4 blocker #1 ("the current 0.0042 bump is invisible"):
    # 0.0042 -> 0.0062 + the 680-scale pore union above — a visible
    # micro-normal at Cam_Face scale.
    # p4 r5 blocker #1 ("putty skin with uniform speckle"): the 0.0062
    # amplitude WAS the speckle — CUT to 0.0034; the zone modulation above
    # carries the living-skin variation instead of raw amplitude.
    _wire_displacement(nt, out, h3, "Value", 0.0034, loc=(520, -520))

    # ---- Base color: SPEC base + capillary mottling + landmark warmth -----
    # p5r1 #4: living tonal variation — broad mottling stays LOW-fac, then
    # object-space landmark masks flush the lips/nose/cheeks/ears/knuckles
    # with visible capillary warmth (kills the marble read).
    # fixer r2 blocker #3: the face rendered porcelain-WHITE — the raw SPEC
    # albedo (0.95,0.90,0.82) under the bright warm key + specular sheen
    # reads far whiter than the spec swatch. Base dropped/warmed so the
    # RENDERED face lands on the spec tone; spec+sheen also cut below.
    # fixer r2 blocker #3 (round 3): pixel-sampling showed the render is not
    # blown out — it is DESATURATED (R:G 1.08 vs ~1.2 for living skin; AgX
    # compresses chroma further). Albedo pushed to a genuinely saturated
    # warm tone so the DISPLAYED face lands on a warm skin read.
    # fixer r5 blocker #7: base warmed + mottling contrast raised again —
    # the r4 face still rendered a flat chalk mask under the warm key
    # phase4 fixer r1 blocker #1 ("porcelain mannequin"): six rounds of
    # small warms never survived the key light + AgX highlight desaturation.
    # Albedo taken DOWN a real step (~-30% value, more chroma) so the lit
    # face renders as warm living skin instead of clipping to chalk.
    warm = _mix_color(nt, (-320, 140), (0.62, 0.42, 0.29, 1.0),
                      (0.56, 0.34, 0.25, 1.0))   # warm flush
    # p5b r3 major #6: mottling fac raised 0.35 -> 0.50 (flat single-value
    # skin at full-body distance); r4: -> 0.58 (still reading pale); r5: 0.70
    # p4 r5 blocker #1: mottling contrast CUT 0.70 -> 0.45 — the strong
    # cm-scale mottle read as uniform noise, not living tonal zones
    mfac = _map_range(nt, (-520, 140), 0.32, 0.75, 0.0, 0.45)
    _link(nt, med, "Fac", mfac, "Value")
    _link_mix_fac(nt, mfac, "Result", warm)

    # p5r2 blocker #3 ("single pink blotch = paint smear"): flush is now
    # SUBTLE MULTI-ZONE — bigger, softer radii at LOWER fac (0.20), covering
    # brow / nose / cheeks / ears / knuckles, so it reads as living tonal
    # variation instead of one rouge spot.
    nose_lm = _landmark("godwyn_nose_tip", (0.0, -0.09, 2.93))
    flush_pts = [
        (nose_lm, 0.060),
        ((nose_lm[0], nose_lm[1] + 0.02, nose_lm[2] + 0.115), 0.075),  # brow
        # fixer r3 blocker #1 ("uniform waxy skin"): subtle capillary warmth
        # AROUND THE EYES (lid/canthus zone) — offsets from the nose landmark
        ((nose_lm[0] + 0.062, nose_lm[1] + 0.012, nose_lm[2] + 0.058), 0.042),
        ((nose_lm[0] - 0.062, nose_lm[1] + 0.012, nose_lm[2] + 0.058), 0.042),
        (_landmark("godwyn_cheek_l", (0.09, -0.02, 2.95)), 0.095),
        (_landmark("godwyn_cheek_r", (-0.09, -0.02, 2.95)), 0.095),
        (_landmark("godwyn_ear_l", (0.17, 0.13, 2.98)), 0.065),
        (_landmark("godwyn_ear_r", (-0.17, 0.13, 2.98)), 0.065),
        (_landmark("godwyn_knuckle_r", (1.02, -0.30, 1.86)), 0.105),
        (_landmark("godwyn_knuckle_l", (-1.02, -0.30, 1.86)), 0.105),
        # p5b r3 major #6: elbows + knees join the capillary flush zones
        # (r5: follow the +16% arm stretch + heroic proportion remap)
        ((0.82, 0.10, 2.14), 0.085),   # elbow R
        ((-0.82, 0.10, 2.14), 0.085),  # elbow L
        ((0.17, -0.06, 1.00), 0.095),  # knee R
        ((-0.17, -0.06, 1.00), 0.095), # knee L
    ]
    fmask, fsock = _warmth_mask(nt, (-2100, 600), flush_pts)
    # p5b r3 major #6: flush fac 0.20 -> 0.34 — the r2 value was invisible
    # at render distance (uniform matte white read)
    ffac = _math(nt, "MULTIPLY", (-1500, 300), None, 0.62)   # r5: warmer still
    nt.links.new(fmask.outputs[fsock], ffac.inputs[0])
    flush = _mix_color(nt, (-160, 140), None, (0.82, 0.48, 0.38, 1.0))
    nt.links.new(_out_sock(warm, "Result_Color"), _in_sock(flush, "A_Color"))
    _link_mix_fac(nt, ffac, "Value", flush)

    # COOL JAW/CHIN zone (p5r2 blocker #3): a faint cool shift low on the
    # face — the classic warm-forehead/cool-jaw portrait zoning.
    ear_l = _landmark("godwyn_ear_l", (0.17, 0.13, 2.98))
    ear_r = _landmark("godwyn_ear_r", (-0.17, 0.13, 2.98))
    jaw_pts = [
        ((ear_l[0] * 0.85, ear_l[1] - 0.03, ear_l[2] - 0.075), 0.075),
        ((ear_r[0] * 0.85, ear_r[1] - 0.03, ear_r[2] - 0.075), 0.075),
        ((0.0, -0.09, 2.83), 0.060),   # chin/jaw centre
    ]
    jmask, jsock = _warmth_mask(nt, (-2100, 250), jaw_pts)
    jfac = _math(nt, "MULTIPLY", (-1500, 100), None, 0.22)  # p4 r4 zoning
    nt.links.new(jmask.outputs[jsock], jfac.inputs[0])
    cool = _mix_color(nt, (-80, 140), None, (0.86, 0.85, 0.86, 1.0))
    nt.links.new(_out_sock(flush, "Result_Color"), _in_sock(cool, "A_Color"))
    _link_mix_fac(nt, jfac, "Value", cool)

    # FAINT VEINS (p5r2 major #5): thin ridged-noise lines, cool blue-grey,
    # masked to the temples + upper chest, very low fac.
    vn = _new_node(nt, "ShaderNodeTexNoise", (-2100, -400))
    vn.inputs["Scale"].default_value = 16.0
    vn.inputs["Detail"].default_value = 5.0
    _link(nt, tex_c, "Object", vn, "Vector")
    # ridged: 1 - |2x-1| -> thin lines where noise crosses 0.5
    v_a = _math(nt, "MULTIPLY_ADD", (-1900, -400), None, 2.0, -1.0)
    _link(nt, vn, "Fac", v_a, 0)
    v_b = _math(nt, "ABSOLUTE", (-1750, -400))
    _link(nt, v_a, "Value", v_b, 0)
    v_line = _map_range(nt, (-1600, -400), 0.0, 0.06, 1.0, 0.0)
    _link(nt, v_b, "Value", v_line, "Value")
    vein_pts = [
        ((ear_l[0] * 0.90, ear_l[1] - 0.055, ear_l[2] + 0.055), 0.055),  # temples
        ((ear_r[0] * 0.90, ear_r[1] - 0.055, ear_r[2] + 0.055), 0.055),
        ((0.0, -0.11, 2.41), 0.16),    # upper chest
        # p5b r3 major #6: forearms join the cool-vein zones (r5: stretched)
        ((0.90, -0.09, 2.02), 0.11),   # forearm R
        ((-0.90, -0.09, 2.02), 0.11),  # forearm L
    ]
    vmask, vsock = _warmth_mask(nt, (-2100, -650), vein_pts)
    v_m = _math(nt, "MULTIPLY", (-1450, -500))
    _link(nt, v_line, "Result", v_m, 0)
    nt.links.new(vmask.outputs[vsock], v_m.inputs[1])
    vfac = _math(nt, "MULTIPLY", (-1300, -500), None, 0.40)
    _link(nt, v_m, "Value", vfac, 0)
    veins = _mix_color(nt, (0, 140), None, (0.74, 0.77, 0.85, 1.0))
    nt.links.new(_out_sock(cool, "Result_Color"), _in_sock(veins, "A_Color"))
    _link_mix_fac(nt, vfac, "Value", veins)

    # LIPS: tighter, stronger rose tint (p5r1 blocker #1: invisible lips)
    lmask, lsock = _warmth_mask(
        nt, (-2100, -100),
        [(_landmark("godwyn_lip_c", (0.0, -0.10, 2.885)), 0.042)])
    lfac = _math(nt, "MULTIPLY", (-1500, -300), None, 0.80)  # p4 r4 zoning
    nt.links.new(lmask.outputs[lsock], lfac.inputs[0])
    lips = _mix_color(nt, (120, 140), None, (0.72, 0.38, 0.34, 1.0))
    nt.links.new(_out_sock(veins, "Result_Color"), _in_sock(lips, "A_Color"))
    _link_mix_fac(nt, lfac, "Value", lips)

    # LID DARKENING (phase4 fixer r2 blocker #1 "flat lid rims / porcelain
    # doll"): a warm shadow tone pooled around the eye sockets — the
    # natural lid/canthus pigment zone every living face has. Landmark-
    # driven from the eye centres 02_details stored.
    eye_l = _landmark("godwyn_eye_l", (0.049, -0.055, 2.955))
    eye_r = _landmark("godwyn_eye_r", (-0.049, -0.055, 2.955))
    lid_pts = [
        ((eye_l[0], eye_l[1] - 0.012, eye_l[2]), 0.040),
        ((eye_r[0], eye_r[1] - 0.012, eye_r[2]), 0.040),
        # slightly larger, softer sub-orbital zones
        ((eye_l[0], eye_l[1] - 0.008, eye_l[2] - 0.022), 0.034),
        ((eye_r[0], eye_r[1] - 0.008, eye_r[2] - 0.022), 0.034),
        # phase4 fixer r3 blocker #1: UPPER-SOCKET shadow zones under the
        # strengthened brow ridge (deepens the set-back socket read)
        ((eye_l[0], eye_l[1] - 0.006, eye_l[2] + 0.020), 0.032),
        ((eye_r[0], eye_r[1] - 0.006, eye_r[2] + 0.020), 0.032),
    ]
    dmask, dsock = _warmth_mask(nt, (-2100, -900), lid_pts)
    # p4 r3: 0.42 -> 0.56 — the socket AO must read at portrait range
    dfac_l = _math(nt, "MULTIPLY", (-1500, -900), None, 0.56)
    nt.links.new(dmask.outputs[dsock], dfac_l.inputs[0])
    lids = _mix_color(nt, (190, 140), None, (0.46, 0.30, 0.24, 1.0))
    nt.links.new(_out_sock(lips, "Result_Color"), _in_sock(lids, "A_Color"))
    _link_mix_fac(nt, dfac_l, "Value", lids)

    # p5b fixer r3 major #6: BROAD tonal breakup — a very large-scale noise
    # shifts the base toward a warmer, slightly deeper tone in patches so no
    # region of the body is a single flat value at full-body distance.
    broad_n = _new_node(nt, "ShaderNodeTexNoise", (-900, 340))
    broad_n.inputs["Scale"].default_value = 2.2
    broad_n.inputs["Detail"].default_value = 2.0
    _link(nt, tex_c, "Object", broad_n, "Vector")
    bfac = _map_range(nt, (-700, 340), 0.35, 0.65, 0.0, 0.30)
    _link(nt, broad_n, "Fac", bfac, "Value")
    broad = _mix_color(nt, (260, 140), None, (0.58, 0.44, 0.31, 1.0))
    nt.links.new(_out_sock(lids, "Result_Color"), _in_sock(broad, "A_Color"))
    _link_mix_fac(nt, bfac, "Result", broad)
    _link_mix_out(nt, broad, pbsdf, "Base Color")

    # ---- Roughness: broad 0.42..0.58 breakup + pore-level boost -----------
    noise = _new_node(nt, "ShaderNodeTexNoise", (-320, -200))
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 5.0
    _link(nt, tex_c, "Object", noise, "Vector")
    # fixer r3 blocker #1: wider roughness swing (0.38-0.62 -> 0.34-0.68) —
    # oily T-zone vs matte patches, so the face specular isn't one wax value
    mapv = _map_range(nt, (-140, -200), 0.0, 1.0, 0.30, 0.72)  # r5: wider
    _link(nt, noise, "Fac", mapv, "Value")
    # pores are slightly rougher (oil sits in them). p5r1 #4: boost DROPPED
    # 0.16 -> 0.07 — the strong per-pore roughness contrast rendered as
    # white paint-fleck speckle under the key light.
    # phase4 fixer r3 blocker #1: 0.07 -> 0.12 — micro-roughness must break
    # the plastic sheen (0.12 stays below the 0.16 speckle threshold).
    # p4 r5 blocker #1: pore roughness contrast 0.12 -> 0.07 (speckle cut)
    r2 = _math(nt, "MULTIPLY_ADD", (-20, -280), None, 0.07)
    _link(nt, pore, "Value", r2, 0)
    _link(nt, mapv, "Result", r2, 2)
    _link(nt, r2, "Value", pbsdf, "Roughness")

    # Specular — skin-level, not plastic (r2: 0.30 -> 0.18, the broad white
    # sheen was a big part of the waxy porcelain read)
    try:
        # fixer r4 blocker #7: 0.18 -> 0.13 — the broad white spec wash was
        # part of the porcelain read
        pbsdf.inputs["Specular IOR Level"].default_value = 0.13
    except (KeyError, AttributeError):
        try:
            pbsdf.inputs["Specular"].default_value = 0.07
        except (KeyError, AttributeError):
            pass
    # Sheen: nearly off (r2 — flat white sheen wash)
    try:
        pbsdf.inputs["Sheen Weight"].default_value = 0.04
        pbsdf.inputs["Sheen Roughness"].default_value = 0.55
    except KeyError:
        pass

    # Subsurface — REAL translucent warmth: warm red-orange radius, larger
    # scale so ears/nose/fingers show light bleed (major #5)
    # p5r1 #4: weight/scale RAISED + red-dominant radius so thin areas
    # (nose, ears, fingers) show visible warm light bleed at portrait range.
    # p5b fixer r3 major #6: SSS pushed harder — weight 0.48 -> 0.62, red-
    # dominant radius +40%, scale 0.14 -> 0.24 so ears/nose/fingers show a
    # warm translucent glow at grazing light instead of matte porcelain.
    sss_color = (0.98, 0.84, 0.66, 1.0)
    try:
        # Blender 4+ API
        # fixer r1 major #6: 0.62 washed the face toward chalk-wax — 0.42
        # fixer r2 blocker #3: the WAXY-PORCELAIN read was the subsurface —
        # radius 0.42 x scale 0.24 gave a ~10cm mean free path, so light
        # diffused through the whole head and washed the albedo to uniform
        # white wax. Weight and scale cut to skin-plausible values (the
        # red-dominant radius keeps the warm blood tone at ears/nose).
        # fixer r4 blocker #7 ("porcelain-white mannequin face"): SSS pushed
        # back up with a strongly red-dominant radius — ears/nose/lids must
        # show warm translucent bleed; weight 0.28 -> 0.40, scale 0.055 ->
        # 0.080 (still an order below the r2 wax washout).
        # fixer r5 blocker #7: stronger red-dominant SSS at ears/nose —
        # weight 0.40 -> 0.48, radius red channel up
        # Phase2 mat refine: face still reading chalk-white. Push SSS scale
        # up to 0.12 (larger diffusion = warmer glow through thin areas like
        # nose/ears); weight stays 0.48 but red radius increases to 0.72 so
        # the backlit ear warmth is more pronounced.
        # phase4 fixer r2 blocker #1 ("waxy uniform pale skin"): the 0.48 x
        # 0.12 SSS again diffused the facial forms toward wax. Weight and
        # scale CUT (0.48 -> 0.30, 0.12 -> 0.055) — the albedo variation +
        # lid darkening below carry the living read; SSS only warms the
        # thin features (nose/ears) now.
        pbsdf.inputs["Subsurface Weight"].default_value = 0.30
        pbsdf.inputs["Subsurface Radius"].default_value = (0.72, 0.12, 0.048)
        try:
            pbsdf.inputs["Subsurface Color"].default_value = sss_color
        except KeyError:
            pass
        try:
            pbsdf.inputs["Subsurface Scale"].default_value = 0.055
        except KeyError:
            pass
    except KeyError:
        try:
            pbsdf.inputs["Subsurface"].default_value = 0.62
            pbsdf.inputs["Subsurface Radius"].default_value = (0.32, 0.11, 0.055)
            pbsdf.inputs["Subsurface Color"].default_value = sss_color
        except KeyError:
            pass

    # Emission: SPEC color (1.0,0.88,0.45) @ strength 2.5, delivered through a
    # LOW MixShader factor so the effective radiance is 2.5 * 0.10 = 0.25 —
    # in the near-black void this makes Godwyn VISIBLY self-luminous (he is
    # the room's light source, blocker #4) while the Principled layer keeps
    # full 3D form (shadows, SSS). Not blown out; not a studio product shot.
    emit = _new_node(nt, "ShaderNodeEmission", (200, -200))
    mix  = _new_node(nt, "ShaderNodeMixShader", (480, 0))
    emit.inputs["Color"].default_value    = G.COL_SKIN_EMIT
    emit.inputs["Strength"].default_value = G.SKIN_EMIT_STR   # 2.5 per SPEC

    # Phase2 r2: fac REDUCED 0.10 -> 0.06 — face still blown out in r1.
    # RE-OUTFIT fixer r1 major #6: 0.06 -> 0.030 — the face still rendered
    # chalk-white/waxy (far lighter than SPEC 0.95,0.90,0.82). Halving the
    # self-glow lets the warm base + SSS read as living skin tone.
    # fixer r2 blocker #3: 0.020 -> 0.012 — still reading chalk-white
    # Phase2 mat refine: kept at 0.012 — emission is subtle, form is from SSS
    # phase4 fixer r1: 0.012 -> 0.006 — every photon of self-glow flattens
    # the facial forms; SSS carries the luminous-demigod read.
    mix.inputs["Fac"].default_value = 0.006
    _link(nt, pbsdf, "BSDF",     mix, 1)
    _link(nt, emit,  "Emission", mix, 2)
    _link(nt, mix,   "Shader",   out, "Surface")

    _set_disp_method(mat, "BUMP")   # game-safe: height renders as bump
    return mat


def make_underlayer_material() -> bpy.types.Material:
    """Padded arming-cloth under the plate (RE-OUTFIT fixer r1; refine
    pass: DEEP BLUE). Every sliver of body that peeks between plates now
    reads as the tabard's blue underlayer showing through the armor gaps
    (SPEC: 'blue cloth UNDERLAYER / accents showing between the gold
    plates') — a darkened cousin of Mat_Tabard's 0.08/0.12/0.35, matte,
    with a faint quilted weave bump. NO emission, never bare skin."""
    mat = bpy.data.materials.new("Mat_Underlayer")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = _new_node(nt, "ShaderNodeOutputMaterial", (600, 0))
    pb = _new_node(nt, "ShaderNodeBsdfPrincipled", (300, 0))
    pb.inputs["Base Color"].default_value = (0.040, 0.060, 0.180, 1.0)
    pb.inputs["Roughness"].default_value = 0.82
    pb.inputs["Metallic"].default_value = 0.0
    try:
        pb.inputs["Specular IOR Level"].default_value = 0.12
    except (KeyError, AttributeError):
        pass
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-600, -200))
    weave = _new_node(nt, "ShaderNodeTexWave", (-400, -200))
    weave.wave_type = "BANDS"
    weave.inputs["Scale"].default_value = 90.0
    weave.inputs["Distortion"].default_value = 1.5
    _link(nt, tex_c, "Object", weave, "Vector")
    _wire_displacement(nt, out, weave, "Fac", 0.0012, loc=(420, -300))
    _link(nt, pb, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_gold_material() -> bpy.types.Material:
    """
    Gold armor / hilt / crossguard — metallic PBR, faintly worn (SPEC 341).

    Node graph:
      Noise Texture (roughness variation)  →  Mix (map to 0.15-0.35)
             ↓ roughness
      Principled BSDF (metallic=1, slight anisotropy)
             ↓
      Material Output

    The roughness noise gives the "faintly worn" look without needing a
    painted texture map.
    """
    mat = bpy.data.materials.new("Mat_Gold")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial",  (800, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled",  (500, 0))
    tex_c = _new_node(nt, "ShaderNodeTexCoord",         (-1200, -100))

    pbsdf.inputs["Metallic"].default_value = 1.0
    # p5r1 #3: REAL anisotropic brushing — radial tangent + higher aniso so
    # highlights streak along the polish direction instead of dot-speckling.
    try:
        # fixer r3 blocker #3: the 0.28 radial-Z aniso rendered the greaves
        # as vertical WOOD-GRAIN streaks. Aniso cut to a faint 0.10 and the
        # rotation is VARIED by a low-freq noise so any residual streaking
        # curves/breaks instead of running straight down the plate.
        # fixer r4 major #5: STILL reading as wood grain on the fauld/tasset
        # plates — 0.10 -> 0.06 (barely-there forge polish).
        # phase4 fixer r1 major #4: 0.06 -> 0.13 — restore mild forge
        # anisotropy (the 0.06 read as uniform polished brass); the noise-
        # varied rotation below keeps it from going wood-grain.
        pbsdf.inputs["Anisotropic"].default_value          = 0.13
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    except KeyError:
        pass
    tang = _new_node(nt, "ShaderNodeTangent", (-1200, 140))
    tang.direction_type = "RADIAL"
    tang.axis = "Z"
    try:
        _link(nt, tang, "Tangent", pbsdf, "Tangent")
        rot_n = _new_node(nt, "ShaderNodeTexNoise", (-1200, 300))
        rot_n.inputs["Scale"].default_value = 2.5
        rot_n.inputs["Detail"].default_value = 2.0
        _link(nt, tex_c, "Object", rot_n, "Vector")
        rot_m = _map_range(nt, (-1000, 300), 0.30, 0.70, 0.02, 0.42)
        _link(nt, rot_n, "Fac", rot_m, "Value")
        _link(nt, rot_m, "Result", pbsdf, "Anisotropic Rotation")
    except KeyError:
        pass
    try:
        pbsdf.inputs["IOR"].default_value = 1.5
    except KeyError:
        pass

    # ---- MESO/MICRO masks --------------------------------------------------
    # Edge wear: curvature-driven via Geometry->Pointiness (narrow + smooth).
    # Recess grime: AO-driven (p5r1 #3 — pointiness alone was too noisy and
    # never actually darkened the concavities on the curve-built trim).
    geo = _new_node(nt, "ShaderNodeNewGeometry", (-1200, -400))
    # r2: wider edge-wear range catches more plate rim bevels (0.58-0.70 -> 0.55-0.72)
    # p4 r5 major #5 ("no visible convex-edge wear"): wider catch range
    edge_pt = _map_range(nt, (-1000, -340), 0.52, 0.74, 0.0, 1.0)  # convex edges
    _link(nt, geo, "Pointiness", edge_pt, "Value")
    # fixer r3 blocker #3: pointiness alone misses most rims on the lofted/
    # curve-built plates (it needs dense connected topology). A BEVEL-NODE
    # edge mask catches EVERY sharp rim regardless of topology: where the
    # 4mm-bevel normal deviates from the true normal, we are on an edge.
    bevn = _new_node(nt, "ShaderNodeBevel", (-1200, -240))
    # p4 r5 major #5: radius 0.0065 -> 0.0110 + softer threshold — every
    # chamfered rim carries a visible band of wear, not a hairline
    bevn.inputs["Radius"].default_value = 0.0110
    bevn.samples = 4
    dotp = _new_node(nt, "ShaderNodeVectorMath", (-1000, -240))
    dotp.operation = "DOT_PRODUCT"
    _link(nt, bevn, "Normal", dotp, 0)
    _link(nt, geo, "True Normal", dotp, 1)
    edge_bv = _map_range(nt, (-840, -240), 0.997, 0.90, 0.0, 1.0)
    nt.links.new(dotp.outputs["Value"], edge_bv.inputs["Value"])
    edge = _math(nt, "MAXIMUM", (-700, -300))
    _link(nt, edge_pt, "Result", edge, 0)
    _link(nt, edge_bv, "Result", edge, 1)
    # r2: deeper concave sensitivity for crevice grime (0.46-0.36 -> 0.50-0.34)
    crev = _map_range(nt, (-1000, -520), 0.50, 0.34, 0.0, 1.0)   # concave pits
    _link(nt, geo, "Pointiness", crev, "Value")
    ao = _new_node(nt, "ShaderNodeAmbientOcclusion", (-1200, -560))
    # fixer r3 blocker #3: deeper AO reach + wider ramp — plate-gap shadow
    # lines must READ at full-body distance (separate plates, not one shell)
    # fixer r4 major #5 ("no readable crevice grime at distance"): reach
    # 0.20 -> 0.35, wider ramp, then a 0.75 POWER (gamma-down) so mid-level
    # occlusion still registers as grime instead of vanishing.
    # p4 r5 major #5: 0.35 -> 0.45 — grime under plate overlaps must read
    ao.inputs["Distance"].default_value = 0.45
    ao.samples = 8
    ao_dark0 = _map_range(nt, (-1000, -620), 0.30, 0.92, 1.0, 0.0)  # 1=occl.
    _link(nt, ao, "AO", ao_dark0, "Value")
    ao_dark = _math(nt, "POWER", (-860, -620), None, 0.75)
    _link(nt, ao_dark0, "Result", ao_dark, 0)

    # Fine scratches (p5r1 #3): STRONGLY elongated along local Z so they
    # render as directional hairlines, not white paint-fleck dots.
    # fixer r3 blocker #3: the 0.12 z-stretch drew long straight vertical
    # streaks that read as WOOD GRAIN on the greaves — elongation relaxed
    # (0.12 -> 0.5) so scratches are short broken hairlines, not planks.
    sn = _stretched_noise(nt, tex_c, (-1000, -720),
                          mapping_scale=(26.0, 26.0, 0.5),
                          noise_scale=22.0, detail=3.0)
    scr_ramp = _new_node(nt, "ShaderNodeValToRGB", (-760, -720))
    scr_ramp.color_ramp.elements[0].position = 0.66   # p4 r2: sparser
    scr_ramp.color_ramp.elements[1].position = 0.71
    _link(nt, sn, "Fac", scr_ramp, "Fac")

    # Hammered/worn low-freq surface undulation
    ham = _new_node(nt, "ShaderNodeTexNoise", (-1000, -940))
    ham.inputs["Scale"].default_value = 22.0
    ham.inputs["Detail"].default_value = 5.0
    ham.inputs["Roughness"].default_value = 0.6
    _link(nt, tex_c, "Object", ham, "Vector")

    # ---- Base color: gold, burnished on worn edges, AO-darkened recesses --
    # fixer r4 major #5: edge-wear pushed to a clearly BRIGHTER worn tone
    # (full-fac, near-white gold) so every rim reads lightened at distance
    col_edge = _mix_color(nt, (-560, 60), G.COL_GOLD,
                          (1.0, 0.91, 0.46, 1.0))
    ef = _math(nt, "MULTIPLY", (-760, 60), None, 1.0)   # r4: full strength
    _link(nt, edge, "Value", ef, 0)
    _link_mix_fac(nt, ef, "Value", col_edge)
    col_grime = _mix_color(nt, (-360, 60), None,
                           (0.22, 0.14, 0.035, 1.0))  # crevice tarnish
    nt.links.new(_out_sock(col_edge, "Result_Color"),
                 _in_sock(col_grime, "A_Color"))
    gf = _math(nt, "MULTIPLY", (-560, -100), None, 1.0)   # p4 r5: full grime
    _link(nt, crev, "Result", gf, 0)
    _link_mix_fac(nt, gf, "Value", col_grime)
    # AO recess darkening (p5r1 #3): occluded areas fall toward dark grime
    col_ao = _mix_color(nt, (-160, 60), None, (0.16, 0.10, 0.03, 1.0))
    nt.links.new(_out_sock(col_grime, "Result_Color"),
                 _in_sock(col_ao, "A_Color"))
    af = _math(nt, "MULTIPLY", (-360, -140), None, 0.95)   # r4: stronger grime
    _link(nt, ao_dark, "Value", af, 0)
    _link_mix_fac(nt, af, "Value", col_ao)
    _link_mix_out(nt, col_ao, pbsdf, "Base Color")

    # ---- Roughness: worn plate base 0.26..0.44, polished edges, rough
    #      grime, scratches catch light -------------------------------------
    noise = _new_node(nt, "ShaderNodeTexNoise", (-760, -200))
    noise.inputs["Scale"].default_value      = 12.0
    noise.inputs["Detail"].default_value     = 4.0
    noise.inputs["Roughness"].default_value  = 0.65
    noise.inputs["Distortion"].default_value = 0.15
    _link(nt, tex_c, "Object", noise, "Vector")
    mapv = _map_range(nt, (-560, -200), 0.0, 1.0, 0.26, 0.44)
    _link(nt, noise, "Fac", mapv, "Value")
    # fixer r4 major #5: rims are WORN (bright + slightly matte-scuffed),
    # not mirror-polished — the roughness now RISES a touch on edges
    # p4 r5 major #5 ("factory-new gold"): convex-bevel wear is now
    # BRIGHTER + LOWER-ROUGHNESS (burnished by handling) — roughness DROPS
    # on edges so the rims catch crisp highlights at every camera.
    r_e = _math(nt, "MULTIPLY_ADD", (-380, -200), None, -0.14)
    _link(nt, edge, "Value", r_e, 0)
    _link(nt, mapv, "Result", r_e, 2)
    r_g = _math(nt, "MULTIPLY_ADD", (-220, -260), None, 0.32)   # grime rough
    _link(nt, crev, "Result", r_g, 0)
    _link(nt, r_e, "Value", r_g, 2)
    # p5r1 #3: scratch roughness boost dropped 0.22 -> 0.10 (the strong
    # per-fleck contrast was the "bird-dropping speckle")
    r_s = _math(nt, "MULTIPLY_ADD", (-60, -320), None, 0.06)    # p4 r4: calmer
    _link(nt, scr_ramp, "Color", r_s, 0)
    _link(nt, r_g, "Value", r_s, 2)
    # fixer r3 blocker #3 ("uniform mirror-smooth at distance"): MACRO
    # roughness breakup — a large-scale noise swings the roughness ±0.09 in
    # body-sized patches so the full-body specular read varies plate to plate
    macro_r = _new_node(nt, "ShaderNodeTexNoise", (-380, -420))
    macro_r.inputs["Scale"].default_value = 1.6
    macro_r.inputs["Detail"].default_value = 3.0
    _link(nt, tex_c, "Object", macro_r, "Vector")
    mr_c = _math(nt, "SUBTRACT", (-220, -420))
    _link(nt, macro_r, "Fac", mr_c, 0)
    mr_c.inputs[1].default_value = 0.5
    # p4 r5 major #5: low-freq roughness breakup 0.18 -> 0.30 — the
    # plate-to-plate specular must stop reading as uniform plastic
    r_mac = _math(nt, "MULTIPLY_ADD", (-60, -420), None, 0.30)
    _link(nt, mr_c, "Value", r_mac, 0)
    _link(nt, r_s, "Value", r_mac, 2)
    r_mn = _math(nt, "MINIMUM", (100, -320), None, 0.75)
    _link(nt, r_mac, "Value", r_mn, 0)
    r_cl = _math(nt, "MAXIMUM", (240, -320), None, 0.05)
    _link(nt, r_mn, "Value", r_cl, 0)
    _link(nt, r_cl, "Value", pbsdf, "Roughness")

    # ---- ENGRAVING (Phase2 refit): two-scale chased line-work —
    # RINGS wave at FINE scale (120.0) so the engraving reads as small
    # goldsmith work rather than huge corrugated bands (the old scale=24 on a
    # 3.2m figure produced 10cm-wide horizontal ridges = cheap corrugated tin).
    # A second BANDS wave runs perpendicular to vary the pattern (filigree grid).
    eng_w = _new_node(nt, "ShaderNodeTexWave", (-1000, -1100))
    eng_w.wave_type = "RINGS"
    # p4 r5 major #3 ("cuirass engraving reads as faint horizontal
    # tape-wrap scratches"): the 120-scale fine rings WERE the tape lines —
    # coarsened to 70 (~1.5cm goldsmith work) with deeper distortion so the
    # close-range detail curls like chased scrollwork.
    # (r5 iter-2: 5.6 still rendered as wavy horizontal stripes on the
    # cuirass — RINGS needs deep distortion to break into curls: -> 9.0)
    eng_w.inputs["Scale"].default_value = 70.0
    eng_w.inputs["Distortion"].default_value = 9.0  # phase4 r1: curlier (was
    # 2.8 — near-straight lines read as scratchy crosshatch, not scrollwork)
    try:
        eng_w.inputs["Detail"].default_value = 3.0
    except KeyError:
        pass
    _link(nt, tex_c, "Object", eng_w, "Vector")
    eng_ramp = _new_node(nt, "ShaderNodeValToRGB", (-760, -1100))
    # r2: tighten ramp 0.44-0.56 -> 0.47-0.53 for sharper, finer grooves
    eng_ramp.color_ramp.elements[0].position = 0.47
    eng_ramp.color_ramp.elements[1].position = 0.53
    _link(nt, eng_w, "Fac", eng_ramp, "Fac")

    # FILIGREE ACCENT: a finer bands wave perpendicular to the rings — produces
    # a crossing grid of chased lines that reads as intricate filigree work.
    fil_w = _new_node(nt, "ShaderNodeTexWave", (-1000, -1300))
    fil_w.wave_type = "BANDS"
    try:
        fil_w.bands_direction = "Y"
    except AttributeError:
        pass
    fil_w.inputs["Scale"].default_value = 55.0      # phase4 r1: coarser +
    fil_w.inputs["Distortion"].default_value = 6.5  # curlier — vine meander,
    # not a crosshatch grid
    try:
        fil_w.inputs["Detail"].default_value = 2.0
    except KeyError:
        pass
    _link(nt, tex_c, "Object", fil_w, "Vector")
    fil_ramp = _new_node(nt, "ShaderNodeValToRGB", (-760, -1300))
    # r2: tight bands = thin filigree lines
    fil_ramp.color_ramp.elements[0].position = 0.47
    fil_ramp.color_ramp.elements[1].position = 0.53
    _link(nt, fil_w, "Fac", fil_ramp, "Fac")

    # Combine: take the MAX of the two engraving patterns (union of grooves)
    eng_union = _math(nt, "MAXIMUM", (-560, -1200))
    _link(nt, eng_ramp, "Color", eng_union, 0)
    _link(nt, fil_ramp, "Color", eng_union, 1)

    # fixer r2 blocker #2: PURPOSEFUL ornament — the uniform all-over grid
    # read as texture noise, not goldsmith work. The engraving is now
    # CONCENTRATED at plate borders/rims (where pointiness deviates from
    # flat: rolled rims, trim ribs, chamfers, ridge crowns) and only faint
    # across open plate faces — Elden Ring's restrained border-filigree
    # language. border = union of convex-edge + concave-crease masks.
    border = _math(nt, "MAXIMUM", (-560, -1350))
    _link(nt, edge, "Value", border, 0)
    _link(nt, crev, "Result", border, 1)
    # phase4 fixer r2 major #3 ("crackle noise over every plate"): the r1
    # 0.32 floor spread the distorted wave union over the WHOLE surface —
    # that WAS the cracked-paint read. Floor cut to 0.04: open plate faces
    # are now a mostly-clean polished field; the chased line-work lives at
    # plate borders/rims only, and the STRUCTURED ornament (medallion,
    # laurel garland bands — 02_details geometry) carries the filigree.
    # phase4 fixer r3 major #3: floor 0.04 -> 0.08 (a touch more field
    # line-work) — the r2 field was so clean the gold read as plain brass.
    bmask = _math(nt, "MULTIPLY_ADD", (-420, -1350), None, 0.92, 0.08)
    _link(nt, border, "Value", bmask, 0)
    eng_masked = _math(nt, "MULTIPLY", (-420, -1200))
    _link(nt, eng_union, "Value", eng_masked, 0)
    _link(nt, bmask, "Value", eng_masked, 1)

    # phase4 fixer r3 major #3 ("engraving does not READ"): STRUCTURED
    # LAUREL SCROLL BANDS — horizontal band masks at the armor's key plate
    # heights (breastplate face, plackart, cuisse faces, greave shin) where
    # the BOLD scroll pattern below runs at FULL strength regardless of the
    # border mask, so deep-cut scroll bands read across the open plate
    # faces at Cam_Full range (deliberate goldsmith banding, not noise).
    sep_gz = _new_node(nt, "ShaderNodeSeparateXYZ", (-1000, -1650))
    _link(nt, tex_c, "Object", sep_gz, "Vector")
    band_nodes = []
    # final-proportion (post-remap) heights: pauldron/collar rim zone,
    # plackart face below the emblem, cuisse mid-face, greave mid-shin
    # p4 r4 major #5: bands widened ~1.5x so the scroll zones read at range
    # p4 r5 major #3: bands widened again (readable zones at 1280px full)
    for bz, bh in ((2.620, 0.085), (2.140, 0.085),
                   (1.320, 0.110), (0.640, 0.110)):
        b0 = _math(nt, "SUBTRACT", (-860, -1650 - 90 * len(band_nodes)),
                   None, bz)
        _link(nt, sep_gz, "Z", b0, 0)
        b1 = _math(nt, "ABSOLUTE", (-740, -1650 - 90 * len(band_nodes)))
        _link(nt, b0, "Value", b1, 0)
        b2 = _map_range(nt, (-620, -1650 - 90 * len(band_nodes)),
                        bh * 0.55, bh, 1.0, 0.0)
        _link(nt, b1, "Value", b2, "Value")
        band_nodes.append(b2)
    band_total = band_nodes[0]
    for bn in band_nodes[1:]:
        m = _math(nt, "MAXIMUM", (-480, -1700))
        _link(nt, band_total,
              "Result" if band_total.bl_idname == "ShaderNodeMapRange"
              else "Value", m, 0)
        _link(nt, bn, "Result", m, 1)
        band_total = m
    band_sock = ("Result" if band_total.bl_idname == "ShaderNodeMapRange"
                 else "Value")
    # bold-scroll gate = max(border mask, laurel band)
    bmask2 = _math(nt, "MAXIMUM", (-420, -1550))
    _link(nt, bmask, "Value", bmask2, 0)
    bscale = _math(nt, "MULTIPLY", (-560, -1550), None, 1.0)  # p4 r5: full
    _link(nt, band_total, band_sock, bscale, 0)
    _link(nt, bscale, "Value", bmask2, 1)

    # fixer r4 major #5 ("engraving too sparse to register at Cam_Full"):
    # a SECOND, LARGER-scale filigree band pattern (~5cm meander lines)
    # concentrated at the same plate borders — coarse enough to read at
    # full-body range, still restrained (border-masked, thin ramp).
    eng2_w = _new_node(nt, "ShaderNodeTexWave", (-1000, -1500))
    eng2_w.wave_type = "RINGS"
    # phase4 fixer r1 major #4 ("filigree invisible at Cam_Full"): the
    # large-scale band drops 18 -> 9 (~10cm meander) with deep distortion —
    # bold curling scroll lines that read at full-body distance.
    # phase4 fixer r4 major #5: 9.0 -> 6.0 (~15cm scrolls) — the bands
    # must survive to ~6m viewing distance
    # p4 r5 major #3 ("ornament invisible at Cam_Full; tape-wrap
    # scratches"): scale 6.0 -> 9.5 (~10cm motifs — the 8-12cm target that
    # reads at 4m) and distortion pulled back 5.5 -> 3.6 so the lines
    # stay COHERENT curling scrolls instead of smeared streaks.
    eng2_w.inputs["Scale"].default_value = 9.5
    # r5 iter-2: 3.6 read as horizontal wave stripes at Cam_Full — deeper
    # distortion breaks the rings into vine-scroll curls
    eng2_w.inputs["Distortion"].default_value = 5.2
    try:
        eng2_w.inputs["Detail"].default_value = 2.0
    except KeyError:
        pass
    _link(nt, tex_c, "Object", eng2_w, "Vector")
    eng2_ramp = _new_node(nt, "ShaderNodeValToRGB", (-760, -1500))
    eng2_ramp.color_ramp.elements[0].position = 0.42
    eng2_ramp.color_ramp.elements[1].position = 0.58
    _link(nt, eng2_w, "Fac", eng2_ramp, "Fac")
    eng2_masked = _math(nt, "MULTIPLY", (-420, -1500))
    _link(nt, eng2_ramp, "Color", eng2_masked, 0)
    # p4 r3: the bold scroll runs full-strength inside the laurel bands
    _link(nt, bmask2, "Value", eng2_masked, 1)
    eng_total = _math(nt, "MAXIMUM", (-300, -1300))
    _link(nt, eng_masked, "Value", eng_total, 0)
    _link(nt, eng2_masked, "Value", eng_total, 1)
    # p4 r4 major #5: ROUGHNESS CONTRAST — engraved line-work is matte
    # (chased metal) vs the polished field, so the pattern reads in the
    # specular at full-body distance. Relinks the Roughness socket.
    r_eng = _math(nt, "MULTIPLY_ADD", (380, -320), None, 0.22)
    _link(nt, eng_total, "Value", r_eng, 0)
    _link(nt, r_cl, "Value", r_eng, 2)
    _link(nt, r_eng, "Value", pbsdf, "Roughness")

    # phase4 fixer r3 major #3 ("uniform speckle dirt"): scratches are now
    # CREVICE/BORDER-WEIGHTED — wear collects at rims and recesses instead
    # of speckling open plate faces. scr_w replaces scr_ramp in the
    # roughness + height stacks (nt.links.new re-links occupied sockets).
    # phase4 fixer r4 major #3 ("torn-foil white flecks across every
    # plate"): the bmask FLOOR (0.08) leaked scratch flecks over the open
    # field. Scratches now gate on the curvature-convex EDGE mask ONLY —
    # zero field wear; mid-plate stays clean polished gold.
    scr_w = _math(nt, "MULTIPLY", (-420, -1600))
    _link(nt, scr_ramp, "Color", scr_w, 0)
    _link(nt, edge, "Value", scr_w, 1)
    _link(nt, scr_w, "Value", r_s, 0)     # re-link roughness scratch input
    # (the height-stack scratch node below links scr_w directly)

    # ---- Height: engraving grooves + scratch pits + hammered undulation ----
    h_h = _math(nt, "SUBTRACT", (-560, -940))
    _link(nt, ham, "Fac", h_h, 0)
    h_h.inputs[1].default_value = 0.5
    # fixer r5 blocker #11 ("pauldrons read as crumpled foil"): hammered
    # undulation amplitude cut 0.30 -> 0.10 — large plates must read as
    # smooth forged bowls; bevel-edge wear + engraving carry the detail.
    h1 = _math(nt, "MULTIPLY_ADD", (-380, -940), None, 0.10, 0.5)
    _link(nt, h_h, "Value", h1, 0)
    # p4 r2 major #3: scratch pits halved — with the engraving mask cut to
    # borders, the remaining scratch field must read as faint wear, never
    # a crackle texture.
    h2 = _math(nt, "MULTIPLY_ADD", (-200, -940), None, -0.10)   # p4 r4: edge-only wear
    _link(nt, scr_w, "Value", h2, 0)    # p4 r3: crevice-weighted scratches
    _link(nt, h1, "Value", h2, 2)
    h3 = _math(nt, "MULTIPLY_ADD", (-40, -1000), None, -0.85)   # engraved cuts
    _link(nt, eng_total, "Value", h3, 0)     # r4: fine + large-scale union
    _link(nt, h2, "Value", h3, 2)
    # fixer r2 blocker #2: 0.0030 -> 0.0055 — the relief was still invisible
    # even in the torso close-up (featureless polished brass read).
    # fixer r4 major #5: 0.0055 -> 0.0075 so the large-band ornament reads
    # at Cam_Full range.
    # fixer r5 blocker #11: 0.0075 -> 0.0052 — at 0.0075 the whole bump
    # stack (hammer+scratch+engraving) crinkled the big plates like foil.
    # phase4 r1: 0.0052 -> 0.0062 — the bolder scroll bands must relief-read
    # phase4 r2 major #3: 0.0062 -> 0.0048 — with the field now mostly
    # clean, the remaining border line-work reads at a calmer depth.
    # phase4 fixer r3 major #3 ("engraving does not READ in either
    # render"): relief 0.0048 -> 0.0080 — deep-cut chased work. The
    # crackle risk is gone because the field mask is border+laurel-band
    # weighted now, not all-over.
    # p4 r5 major #3: 0.0080 -> 0.0100 — the scroll bands must survive at
    # Cam_Full/1280px (normal strength up with the coarser motif scale).
    _wire_displacement(nt, out, h3, "Value", 0.0100, loc=(520, -520))

    # engraved grooves also collect grime (darken) — ties into the color mix
    # Phase2: INCREASED grime in grooves (0.55 -> 0.75) for better visual depth
    # p4 r3: CAVITY darkening — cuts hold near-black grime so the chased
    # line-work reads as engraved depth while the ridges stay bright
    g_eng = _mix_color(nt, (40, 60), None, (0.055, 0.032, 0.010, 1.0))  # p4 r4: near-black cavity
    nt.links.new(_out_sock(col_ao, "Result_Color"), _in_sock(g_eng, "A_Color"))
    egf = _math(nt, "MULTIPLY", (-40, -60), None, 1.0)            # r3: full
    _link(nt, eng_total, "Value", egf, 0)     # r4: both engraving scales
    _link_mix_fac(nt, egf, "Value", g_eng)

    # FILIGREE GOLD HIGHLIGHT: raised filigree ridges catch extra warm light
    # (the inverse of the grime — bright gold where the lines peak)
    g_fil = _mix_color(nt, (200, 60), None, (1.0, 0.88, 0.34, 1.0))  # p4 r4: brighter ridges
    nt.links.new(_out_sock(g_eng, "Result_Color"), _in_sock(g_fil, "A_Color"))
    fil_hi = _map_range(nt, (40, -120), 0.40, 0.55, 0.0, 1.0)       # only peaks
    _link(nt, eng_total, "Value", fil_hi, "Value")
    fhf = _math(nt, "MULTIPLY", (40, -180), None, 0.95)   # p4 r5: ridge pop
    _link(nt, fil_hi, "Result", fhf, 0)
    # p4 r4 major #3: ridge highlight GATED to border+band zones only (a
    # floor-free gate — the bmask 0.08 field floor was flecking mid-plate)
    fh_gate = _math(nt, "MAXIMUM", (100, -240))
    _link(nt, border, "Value", fh_gate, 0)
    _link(nt, bscale, "Value", fh_gate, 1)
    fhg = _math(nt, "MULTIPLY", (160, -180))
    _link(nt, fhf, "Value", fhg, 0)
    _link(nt, fh_gate, "Value", fhg, 1)
    _link_mix_fac(nt, fhg, "Value", g_fil)
    _link_mix_out(nt, g_fil, pbsdf, "Base Color")

    # fixer r3 blocker #3 ("one uniform polished tone at distance"): MACRO
    # TONE BREAKUP — a very-low-frequency noise shifts body-sized patches of
    # the gold toward a deeper old-gold tone. Final link wins the Base Color
    # socket (replaces the g_fil link above; g_fil feeds A).
    macro_n = _new_node(nt, "ShaderNodeTexNoise", (200, -300))
    macro_n.inputs["Scale"].default_value = 1.2
    macro_n.inputs["Detail"].default_value = 3.0
    _link(nt, tex_c, "Object", macro_n, "Vector")
    macro_f = _map_range(nt, (340, -300), 0.32, 0.68, 0.0, 0.28)
    _link(nt, macro_n, "Fac", macro_f, "Value")
    col_macro = _mix_color(nt, (380, 60), None, (0.55, 0.40, 0.095, 1.0))
    nt.links.new(_out_sock(g_fil, "Result_Color"),
                 _in_sock(col_macro, "A_Color"))
    _link_mix_fac(nt, macro_f, "Result", col_macro)
    _link_mix_out(nt, col_macro, pbsdf, "Base Color")

    _link(nt, pbsdf, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_robe_material() -> bpy.types.Material:
    """
    Deep blue flowing robe — cloth-ish, NO emission (SPEC 340).

    Principled BSDF: deep-blue base, moderate roughness, slight sheen
    for the flowing-fabric read.
    """
    mat = bpy.data.materials.new("Mat_Tabard")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-1100, -300))

    pbsdf.inputs["Metallic"].default_value = 0.0
    # NO emission (SPEC 340)
    # r2: specular raised 0.08->0.18 so the cape has subtle sheen (was too matte,
    # read as grey cardboard at render distance instead of rich wool/silk)
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.18
    except (KeyError, AttributeError):
        try:
            pbsdf.inputs["Specular"].default_value = 0.12
        except (KeyError, AttributeError):
            pass

    # Sheen for fabric fold micro-highlights (napped velvet-wool read)
    # r2: sheen weight reduced 0.55->0.35 to prevent grey wash-out
    # fixer r5 major #6: woven-cloth ANISOTROPY — the specular streaks along
    # the hang direction like woven fibre, not an isotropic rubber sheen
    # Phase2 mat refine: anisotropy reduced (was washing blue out toward grey).
    # Sheen kept for cloth read but tint is now deeper cobalt so grazing
    # highlights stay in the blue family rather than going grey/white.
    try:
        pbsdf.inputs["Anisotropic"].default_value = 0.20  # reduced: was causing grey cast
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.25
        _ctan = _new_node(nt, "ShaderNodeTangent", (-300, 420))
        _ctan.direction_type = "RADIAL"
        _ctan.axis = "Z"
        _link(nt, _ctan, "Tangent", pbsdf, "Tangent")
    except KeyError:
        pass
    try:
        # fixer r3 major #4 ("stiff felt/rubber"): sheen raised 0.35 -> 0.55
        # — the grazing-angle nap lift is what sells woven cloth vs rubber
        # fixer r5 major #6: 0.55 -> 0.65, sheen roughness 0.50 -> 0.38
        # Phase2 mat refine: sheen weight 0.65 -> 0.50, tint deepened to cobalt
        # to prevent the blue from washing out to periwinkle at grazing angles.
        pbsdf.inputs["Sheen Weight"].default_value = 0.50
        pbsdf.inputs["Sheen Roughness"].default_value = 0.42
        # Sheen tint: deep cobalt, not pale — keeps grazing angles in deep blue
        try:
            pbsdf.inputs["Sheen Tint"].default_value = (0.08, 0.14, 0.55, 1.0)
        except KeyError:
            pass
    except KeyError:
        try:
            pbsdf.inputs["Sheen"].default_value = 0.25
        except KeyError:
            pass

    # ---- MICRO: thread weave (two crossed band waves, object coords) ------
    def _wave(loc, direction):
        w = _new_node(nt, "ShaderNodeTexWave", loc)
        w.wave_type = "BANDS"
        try:
            w.bands_direction = direction
        except AttributeError:
            pass
        w.inputs["Scale"].default_value = 110.0   # p5r1 #8: coarser threads
        w.inputs["Distortion"].default_value = 4.0
        try:
            w.inputs["Detail"].default_value = 2.0
        except KeyError:
            pass
        _link(nt, tex_c, "Object", w, "Vector")
        return w

    w_warp = _wave((-900, -300), "X")   # warp threads
    w_weft = _wave((-900, -480), "Z")   # weft threads (robe hangs along Z)
    weave = _math(nt, "ADD", (-700, -380))
    _link(nt, w_warp, "Fac", weave, 0)
    _link(nt, w_weft, "Fac", weave, 1)
    weave_h = _math(nt, "MULTIPLY", (-540, -380), None, 0.5)   # 0..1
    _link(nt, weave, "Value", weave_h, 0)

    # Cloth nap (fuzzy micro noise)
    nap = _new_node(nt, "ShaderNodeTexNoise", (-900, -680))
    nap.inputs["Scale"].default_value = 28.0
    nap.inputs["Detail"].default_value = 6.0
    _link(nt, tex_c, "Object", nap, "Vector")

    # Height = 0.5 + 0.30*(weave-0.5) + 0.18*(nap-0.5)
    wv_c = _math(nt, "SUBTRACT", (-380, -380)); _link(nt, weave_h, "Value", wv_c, 0); wv_c.inputs[1].default_value = 0.5
    np_c = _math(nt, "SUBTRACT", (-380, -680)); _link(nt, nap, "Fac", np_c, 0); np_c.inputs[1].default_value = 0.5
    h1 = _math(nt, "MULTIPLY_ADD", (-220, -380), None, 0.45, 0.5)
    _link(nt, wv_c, "Value", h1, 0)
    h2 = _math(nt, "MULTIPLY_ADD", (-60, -480), None, 0.18)
    _link(nt, np_c, "Value", h2, 0)
    _link(nt, h1, "Value", h2, 2)
    # fixer r3 major #4: WRINKLE-SCALE bump — a mid-frequency noise layer
    # (between the mesh folds and the thread weave) breaks the smooth bell
    # walls into soft cloth crumple that reads at render distance
    wrk = _new_node(nt, "ShaderNodeTexNoise", (-380, -840))
    wrk.inputs["Scale"].default_value = 6.5
    wrk.inputs["Detail"].default_value = 4.0
    wrk.inputs["Roughness"].default_value = 0.55
    _link(nt, tex_c, "Object", wrk, "Vector")
    wr_c = _math(nt, "SUBTRACT", (-220, -840))
    _link(nt, wrk, "Fac", wr_c, 0)
    wr_c.inputs[1].default_value = 0.5
    # fixer r4 minor #6: wrinkle contribution 0.55 -> 0.80 + deeper overall
    # bump so the cloth crumple reads against the new sculpted folds
    h3 = _math(nt, "MULTIPLY_ADD", (-60, -720), None, 0.80)
    _link(nt, wr_c, "Value", h3, 0)
    _link(nt, h2, "Value", h3, 2)

    # ---- LAUREL EMBROIDERY BORDER (phase4 fixer r2 major #4) --------------
    # The physical piping cords are gone (02_details). The gold laurel
    # motif is now DRAWN as a stitched texture band in the panel's
    # "TabardUV" space: a garland of alternating leaf lenses along each
    # side edge and the hem, plus a thin continuous stem line. Gold color
    # + metallic + raised stitch bump — reads as embroidery, not rope.
    uvn = _new_node(nt, "ShaderNodeUVMap", (-1500, 700))
    uvn.uv_map = "TabardUV"
    uv_sep = _new_node(nt, "ShaderNodeSeparateXYZ", (-1320, 700))
    _link(nt, uvn, "UV", uv_sep, "Vector")

    def _leaf_band(cl_val, coord_sock_name, along_sock_name, n_rep, ybase,
                   halfw=0.032):
        """phase4 fixer r4 major #4 ("chunky gold zigzag rickrack — no leaf
        shapes readable"): a REAL repeating laurel leaf-pair garland. The
        across coordinate s = (coord-cl)/halfw; the along coordinate splits
        into n_rep CELLS; each cell grows ONE elongated leaf (lens profile
        sin(pi*a)^0.75, clearly longer than tall) on a side that ALTERNATES
        with cell parity, attached to a thin continuous central stem — the
        classic laurel garland, not a sawtooth strip."""
        d0 = _math(nt, "SUBTRACT", (-1160, ybase), None, cl_val)
        _link(nt, uv_sep, coord_sock_name, d0, 0)
        s_n = _math(nt, "DIVIDE", (-1020, ybase), None, halfw)   # signed
        _link(nt, d0, "Value", s_n, 0)
        acr = _math(nt, "ABSOLUTE", (-880, ybase))
        _link(nt, s_n, "Value", acr, 0)
        # along-cells: cell index + in-cell coordinate a (0..1)
        al0 = _math(nt, "MULTIPLY", (-1160, ybase - 120), None, float(n_rep))
        _link(nt, uv_sep, along_sock_name, al0, 0)
        cell = _math(nt, "FLOOR", (-1020, ybase - 120))
        _link(nt, al0, "Value", cell, 0)
        a_in = _math(nt, "SUBTRACT", (-880, ybase - 120))
        _link(nt, al0, "Value", a_in, 0)
        _link(nt, cell, "Value", a_in, 1)
        # leaf side alternates with cell parity: -1 / +1
        par = _math(nt, "MODULO", (-1020, ybase - 210), None, 2.0)
        _link(nt, cell, "Value", par, 0)
        side = _math(nt, "MULTIPLY_ADD", (-880, ybase - 210), None, 2.0, -1.0)
        _link(nt, par, "Value", side, 0)
        s_side = _math(nt, "MULTIPLY", (-740, ybase - 60))
        _link(nt, s_n, "Value", s_side, 0)
        _link(nt, side, "Value", s_side, 1)
        # elongated lens: leaf outer edge = 0.14 + 0.72*sin(pi*a)^0.75
        a_pi = _math(nt, "MULTIPLY", (-740, ybase - 160), None, math.pi)
        _link(nt, a_in, "Value", a_pi, 0)
        a_sin = _math(nt, "SINE", (-600, ybase - 160))
        _link(nt, a_pi, "Value", a_sin, 0)
        a_pw = _math(nt, "POWER", (-460, ybase - 160), None, 0.75)
        _link(nt, a_sin, "Value", a_pw, 0)
        w_out = _math(nt, "MULTIPLY_ADD", (-320, ybase - 160), None, 0.72,
                      0.14)
        _link(nt, a_pw, "Value", w_out, 0)
        gI = _math(nt, "GREATER_THAN", (-460, ybase - 40), None, 0.14)
        _link(nt, s_side, "Value", gI, 0)
        lO = _math(nt, "LESS_THAN", (-320, ybase - 40))
        _link(nt, s_side, "Value", lO, 0)
        _link(nt, w_out, "Value", lO, 1)
        leaf = _math(nt, "MULTIPLY", (-200, ybase - 40))
        _link(nt, gI, "Value", leaf, 0)
        _link(nt, lO, "Value", leaf, 1)
        # continuous central stem (p4 r5: thicker — must read as a gold
        # cord at the tabard camera, not a hairline)
        st = _math(nt, "LESS_THAN", (-600, ybase - 260), None, 0.105)
        _link(nt, acr, "Value", st, 0)
        mx = _math(nt, "MAXIMUM", (-80, ybase))
        _link(nt, leaf, "Value", mx, 0)
        _link(nt, st, "Value", mx, 1)
        return mx

    # p4 r3: bands widened to a real 40-55mm embroidered border (u-space
    # halfw 0.085 ~= 26mm half-width at the hem width; hem v-space 0.024
    # ~= 47mm) and pulled slightly in from the raw cloth edge so the
    # garland reads as a bordered band, not edge piping.
    # p4 r4 major #4: border bands NARROWED ~30% (halfw 0.085 -> 0.060)
    # p4 r5 major #4 ("thin gold squiggle/piping"): band WIDENED ~2x
    # (halfw 0.060 -> 0.115) and leaf count DROPPED 26 -> 16 so each
    # leaf-pair motif lands at ~50-60mm and resolves at the tabard camera.
    ebL = _leaf_band(0.105, "X", "Y", 16, 800, halfw=0.115)   # left border
    ebR = _leaf_band(0.895, "X", "Y", 16, 500, halfw=0.115)   # right border
    # hem garland sits ABOVE the scalloped bottom edge (iter-2: overlapping
    # the scallop made the leaves read as sawtooth fringe teeth)
    # (hem leaves LONGER than tall — n_rep 10 over a 35mm band — or they
    # render as vertical sawtooth teeth at the hem)
    # p4 r5 major #4 ("faint zigzag at the hem"): hem band DOUBLED in
    # width (halfw 0.010 -> 0.021 v-units ~ 40mm) and densified 12 -> 18
    # leaves — a continuous garland, not a zigzag remnant.
    ebH = _leaf_band(0.895, "Y", "X", 18, 200, halfw=0.021)   # hem border
    # hem band must not extend past the side borders' outer edge: gate the
    # hem mask to 0.02 < u < 0.98 (cheap clamp via two LESS/GREATER)
    g0 = _math(nt, "GREATER_THAN", (-460, 80), None, 0.02)
    _link(nt, uv_sep, "X", g0, 0)
    g1 = _math(nt, "LESS_THAN", (-460, -20), None, 0.98)
    _link(nt, uv_sep, "X", g1, 0)
    gh = _math(nt, "MULTIPLY", (-320, 30))
    _link(nt, g0, "Value", gh, 0)
    _link(nt, g1, "Value", gh, 1)
    ebH2 = _math(nt, "MULTIPLY", (-320, 200))
    _link(nt, ebH, "Value", ebH2, 0)
    _link(nt, gh, "Value", ebH2, 1)
    eb01 = _math(nt, "MAXIMUM", (-180, 650))
    _link(nt, ebL, "Value", eb01, 0)
    _link(nt, ebR, "Value", eb01, 1)
    emb = _math(nt, "MAXIMUM", (-40, 650))
    _link(nt, eb01, "Value", emb, 0)
    _link(nt, ebH2, "Value", emb, 1)

    # metallic gold threads where embroidered (color mix joins the base-
    # color chain below, after nap_col exists)
    _link(nt, emb, "Value", pbsdf, "Metallic")
    # p4 r3: STITCH-DIRECTION detail — a fine directional ripple confined
    # to the embroidered band so the gold reads as laid thread runs
    # (satin-stitch), not flat gold paint.
    stw = _new_node(nt, "ShaderNodeTexWave", (-140, -900))
    stw.wave_type = "BANDS"
    try:
        stw.bands_direction = "DIAGONAL"
    except (AttributeError, TypeError):
        pass
    stw.inputs["Scale"].default_value = 420.0
    stw.inputs["Distortion"].default_value = 1.2
    _link(nt, tex_c, "Object", stw, "Vector")
    st_c = _math(nt, "SUBTRACT", (20, -900))
    _link(nt, stw, "Fac", st_c, 0)
    st_c.inputs[1].default_value = 0.5
    st_m = _math(nt, "MULTIPLY", (160, -900))
    _link(nt, st_c, "Value", st_m, 0)
    _link(nt, emb, "Value", st_m, 1)
    # p4 r5 major #4: stitch-direction relief up 0.14 -> 0.24 — the laid
    # thread runs must shade so leaves resolve as embroidery
    st_h = _math(nt, "MULTIPLY_ADD", (300, -900), None, 0.24)
    _link(nt, st_m, "Value", st_h, 0)
    # stitched threads sit proud of the cloth
    h4 = _math(nt, "MULTIPLY_ADD", (80, -720), None, 0.40)
    _link(nt, emb, "Value", h4, 0)
    _link(nt, h3, "Value", h4, 2)
    _link(nt, h4, "Value", st_h, 2)
    _wire_displacement(nt, out, st_h, "Value", 0.0130, loc=(520, -520))

    # ---- Base color: SPEC deep indigo (0.08,0.12,0.35) — AgX FIX
    # Problem: AgX tonemapping lifts deep-shadow values substantially, so
    # COL_ROBE (0.08,0.12,0.35) rendered as medium periwinkle in earlier passes.
    # Fix: keep the SPEC base value exactly, clamp the dye lift ABOVE it to a
    # VERY narrow range (no more than 0.04 lift in each channel), and DEEPEN
    # the fold-shadow tone so the cloth reads as rich night-indigo under AgX.
    # The nap ramp now lifts only faintly so grazing angles show iridescent
    # midnight blue (not grey and not the periwinkle from over-lifting the base).
    dye = _new_node(nt, "ShaderNodeTexNoise", (-900, 160))
    dye.inputs["Scale"].default_value = 3.5       # broader dye patches
    dye.inputs["Detail"].default_value = 4.0
    _link(nt, tex_c, "Object", dye, "Vector")
    # COL_ROBE is (0.08,0.12,0.35) — the SPEC deep indigo; lifted shade kept
    # close (0.10,0.15,0.42) so AgX output stays clearly dark blue, not medium.
    col = _mix_color(nt, (-540, 160), G.COL_ROBE,
                     (0.10, 0.15, 0.42, 1.0))     # close lifted shade, AgX-safe
    dfac = _map_range(nt, (-700, 160), 0.25, 0.75, 0.0, 0.18)  # NARROW lift range
    _link(nt, dye, "Fac", dfac, "Value")
    _link_mix_fac(nt, dfac, "Result", col)

    # Shadow depth: stronger fold-shadow darkening to fight AgX lift.
    # Folds pull toward near-black indigo so the cloth reads with depth.
    fold_n = _new_node(nt, "ShaderNodeTexNoise", (-900, -80))
    fold_n.inputs["Scale"].default_value = 1.8    # large fold-scale
    fold_n.inputs["Detail"].default_value = 3.0
    _link(nt, tex_c, "Object", fold_n, "Vector")
    # Deeper shadow tone (0.015, 0.025, 0.10) = very dark indigo shadow
    col_dark = _mix_color(nt, (-340, 60), None, (0.015, 0.025, 0.10, 1.0))
    nt.links.new(_out_sock(col, "Result_Color"), _in_sock(col_dark, "A_Color"))
    # Stronger fold shadow fac (0.40 -> 0.55) so deep folds stay dark indigo
    dfold = _map_range(nt, (-520, -80), 0.20, 0.55, 0.0, 0.55)
    _link(nt, fold_n, "Fac", dfold, "Value")
    _link_mix_fac(nt, dfold, "Result", col_dark)

    # Nap ramp: grazing angles lift very faintly to midnight-blue.
    # REDUCED lift fac (0.45 -> 0.22) so we don't wash the dark base out.
    lw = _new_node(nt, "ShaderNodeLayerWeight", (-540, 320))
    lw.inputs["Blend"].default_value = 0.20
    # Nap lift color closer to the base indigo (not a bright cerulean)
    nap_col = _mix_color(nt, (-340, 200), None, (0.12, 0.18, 0.50, 1.0))
    nt.links.new(_out_sock(col_dark, "Result_Color"), _in_sock(nap_col, "A_Color"))
    nf = _math(nt, "MULTIPLY", (-540, 460), None, 0.22)  # restrained nap lift
    _link(nt, lw, "Facing", nf, 0)
    _link_mix_fac(nt, nf, "Value", nap_col)
    # p4 r2 major #4: gold laurel EMBROIDERY color (SPEC 0.82,0.65,0.15)
    # over the cloth base, masked by the TabardUV border band built above
    emb_col = _mix_color(nt, (140, 320), None, (0.82, 0.65, 0.15, 1.0))
    nt.links.new(_out_sock(nap_col, "Result_Color"),
                 _in_sock(emb_col, "A_Color"))
    _link_mix_fac(nt, emb, "Value", emb_col)
    _link_mix_out(nt, emb_col, pbsdf, "Base Color")
    # p4 r4 major #4: TWO-TONE gold thread — patches of the garland lift
    # toward a paler gold (mixed-thread embroidery read), confined to the
    # stitched band. Final link wins Base Color.
    tt_n = _new_node(nt, "ShaderNodeTexNoise", (60, 500))
    tt_n.inputs["Scale"].default_value = 34.0
    tt_n.inputs["Detail"].default_value = 2.0
    _link(nt, tex_c, "Object", tt_n, "Vector")
    # p4 r5 major #4: two-tone contrast raised — pale thread patches lift
    # to a bright near-white gold so the garland separates from the blue
    tt_m = _map_range(nt, (200, 500), 0.38, 0.62, 0.0, 0.95)
    _link(nt, tt_n, "Fac", tt_m, "Value")
    tt_f = _math(nt, "MULTIPLY", (340, 500))
    _link(nt, emb, "Value", tt_f, 0)
    _link(nt, tt_m, "Result", tt_f, 1)
    emb_col2 = _mix_color(nt, (420, 320), None, (1.0, 0.90, 0.46, 1.0))
    nt.links.new(_out_sock(emb_col, "Result_Color"),
                 _in_sock(emb_col2, "A_Color"))
    _link_mix_fac(nt, tt_f, "Value", emb_col2)
    _link_mix_out(nt, emb_col2, pbsdf, "Base Color")

    # ---- Roughness: matte cloth 0.68..0.88, slightly lowered for better
    # contrast — very high roughness (>0.85) scatters highlights too broadly
    # and competes with the deep-blue saturation (reads grey at distance).
    rmap = _map_range(nt, (-220, -120), 0.0, 1.0, 0.62, 0.84)
    _link(nt, nap, "Fac", rmap, "Value")
    # fixer r5 major #6: thread-weave micro-roughness modulation — the
    # crossed warp/weft pattern breaks the specular into woven texture
    r_wv = _math(nt, "MULTIPLY_ADD", (-60, -120), None, 0.16)
    _link(nt, wv_c, "Value", r_wv, 0)
    _link(nt, rmap, "Result", r_wv, 2)
    # p4 r2: gold embroidery threads are glossier than the wool —
    # lerp roughness toward 0.34 inside the stitched band
    r_om = _math(nt, "SUBTRACT", (80, -120), 1.0)
    _link(nt, emb, "Value", r_om, 1)
    r_a = _math(nt, "MULTIPLY", (220, -120))
    _link(nt, r_wv, "Value", r_a, 0)
    _link(nt, r_om, "Value", r_a, 1)
    r_b = _math(nt, "MULTIPLY_ADD", (360, -120), None, 0.34)
    _link(nt, emb, "Value", r_b, 0)
    _link(nt, r_a, "Value", r_b, 2)
    _link(nt, r_b, "Value", pbsdf, "Roughness")

    _link(nt, pbsdf, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_blade_material() -> bpy.types.Material:
    """
    Sword blade — polished steel + subtle blue tint + faint glow (SPEC 317).

    Round-2 rebuild (major #6): the old MixShader(steel, dim-emission)
    DARKENED the metal — the blade read as flat navy plastic. Now it is a
    single Principled BSDF: metallic=1, LOW roughness (real specular steel),
    lighter blue-steel base, with the faint blue emission delivered through
    the Principled emission inputs (strength 0.12 — far below the skin's
    effective glow) so it never dims the metal reflections.
    """
    mat = bpy.data.materials.new("Mat_Blade")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    # r3 major #4: at roughness 0.10 in a black void a perfect mirror has
    # nothing to reflect — the blade rendered near-black. Lighter steel base,
    # broader highlight lobe, and a stronger (still << skin) blue emission so
    # the edge reads against the void.
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-900, -200))
    # phase4 fixer r2 minor #7: blue tint STRENGTHENED (0.78,0.82,0.92 was
    # near-neutral steel at full-body range) — a clearly blue-tinged blade
    # without emission carrying the read.
    pbsdf.inputs["Base Color"].default_value = (0.55, 0.66, 0.92, 1.0)
    pbsdf.inputs["Metallic"].default_value   = 1.0
    try:
        pbsdf.inputs["Anisotropic"].default_value = 0.55   # forged/brushed grain
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    except KeyError:
        pass
    # faint blue emission INSIDE the BSDF (Blender 4+), << skin (0.55 eff.)
    try:
        pbsdf.inputs["Emission Color"].default_value = G.COL_BLADE_EMIT
        pbsdf.inputs["Emission Strength"].default_value = 0.40  # p4 r2
    except KeyError:
        pass

    # ---- MICRO: brushed grain along the blade (local Z = blade length) ----
    grain = _stretched_noise(nt, tex_c, (-700, -200),
                             mapping_scale=(40.0, 40.0, 0.6),
                             noise_scale=16.0, detail=4.0)
    rmap = _map_range(nt, (-300, -120), 0.0, 1.0, 0.16, 0.34)
    _link(nt, grain, "Fac", rmap, "Value")
    _link(nt, rmap, "Result", pbsdf, "Roughness")

    # Sparse battle nicks: thresholded second noise, pits in the height
    nick = _new_node(nt, "ShaderNodeTexNoise", (-700, -440))
    nick.inputs["Scale"].default_value = 30.0
    nick.inputs["Detail"].default_value = 3.0
    _link(nt, tex_c, "Object", nick, "Vector")
    nick_ramp = _new_node(nt, "ShaderNodeValToRGB", (-500, -440))
    nick_ramp.color_ramp.elements[0].position = 0.70
    nick_ramp.color_ramp.elements[1].position = 0.74
    _link(nt, nick, "Fac", nick_ramp, "Fac")

    # Height = 0.5 + 0.18*(grain-0.5) - 0.45*nick
    g_c = _math(nt, "SUBTRACT", (-300, -300)); _link(nt, grain, "Fac", g_c, 0); g_c.inputs[1].default_value = 0.5
    h1 = _math(nt, "MULTIPLY_ADD", (-140, -300), None, 0.18, 0.5)
    _link(nt, g_c, "Value", h1, 0)
    h2 = _math(nt, "MULTIPLY_ADD", (20, -380), None, -0.45)
    _link(nt, nick_ramp, "Color", h2, 0)
    _link(nt, h1, "Value", h2, 2)
    _wire_displacement(nt, out, h2, "Value", 0.0004, loc=(260, -520))

    _link(nt, pbsdf, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_hair_material() -> bpy.types.Material:
    """
    Golden-blonde hair — lighter/less-saturated than armor gold (SPEC 299).

    Principled BSDF with anisotropic sheen (approximates hair specularity
    on mesh tubes), COL_HAIR is (0.75,0.58,0.08) — same hue family as
    armor gold but brighter/less saturated.
    """
    mat = bpy.data.materials.new("Mat_Hair")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-1100, -200))

    pbsdf.inputs["Metallic"].default_value = 0.0

    # Anisotropy → hair-like directional sheen along the strands
    # p5b fixer r3 blocker #2: explicit RADIAL-Z tangent + 0.25 rotation so
    # the anisotropic highlight streaks ALONG the (mostly vertical) strands
    # instead of using an undefined default tangent.
    try:
        # p4 r4 blocker #2 ("diffuse clay look"): aniso 0.80 -> 0.92 —
        # a real tangent-shifted sheen band along the strands
        pbsdf.inputs["Anisotropic"].default_value          = 0.92
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.25
        tan = _new_node(nt, "ShaderNodeTangent", (-300, 260))
        tan.direction_type = "RADIAL"
        tan.axis = "Z"
        _link(nt, tan, "Tangent", pbsdf, "Tangent")
        # fixer r3 blocker #1 ("clay" hair): PER-LOCK highlight breakup —
        # a lock-scale noise varies the anisotropic rotation so the specular
        # band breaks up strand to strand instead of one clay sheen.
        # fixer r4 blocker #7: STRONGER per-lock aniso variation (wider
        # rotation swing, finer noise) — the single clay sheen band breaks
        # into per-lock highlights.
        lk_n = _new_node(nt, "ShaderNodeTexNoise", (-500, 380))
        lk_n.inputs["Scale"].default_value = 34.0
        lk_n.inputs["Detail"].default_value = 2.0
        _link(nt, tex_c, "Object", lk_n, "Vector")
        lk_m = _map_range(nt, (-300, 380), 0.30, 0.70, 0.02, 0.58)
        _link(nt, lk_n, "Fac", lk_m, "Value")
        _link(nt, lk_m, "Result", pbsdf, "Anisotropic Rotation")
    except KeyError:
        pass

    # Subtle specular boost so the gold reads at render distance
    # p4 r4 blocker #2: spec up + a low-rough COAT — the secondary
    # tangent-shifted sheen band that sells FromSoft hair
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.75
    except KeyError:
        try:
            pbsdf.inputs["Specular"].default_value = 0.50
        except KeyError:
            pass
    try:
        # p4 r5 blocker #2: stronger anisotropic sheen band — coat up
        pbsdf.inputs["Coat Weight"].default_value = 0.45
        pbsdf.inputs["Coat Roughness"].default_value = 0.10
    except KeyError:
        pass

    # ---- MICRO: strand-direction streaks (elongated along Z — hair falls
    #      vertically; the mapping stretch follows the fall direction) ------
    # p5r2 major #4: stronger directional read — features stretched harder
    # along the fall (Z) so the scalp cap shades as combed strands, not a
    # smooth shell.
    strand = _stretched_noise(nt, tex_c, (-900, -200),
                              mapping_scale=(80.0, 80.0, 1.4),
                              noise_scale=10.0, detail=5.0)

    # Strand-to-strand color depth: base blonde <-> darker root/shadow tone,
    # with a narrow bright band for individual catching-the-light strands.
    # fixer r5 blocker #7 ("uniform khaki tone"): base DESATURATED toward a
    # true golden-blonde (the old COL_HAIR G/B ratio read as khaki clay),
    # shadow strands deeper brown
    # p4 r5 blocker #2 ("muddy tan-gold, not golden-blonde"): base albedo
    # LIFTED + warmed toward true golden blonde; shadow strands stay a warm
    # brown; strand-darkening fac cut so the mass stops reading as clay.
    dark_mix = _mix_color(nt, (-420, 60), (0.84, 0.64, 0.24, 1.0),
                          (0.36, 0.23, 0.075, 1.0))
    dk = _map_range(nt, (-620, 60), 0.28, 0.72, 0.0, 0.60)
    _link(nt, strand, "Fac", dk, "Value")
    _link_mix_fac(nt, dk, "Result", dark_mix)
    hi_ramp = _new_node(nt, "ShaderNodeValToRGB", (-620, -80))
    hi_ramp.color_ramp.elements[0].position = 0.72
    hi_ramp.color_ramp.elements[1].position = 0.80
    _link(nt, strand, "Fac", hi_ramp, "Fac")
    hi_mix = _mix_color(nt, (-220, 60), None,
                        (0.95, 0.80, 0.42, 1.0))   # p4 r4: golden lit strand
    nt.links.new(_out_sock(dark_mix, "Result_Color"),
                 _in_sock(hi_mix, "A_Color"))
    hf = _math(nt, "MULTIPLY", (-420, -80), None, 0.85)  # p4 r5: lit strands
    _link(nt, hi_ramp, "Color", hf, 0)
    _link_mix_fac(nt, hf, "Value", hi_mix)
    # fixer r4 blocker #7 ("smooth clay ribbons"): ROOT-TO-TIP RAMP — hair
    # darkens toward the roots/crown (world Z; roots live above z~2.85) so
    # the mass reads with depth instead of one flat blonde value.
    sep_z = _new_node(nt, "ShaderNodeSeparateXYZ", (-620, 260))
    _link(nt, tex_c, "Object", sep_z, "Vector")
    # p4 r5 blocker #2: STRONGER root-to-tip value gradient (0.55 -> 0.72)
    # — dark roots at the crown falling to bright lit blonde at the tips
    root_f = _map_range(nt, (-420, 260), 2.40, 3.04, 0.0, 0.72)
    _link(nt, sep_z, "Z", root_f, "Value")
    root_mix = _mix_color(nt, (-60, 60), None, (0.155, 0.105, 0.045, 1.0))
    nt.links.new(_out_sock(hi_mix, "Result_Color"),
                 _in_sock(root_mix, "A_Color"))
    _link_mix_fac(nt, root_f, "Result", root_mix)
    # phase4 fixer r1 blocker #2 ("uniform putty color"): PER-LOCK HUE
    # JITTER — a lock-scale cell noise swings neighbouring locks between a
    # warm honey and a cooler ash blonde so the mass reads as thousands of
    # hairs, not one clay material. Final link wins Base Color.
    # phase4 fixer r3 blocker #2 ("carved wooden wig"): jitter frequency
    # raised toward per-STRAND scale (26 -> 55) so neighbouring sub-strands
    # split tonally, and the same noise drives a roughness jitter below —
    # the highlight breaks into individual lit strands, not one clay sheen.
    hue_n = _new_node(nt, "ShaderNodeTexNoise", (-260, 420))
    hue_n.inputs["Scale"].default_value = 55.0
    hue_n.inputs["Detail"].default_value = 2.0
    _link(nt, tex_c, "Object", hue_n, "Vector")
    hue_warm = _mix_color(nt, (80, 60), None, (0.78, 0.55, 0.16, 1.0))  # p4 r4: honey
    nt.links.new(_out_sock(root_mix, "Result_Color"),
                 _in_sock(hue_warm, "A_Color"))
    hw_f = _map_range(nt, (-80, 420), 0.55, 0.80, 0.0, 0.55)
    _link(nt, hue_n, "Fac", hw_f, "Value")
    _link_mix_fac(nt, hw_f, "Result", hue_warm)
    hue_ash = _mix_color(nt, (240, 60), None, (0.58, 0.47, 0.24, 1.0))  # p4 r4: warmer ash
    nt.links.new(_out_sock(hue_warm, "Result_Color"),
                 _in_sock(hue_ash, "A_Color"))
    ha_f = _map_range(nt, (60, 420), 0.45, 0.20, 0.0, 0.28)  # p4 r4: less ash
    _link(nt, hue_n, "Fac", ha_f, "Value")
    _link_mix_fac(nt, ha_f, "Result", hue_ash)
    _link_mix_out(nt, hue_ash, pbsdf, "Base Color")

    # Roughness varies strand-to-strand — p4 r4: silkier band
    rmap = _map_range(nt, (-220, -220), 0.0, 1.0, 0.16, 0.44)
    _link(nt, strand, "Fac", rmap, "Value")
    # p4 r3: PER-STRAND roughness jitter driven by the hue noise — silky
    # lit strands beside matte ones (anisotropic hair, not clay)
    rj_c = _math(nt, "SUBTRACT", (-60, -220))
    _link(nt, hue_n, "Fac", rj_c, 0)
    rj_c.inputs[1].default_value = 0.5
    rj = _math(nt, "MULTIPLY_ADD", (80, -220), None, 0.22)
    _link(nt, rj_c, "Value", rj, 0)
    _link(nt, rmap, "Result", rj, 2)
    rj_cl = _math(nt, "MAXIMUM", (220, -220), None, 0.10)
    _link(nt, rj, "Value", rj_cl, 0)
    _link(nt, rj_cl, "Value", pbsdf, "Roughness")

    # Strand grooves in the shading normal
    s_c = _math(nt, "SUBTRACT", (-420, -360)); _link(nt, strand, "Fac", s_c, 0); s_c.inputs[1].default_value = 0.5
    h1 = _math(nt, "MULTIPLY_ADD", (-220, -360), None, 0.8, 0.5)
    _link(nt, s_c, "Value", h1, 0)
    _wire_displacement(nt, out, h1, "Value", 0.0036, loc=(260, -520))

    _link(nt, pbsdf, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_hair_deep_material() -> bpy.types.Material:
    """Darker under-hair / brow material (fixer r2 blocker #3). The haircap
    and eyebrow strands (02_details slot 1 on Godwyn_Hair) shade with this:
    a deep root-blonde brown so scalp gaps read as shadowed hair mass and
    brows read as real hair, not painted strips. Same strand-streak bump
    language as Mat_Hair, lower value, rougher."""
    mat = bpy.data.materials.new("Mat_HairDeep")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-1100, -200))
    pbsdf.inputs["Metallic"].default_value = 0.0
    try:
        pbsdf.inputs["Anisotropic"].default_value = 0.70
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.25
        tan = _new_node(nt, "ShaderNodeTangent", (-300, 260))
        tan.direction_type = "RADIAL"
        tan.axis = "Z"
        _link(nt, tan, "Tangent", pbsdf, "Tangent")
        # fixer r3 blocker #1: per-lock highlight breakup (see Mat_Hair)
        lk_n = _new_node(nt, "ShaderNodeTexNoise", (-500, 380))
        lk_n.inputs["Scale"].default_value = 24.0
        lk_n.inputs["Detail"].default_value = 2.0
        _link(nt, tex_c, "Object", lk_n, "Vector")
        lk_m = _map_range(nt, (-300, 380), 0.30, 0.70, 0.08, 0.42)
        _link(nt, lk_n, "Fac", lk_m, "Value")
        _link(nt, lk_m, "Result", pbsdf, "Anisotropic Rotation")
    except KeyError:
        pass
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.35
    except KeyError:
        pass
    strand = _stretched_noise(nt, tex_c, (-900, -200),
                              mapping_scale=(80.0, 80.0, 1.4),
                              noise_scale=10.0, detail=5.0)
    dark_mix = _mix_color(nt, (-420, 60), (0.26, 0.165, 0.045, 1.0),
                          (0.085, 0.055, 0.016, 1.0))
    dk = _map_range(nt, (-620, 60), 0.28, 0.72, 0.0, 0.80)
    _link(nt, strand, "Fac", dk, "Value")
    _link_mix_fac(nt, dk, "Result", dark_mix)
    _link_mix_out(nt, dark_mix, pbsdf, "Base Color")
    rmap = _map_range(nt, (-220, -220), 0.0, 1.0, 0.40, 0.68)
    _link(nt, strand, "Fac", rmap, "Value")
    _link(nt, rmap, "Result", pbsdf, "Roughness")
    s_c = _math(nt, "SUBTRACT", (-420, -360))
    _link(nt, strand, "Fac", s_c, 0)
    s_c.inputs[1].default_value = 0.5
    h1 = _math(nt, "MULTIPLY_ADD", (-220, -360), None, 0.8, 0.5)
    _link(nt, s_c, "Value", h1, 0)
    _wire_displacement(nt, out, h1, "Value", 0.0040, loc=(260, -520))
    _link(nt, pbsdf, "BSDF", out, "Surface")
    _set_disp_method(mat, "BUMP")
    return mat


def make_eye_materials():
    """
    Sclera / iris / pupil for the real MPFB2 eyeballs (blocker #2).
    Iris = warm gold-hazel per art direction; all three get a glossy
    clear-coat so the eyes catch light.
    """
    def _eye_ao(nt, p, color_sock_or_value):
        """phase4 fixer r3 blocker #1 ("small glassy eyes"): OCCLUSION —
        the ball darkens where the lid shells sit close over it, so the
        eye seats INTO the socket instead of floating glassy-bright."""
        ao = _new_node(nt, "ShaderNodeAmbientOcclusion", (-500, -200))
        ao.inputs["Distance"].default_value = 0.02
        ao.samples = 8
        ao_m = _map_range(nt, (-320, -200), 0.35, 0.95, 0.35, 1.0)
        _link(nt, ao, "AO", ao_m, "Value")
        mixn = _new_node(nt, "ShaderNodeMix", (-140, -100))
        mixn.data_type = "RGBA"
        mixn.blend_type = "MULTIPLY"
        _in_sock(mixn, "Factor_Float").default_value = 1.0
        if isinstance(color_sock_or_value, tuple):
            _in_sock(mixn, "A_Color").default_value = color_sock_or_value
        else:
            nt.links.new(color_sock_or_value, _in_sock(mixn, "A_Color"))
        # grayscale AO into B (uniform darkening)
        ao_rgb = _new_node(nt, "ShaderNodeCombineColor", (-320, -80))
        for ch in ("Red", "Green", "Blue"):
            _link(nt, ao_m, "Result", ao_rgb, ch)
        _link(nt, ao_rgb, "Color", mixn, 7)   # B_Color
        nt.links.new(_out_sock(mixn, "Result_Color"),
                     p.inputs["Base Color"])

    def base(name, color, rough, emit=None):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
        p = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
        p.inputs["Base Color"].default_value = color
        p.inputs["Roughness"].default_value = rough
        _eye_ao(nt, p, color)
        try:   # glossy cornea coat — p4 r4 blocker #1 ("no wetness/spec
            # highlight"): WET cornea — roughness 0.05 (above the 0.03
            # denoiser-cross threshold), higher coat IOR for a stronger
            # catchlight.
            p.inputs["Coat Weight"].default_value = 1.0
            p.inputs["Coat Roughness"].default_value = 0.05
            try:
                p.inputs["Coat IOR"].default_value = 1.75
            except KeyError:
                pass
        except KeyError:
            pass
        if emit is not None:
            try:
                p.inputs["Emission Color"].default_value = emit[0]
                p.inputs["Emission Strength"].default_value = emit[1]
            except KeyError:
                pass
        _link(nt, p, "BSDF", out, "Surface")
        return mat

    # r3 blocker #1: iris emission 0.60 blew the amber past the sclera —
    # under AgX both rendered flat WHITE and only the tiny pupil survived.
    # Whisper-level emission only; the iris must read as a DARK warm ring.
    # p5b r3 blocker #1: sclera dimmed + warmed — the bright near-white ring
    # read as a doll-white frame around the iris.
    sclera = base("Mat_EyeSclera", (0.70, 0.66, 0.60, 1.0), 0.30,
                  emit=((0.95, 0.93, 0.88, 1.0), 0.015))
    pupil  = base("Mat_EyePupil",  (0.012, 0.010, 0.008, 1.0), 0.12)

    # -- Mat_EyeIris (p5r1 blocker #1): RADIAL-GRADIENT iris over the
    # "EyeUV" map authored by 02_details.build_eyes (U = angle-from-forward
    # / 30deg: 0 at pupil centre, 1.0 at iris rim). The gradient draws a
    # perfectly ROUND dark pupil out past the old square face-band boundary
    # (both slots are near-black there, so the jagged polygon edge
    # disappears), amber iris body with radial fiber breakup, and a dark
    # limbal ring. Glossy coat = wet-eye highlight.
    iris = bpy.data.materials.new("Mat_EyeIris")
    iris.use_nodes = True
    nt = iris.node_tree
    nt.nodes.clear()
    out = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    p = _new_node(nt, "ShaderNodeBsdfPrincipled", (400, 0))
    uv = _new_node(nt, "ShaderNodeUVMap", (-900, 0))
    uv.uv_map = "EyeUV"
    sep = _new_node(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    _link(nt, uv, "UV", sep, "Vector")
    ramp = _new_node(nt, "ShaderNodeValToRGB", (-500, 0))
    cr = ramp.color_ramp
    cr.elements[0].position = 0.44          # round pupil (covers the 12deg
    cr.elements[0].color = (0.005, 0.004, 0.004, 1.0)  # face-band + margin)
    cr.elements[1].position = 0.52
    cr.elements[1].color = (0.16, 0.085, 0.025, 1.0)   # pupil-edge amber
    e = cr.elements.new(0.78)
    e.color = (0.48, 0.30, 0.09, 1.0)                  # iris body gold-amber
    e = cr.elements.new(0.84)
    e.color = (0.30, 0.17, 0.05, 1.0)                  # outer iris
    # p4 r4 blocker #1: LIMBAL RING darker + wider — the iris must read as
    # a defined disc with a crisp dark boundary, not a soft amber smudge
    e = cr.elements.new(0.875)
    e.color = (0.020, 0.012, 0.006, 1.0)               # dark limbal ring
    e = cr.elements.new(0.935)
    e.color = (0.020, 0.012, 0.006, 1.0)               # ring held wide
    # fixer r2 blocker #3 ("pixelated iris"): the jaggedness was the LOW-POLY
    # iris/sclera material-band boundary — the ramp used to END on the dark
    # limbal ring, so the polygon edge rendered as a jagged dark ring. The
    # ramp now FADES TO THE SCLERA TONE past the limbal ring, making the
    # geometric band boundary invisible (same trick as the round pupil).
    e = cr.elements.new(0.96)
    e.color = (0.70, 0.66, 0.60, 1.0)                  # = sclera base
    _link(nt, sep, "X", ramp, "Fac")
    # radial fiber breakup (object-space noise — no UV seam)
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-900, -300))
    fib = _new_node(nt, "ShaderNodeTexNoise", (-700, -300))
    fib.inputs["Scale"].default_value = 480.0   # r2: 900 aliased into pixel
    fib.inputs["Detail"].default_value = 3.0    # noise at render res
    _link(nt, tex_c, "Object", fib, "Vector")
    fmr = _map_range(nt, (-500, -300), 0.0, 1.0, 0.86, 1.14)
    _link(nt, fib, "Fac", fmr, "Value")
    fmix = _new_node(nt, "ShaderNodeMix", (-220, 0))
    fmix.data_type = "RGBA"
    fmix.blend_type = "MULTIPLY"
    _in_sock(fmix, "Factor_Float").default_value = 0.45
    nt.links.new(ramp.outputs["Color"], _in_sock(fmix, "A_Color"))
    # fiber value -> B color (grayscale multiply)
    nt.links.new(fmr.outputs["Result"], _in_sock(fmix, "B_Color"))
    # p4 r3: lid-contact occlusion ring on the iris too
    _eye_ao(nt, p, _out_sock(fmix, "Result_Color"))
    p.inputs["Roughness"].default_value = 0.18
    try:   # wet-eye clearcoat — p4 r4: wetter (0.05) + higher coat IOR so
        # the iris carries a real catchlight under the key
        p.inputs["Coat Weight"].default_value = 1.0
        p.inputs["Coat Roughness"].default_value = 0.05
        try:
            p.inputs["Coat IOR"].default_value = 1.75
        except KeyError:
            pass
    except KeyError:
        pass
    try:
        p.inputs["Emission Color"].default_value = (1.0, 0.85, 0.40, 1.0)
        p.inputs["Emission Strength"].default_value = 0.08
    except KeyError:
        pass
    _link(nt, p, "BSDF", out, "Surface")

    return sclera, iris, pupil


def assign_eye_materials(eyes, sclera, iris, pupil, skin):
    """
    Godwyn_Eyes (built by 02_details.build_eyes) carries per-face
    material_index bands already: 0=sclera, 1=iris, 2=pupil, 3=eyelid skin
    (r3). Replace the materials IN-SLOT — materials.clear() would RESET
    every polygon's material_index to 0 (that wiped the iris/pupil in r2).
    """
    me = eyes.data
    assert len(me.materials) >= 3, \
        f"Godwyn_Eyes expected 3+ material slots, has {len(me.materials)}"
    me.materials[0] = sclera
    me.materials[1] = iris
    me.materials[2] = pupil
    if len(me.materials) >= 4:
        me.materials[3] = skin           # eyelid shells match the face
    me.update()
    counts = [0, 0, 0, 0]
    for poly in me.polygons:
        counts[min(poly.material_index, 3)] += 1
    print(f"[03_materials] Godwyn_Eyes slots refilled: {counts[0]} sclera / "
          f"{counts[1]} iris / {counts[2]} pupil / {counts[3]} lid polys")


# ---------------------------------------------------------------------------
# SWORD MATERIAL ASSIGNMENT (two-slot: hilt=gold, blade=blade)
# ---------------------------------------------------------------------------

def assign_sword_materials(sword, mat_gold, mat_blade):
    """
    The sword is one joined mesh. We use two material slots and face-level
    assignment:
      Slot 0 = Mat_Gold  (hilt, crossguard, pommel — all gold parts)
      Slot 1 = Mat_Blade (the blade geometry)

    Strategy: faces near or below z=0.21 (in local space, where the
    crossguard/hilt/pommel live) go to slot 0; faces above go to slot 1.
    The blade's local z starts at ~0.20 (just above the crossguard collar).
    """
    sword.data.materials.clear()
    sword.data.materials.append(mat_gold)    # slot 0
    sword.data.materials.append(mat_blade)   # slot 1

    # world-to-local matrix for vertex z lookup
    mw = sword.matrix_world
    for poly in sword.data.polygons:
        # centroid in local space
        local_z = poly.center[2]
        poly.material_index = 1 if local_z > 0.22 else 0

    sword.data.update()


# ---------------------------------------------------------------------------
# VOID WORLD + CRACK
# ---------------------------------------------------------------------------

def build_void_world():
    """
    Rebuild the void world shader (near-black) and the faint vertical golden
    crack plane (INV-7 / SPEC 337-341).  Idempotent: removes any prior
    Godwyn_VoidCrack first.

    The crack is a thin emissive plane standing 5.0m tall behind Godwyn,
    color (1.0,0.85,0.4), strength 3.5 — faint, framing, not dominant.
    """
    # World shader
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("VoidWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()
    bg = wnt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value     = G.COL_WORLD
    bg.inputs["Strength"].default_value  = 1.0
    wout = wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

    # Remove prior crack plane (INV-6)
    for name in list(bpy.data.objects.keys()):
        if "VoidCrack" in name:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    # Remove prior crack material
    if "Mat_VoidCrack" in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials["Mat_VoidCrack"])

    # Tall vertical emissive crack, built VERTICALLY in the XZ plane.
    # (The previous build used primitive_plane_add — which lies FLAT in XY —
    #  then scaled its zero-extent Z axis, leaving an invisible sliver. That
    #  is why every render had a featureless black background, blocker #4.)
    # Body faces -Y; cameras are at -Y, so the crack goes at +Y behind him,
    # offset in X so his silhouette does not fully occlude it.
    import random as _rnd
    _rnd.seed(52)
    # Round 4 (major #5): the crack at (x~1.0, y=7) overlapped Godwyn's
    # silhouette in BOTH review cameras and read as a glowing whip attached
    # to him. Now: pushed to y=12 (far behind), offset to x~2.6 (clears the
    # figure from Cam_Full at (1.5,-9.4) AND Cam_Face at (0,-2.1)), thinner,
    # near-vertical, base raised off the floor so it reads as a DISTANT
    # fissure in the void. Intensity fades toward the top (shader gradient).
    z0, z1 = 0.9, 6.6
    segs = 14
    cverts, cfaces = [], []
    for i in range(segs + 1):
        t = i / segs
        z = z0 + (z1 - z0) * t
        # gently jagged, near-vertical centre-line; pinches at both ends
        cx = 2.60 + 0.025 * math.sin(t * 9.0) + _rnd.uniform(-0.010, 0.010)
        hw = 0.030 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6 \
            + _rnd.uniform(0.0, 0.006)
        cverts.append((cx - hw, 12.0, z))
        cverts.append((cx + hw, 12.0, z))
    for i in range(segs):
        a = i * 2
        cfaces.append((a, a + 1, a + 3, a + 2))
    cme = bpy.data.meshes.new("Godwyn_VoidCrack")
    cme.from_pydata(cverts, [], cfaces)
    cme.update()
    crack = bpy.data.objects.new("Godwyn_VoidCrack", cme)
    bpy.context.scene.collection.objects.link(crack)

    crack_mat = bpy.data.materials.new("Mat_VoidCrack")
    crack_mat.use_nodes = True
    cnt = crack_mat.node_tree
    cnt.nodes.clear()
    emit = cnt.nodes.new("ShaderNodeEmission")
    # saturated deep gold at RESTRAINED strength: AgX whites-out emissive
    # highlights fast — 2.6 read as a white ribbon; ~1.8 keeps the gold HUE
    emit.inputs["Color"].default_value = (1.0, 0.50, 0.08, 1.0)
    # r4 major #5: strength FADES toward the top (distant-fissure read):
    # Generated Z (0 at base, 1 at top) -> Map Range 2.0 -> 0.30
    tco = cnt.nodes.new("ShaderNodeTexCoord")
    sep = cnt.nodes.new("ShaderNodeSeparateXYZ")
    mr = cnt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value   = 2.0
    mr.inputs["To Max"].default_value   = 0.30
    cnt.links.new(tco.outputs["Generated"], sep.inputs["Vector"])
    cnt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    cnt.links.new(mr.outputs["Result"], emit.inputs["Strength"])
    mout = cnt.nodes.new("ShaderNodeOutputMaterial")
    cnt.links.new(emit.outputs["Emission"], mout.inputs["Surface"])
    crack.data.materials.append(crack_mat)

    return crack


# ---------------------------------------------------------------------------
# ASSIGN ALL MATERIALS
# ---------------------------------------------------------------------------

def assign_all_materials():
    """
    Build every material and assign it to the corresponding Godwyn_* object.
    Clears preview materials from P1/P2 first (INV-6).
    """
    clear_materials()

    # Build materials
    mat_skin  = make_skin_material()
    mat_gold  = make_gold_material()
    mat_robe  = make_robe_material()
    mat_blade = make_blade_material()
    mat_hair  = make_hair_material()
    sclera, iris, pupil = make_eye_materials()

    print("[03_materials] Materials built: Skin, Gold, Robe, Blade, Hair, "
          "EyeSclera/Iris/Pupil.")

    # Simple assignments
    for obj_name, mat_name in OBJECT_ASSIGNMENTS.items():
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            print(f"[03_materials] WARNING: '{obj_name}' not found — skipping.",
                  file=sys.stderr)
            continue
        if mat_name is None:
            continue    # handled specially below
        if obj_name == "Godwyn_Body":
            continue    # body handled below (skin + eye slots)
        mat = bpy.data.materials[mat_name]
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        print(f"[03_materials]   {obj_name} <- {mat_name}")

    # Body: skin on the FACE/NECK only — everything below the gorget line
    # wears a dark padded UNDERLAYER (gambeson). RE-OUTFIT fixer r1: the
    # design is "minimal exposed skin — face only"; any sliver of body that
    # peeks between plates under an extreme pose now reads as the armor's
    # dark underpadding (grounded FromSoft language), never as bare white
    # skin. Slot 0 = skin, slot 1 = underlayer, split per-polygon by height.
    body = bpy.data.objects.get("Godwyn_Body")
    if body:
        mat_under = make_underlayer_material()
        body.data.materials.clear()
        body.data.materials.append(mat_skin)
        body.data.materials.append(mat_under)
        me = body.data
        n_under = 0
        for poly in me.polygons:
            zc = sum(me.vertices[vi].co.z for vi in poly.vertices) \
                / len(poly.vertices)
            if zc < 2.665:                    # below the jaw/gorget line
                poly.material_index = 1
                n_under += 1
            else:
                poly.material_index = 0
        me.update()
        print(f"[03_materials]   Godwyn_Body <- Mat_Skin (face/neck) + "
              f"Mat_Underlayer ({n_under} polys below the gorget)")

    # Tabard: blue cloth panels + GOLD embroidery cords share the join —
    # replace IN-SLOT via the godwyn_slot_names contract (same as hair)
    tab = bpy.data.objects.get("Godwyn_Tabard")
    if tab:
        slots = tab.data.materials
        slot_names = list(tab.get("godwyn_slot_names", []))
        by_name = {"Mat_Tabard": mat_robe, "Mat_Cape": mat_robe,
                   "Mat_Gold": mat_gold}
        if len(slots) == 0:
            slots.append(mat_robe)
        elif slot_names and len(slot_names) == len(slots):
            for i, nm in enumerate(slot_names):
                slots[i] = by_name.get(nm, mat_robe)
        else:
            for i in range(len(slots)):
                slots[i] = mat_robe
        tab.data.update()
        print(f"[03_materials]   Godwyn_Tabard <- {len(slots)} slots via "
              f"{slot_names or 'legacy order'}")

    # Hair: slot 0 = blonde strands, slot 1 = deep under-hair (haircap +
    # brows — banded by 02_details.build_hair). Replace IN-SLOT so the
    # per-face material indices survive (same contract as the eyes).
    hair_obj = bpy.data.objects.get("Godwyn_Hair")
    if hair_obj:
        mat_hairdeep = make_hair_deep_material()
        slots = hair_obj.data.materials
        slot_names = list(hair_obj.get("godwyn_slot_names", []))
        if len(slots) == 0:
            slots.append(mat_hair)
        elif slot_names and len(slot_names) == len(slots):
            by_name = {"Mat_Hair": mat_hair, "Mat_HairDeep": mat_hairdeep,
                       "Mat_Gold": mat_gold}
            for i, nm in enumerate(slot_names):
                slots[i] = by_name.get(nm, mat_hair)
        else:
            # legacy single-material hair (pre-r2 blends)
            for i in range(len(slots)):
                slots[i] = mat_hair
        hair_obj.data.update()
        print(f"[03_materials]   Godwyn_Hair <- {len(slots)} slots via "
              f"{slot_names or 'legacy order'}")

    # Eyes: sclera/iris/pupil slots (banded by 02_details.build_eyes)
    eyes = bpy.data.objects.get("Godwyn_Eyes")
    if eyes:
        assign_eye_materials(eyes, sclera, iris, pupil, mat_skin)
        print("[03_materials]   Godwyn_Eyes <- EyeSclera/Iris/Pupil (+Skin lids)")
    else:
        print("[03_materials] WARNING: Godwyn_Eyes not found — run 02 first.",
              file=sys.stderr)

    # Sword: hilt=gold, blade=blade
    sword = bpy.data.objects.get("Godwyn_Sword")
    if sword:
        assign_sword_materials(sword, mat_gold, mat_blade)
        print("[03_materials]   Godwyn_Sword <- Gold (hilt) + Blade (blade)")
    else:
        print("[03_materials] WARNING: Godwyn_Sword not found — sword materials skipped.",
              file=sys.stderr)

    return mat_skin, mat_gold, mat_robe, mat_blade, mat_hair


# ---------------------------------------------------------------------------
# BEAUTY PREVIEW CAMERA + LIGHTING
# ---------------------------------------------------------------------------

def setup_beauty_preview(scene):
    """
    Minimal lighting for the beauty preview:
      - A warm key light from upper-front-left (INV-7 color 1.0,0.92,0.6)
      - A cool dim fill to keep shadow side readable, not pure black
      - A rim from behind to separate from the void

    NOT the full P4 rig — just enough to judge material colors.
    We rely primarily on Godwyn's skin emission to carry the face.
    """
    # Remove any prior preview lights/cam
    for name in list(bpy.data.objects.keys()):
        if name.startswith(("Beauty_", "Clay_")):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for d in list(bpy.data.lights):
        if d.name.startswith(("Beauty_", "Clay_")):
            bpy.data.lights.remove(d)
    for d in list(bpy.data.cameras):
        if d.name.startswith(("Beauty_", "Clay_")):
            bpy.data.cameras.remove(d)

    # --- Camera ---
    # Body faces -Y (documented in 02_details.py: "Body faces -Y").
    # Front of character (chest, face) is in the -Y hemisphere.
    # Camera must be placed at negative Y to see the front.
    # Slight right offset (+X) for a 3/4 portrait composition.
    cam_data = bpy.data.cameras.new("Beauty_Cam")
    cam_data.lens    = 70      # slight telephoto for portrait
    cam_data.clip_end = 60.0
    cam_obj = bpy.data.objects.new("Beauty_Cam", cam_data)
    scene.collection.objects.link(cam_obj)
    import mathutils
    # Camera at front-right: x=+1.2, y=-8.0 (looking at front), z=1.85 (mid-chest/upper body)
    cam_obj.location = (1.2, -8.0, 1.85)
    # Aim at chest center (head_z ~3.0, waist ~1.97; mid ~2.4)
    target = mathutils.Vector((0.0, 0.0, 2.10))
    direction = cam_obj.location - target
    cam_obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    scene.camera = cam_obj

    # --- Close-up bust camera (micro-detail critique: pores/hair/gold) ---
    ccam_data = bpy.data.cameras.new("Beauty_CamClose")
    ccam_data.lens = 85
    ccam_data.clip_end = 60.0
    ccam = bpy.data.objects.new("Beauty_CamClose", ccam_data)
    scene.collection.objects.link(ccam)
    ccam.location = (0.62, -2.30, 2.80)
    ctarget = mathutils.Vector((0.0, 0.0, 2.72))     # face/pauldron/sternum
    cdir = mathutils.Vector(ccam.location) - ctarget
    ccam.rotation_euler = cdir.to_track_quat("Z", "Y").to_euler()

    # Dark-fantasy lighting rig per SPEC: Godwyn is the scene light source.
    # In the void, there is no environmental light — the only illumination
    # comes from Godwyn himself and a faint off-axis key to reveal form.
    #
    # Rig philosophy:
    #   • GodwynGlow point at chest = primary ambient (warm, omni)
    #   • Key area light = reveal 3D form (shadows, SSS) from front-left
    #   • Rim area light = separate silhouette from void at back
    #   • No fill — void world has no fill; shadow side goes dark

    # --- Godwyn chest glow (ambient fill) — SPEC 337-339 ---
    # Low warm ambient simulating skin self-emission. Not the primary source.
    glow = bpy.data.lights.new("Beauty_GodwynGlow", "POINT")
    glow.energy   = 18.0     # very low — just warm fill for shadows
    glow.color    = (1.0, 0.92, 0.6)
    glow.shadow_soft_size = 2.0
    glow_o = bpy.data.objects.new("Beauty_GodwynGlow", glow)
    scene.collection.objects.link(glow_o)
    glow_o.location = (0.0, -1.0, 2.30)   # slightly in front of chest

    # --- Key light: primary form revealer (three-point rig) ---
    # r3: key HALVED 160->80W. The face (pale skin 0.95,0.90,0.82) is the
    # whitest surface in the scene — any strong front light blows it out.
    # At 80W the face shows features; the metallic gold armor still catches
    # strong specular highlights (metallic low-roughness = bright at any level).
    key = bpy.data.lights.new("Beauty_Key", "AREA")
    key.energy       = 80.0   # r3: halved — face was blown out at 160W
    key.color        = (1.0, 0.92, 0.6)
    key.size         = 3.0
    key_o = bpy.data.objects.new("Beauty_Key", key)
    scene.collection.objects.link(key_o)
    key_o.location   = (-3.5, -5.0, 5.5)
    key_o.rotation_euler = (math.radians(50), math.radians(-30),
                             math.radians(-20))

    # --- Armor accent light: aimed at torso/limbs from the right, offset
    # upward so it rakes across the plate surfaces showing relief and engraving.
    # Does NOT directly light the face (comes from the wrong side/elevation).
    import mathutils as mu
    acc = bpy.data.lights.new("Beauty_ArmorAccent", "AREA")
    acc.energy       = 140.0   # strong armor reveal — gold needs directional hit
    acc.color        = (1.0, 0.94, 0.65)   # warm gold accent
    acc.size         = 1.5     # tighter source = sharper specular line
    acc_o = bpy.data.objects.new("Beauty_ArmorAccent", acc)
    scene.collection.objects.link(acc_o)
    # Positioned upper-right, angled steeply down to rake plate surfaces
    acc_o.location   = (4.5, -3.0, 4.0)
    acc_target = mu.Vector((0.0, 0.0, 1.8))
    acc_dir = mu.Vector(acc_o.location) - acc_target
    acc_o.rotation_euler = acc_dir.to_track_quat("-Z", "Y").to_euler()

    # --- Rim: behind character (+Y side), separates from void ---
    rim = bpy.data.lights.new("Beauty_Rim", "AREA")
    rim.energy        = 110.0   # warm gold rim — separates silhouette
    rim.color         = (1.0, 0.88, 0.50)
    rim.size          = 3.0
    rim_o = bpy.data.objects.new("Beauty_Rim", rim)
    scene.collection.objects.link(rim_o)
    rim_o.location    = (0.0, 5.5, 4.0)
    target_rim = mu.Vector((0.0, 0.0, 2.0))
    dir_rim = mu.Vector(rim_o.location) - target_rim
    rim_o.rotation_euler = dir_rim.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------------------
# BEAUTY-ONLY ADAPTIVE MICRO-DISPLACEMENT
# ---------------------------------------------------------------------------

DISP_MATS = ("Mat_Skin", "Mat_Tabard")           # true-displacement candidates
DISP_OBJS = ("Godwyn_Body", "Godwyn_Tabard")     # low/mid-poly, safe to dice

def enable_adaptive_disp(scene):
    """
    BEAUTY RENDERS ONLY. Flip skin/robe to true adaptive micro-displacement
    (Cycles experimental feature set + adaptive subdivision). MUST be called
    AFTER bpy.ops.wm.save_as_mainfile — nothing here is ever saved, so the
    stored .blend / exported GLB stays normal-map(bump)-based (game-safe,
    ANIMATABLE invariant).
    """
    # Blender <=4.x gated adaptive subdiv behind feature_set='EXPERIMENTAL';
    # Blender 5.x removed the gate (attribute gone) and moved the toggle onto
    # the SUBSURF modifier itself — guard for both.
    try:
        scene.cycles.feature_set = "EXPERIMENTAL"
    except AttributeError:
        pass
    try:
        scene.cycles.dicing_rate = 2.0            # coarser than default=1:
        scene.cycles.offscreen_dicing_scale = 8.0 # 8GB VRAM guard
    except AttributeError:
        pass
    for mname in DISP_MATS:
        mat = bpy.data.materials.get(mname)
        if mat:
            _set_disp_method(mat, "BOTH")   # displace what dicing reaches,
                                            # bump the rest
    n = 0
    for oname in DISP_OBJS:
        obj = bpy.data.objects.get(oname)
        if obj is None:
            continue
        if "BeautyAdaptiveSubdiv" not in obj.modifiers:
            mod = obj.modifiers.new("BeautyAdaptiveSubdiv", "SUBSURF")
            mod.subdivision_type = "SIMPLE"   # no smoothing — detail only
            mod.levels = 0                    # viewport irrelevant (headless)
        else:
            mod = obj.modifiers["BeautyAdaptiveSubdiv"]
        ok = False
        try:
            mod.use_adaptive_subdivision = True   # Blender 5.x API
            ok = True
        except AttributeError:
            try:
                obj.cycles.use_adaptive_subdivision = True   # Blender <=4.x
                ok = True
            except AttributeError:
                print(f"[03_materials] WARNING: adaptive subdiv API missing "
                      f"on {oname}", file=sys.stderr)
        if ok:
            n += 1
    print(f"[03_materials] Adaptive micro-displacement ON (render-only) for "
          f"{n} objects: {DISP_OBJS}; mats {DISP_MATS} -> method BOTH")


def disable_adaptive_disp(scene):
    """Undo enable_adaptive_disp (in-memory hygiene; nothing was saved)."""
    try:
        scene.cycles.feature_set = "SUPPORTED"
    except AttributeError:
        pass
    for mname in DISP_MATS:
        mat = bpy.data.materials.get(mname)
        if mat:
            _set_disp_method(mat, "BUMP")
    for oname in DISP_OBJS:
        obj = bpy.data.objects.get(oname)
        if obj and "BeautyAdaptiveSubdiv" in obj.modifiers:
            obj.modifiers.remove(obj.modifiers["BeautyAdaptiveSubdiv"])
        try:
            obj.cycles.use_adaptive_subdivision = False
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# VALIDATION ASSERTS (plan Section 3 Phase 3 gate)
# ---------------------------------------------------------------------------

def assert_materials():
    errors = []

    # All core materials must exist
    for name in ("Mat_Skin", "Mat_Gold", "Mat_Tabard", "Mat_Blade", "Mat_Hair"):
        if name not in bpy.data.materials:
            errors.append(f"Material '{name}' missing")

    # Each character object must have at least one material slot
    for obj_name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Tabard",
                     "Godwyn_Hair", "Godwyn_Sword", "Godwyn_Eyes"):
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            errors.append(f"Object '{obj_name}' missing")
            continue
        if len(obj.data.materials) == 0:
            errors.append(f"'{obj_name}' has no material slots")

    # Skin emission must be non-trivial (strength > 0).
    # Emission may be either in a ShaderNodeEmission node OR inside
    # Principled BSDF "Emission Strength" (Blender 4+).
    skin = bpy.data.materials.get("Mat_Skin")
    if skin:
        # Check Principled BSDF emission first (Blender 4+)
        pbsdf_skin = next((n for n in skin.node_tree.nodes
                           if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        emit_ok = False
        if pbsdf_skin:
            try:
                s = pbsdf_skin.inputs["Emission Strength"].default_value
                if s >= 0.5:
                    emit_ok = True
            except KeyError:
                pass
        # Fall back: standalone Emission node (Blender 3.x / Mix approach)
        if not emit_ok:
            emit_node = next((n for n in skin.node_tree.nodes
                             if n.bl_idname == "ShaderNodeEmission"), None)
            if emit_node is not None:
                s = emit_node.inputs["Strength"].default_value
                if s >= 0.1:   # only requires >0 — fac on MixShader controls intensity
                    emit_ok = True
        if not emit_ok:
            errors.append("Mat_Skin: no emission found (check Principled BSDF or Emission node)")

    # Gold must be metallic=1
    gold = bpy.data.materials.get("Mat_Gold")
    if gold:
        pbsdf = next((n for n in gold.node_tree.nodes
                      if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if pbsdf is None:
            errors.append("Mat_Gold has no Principled BSDF")
        else:
            m = pbsdf.inputs["Metallic"].default_value
            if m < 0.99:
                errors.append(f"Mat_Gold metallic < 1: {m}")

    # MICRO-DETAIL gate: every hero material must carry an object-space
    # height signal wired into Material Output.Displacement (bump-mode,
    # game-safe) — this is what kills the "flat clay" read.
    for mname in ("Mat_Skin", "Mat_Gold", "Mat_Tabard", "Mat_Blade", "Mat_Hair"):
        m = bpy.data.materials.get(mname)
        if m is None:
            continue
        has_disp = any(n.bl_idname == "ShaderNodeDisplacement"
                       for n in m.node_tree.nodes)
        if not has_disp:
            errors.append(f"{mname}: no Displacement (micro height) node")
        else:
            outn = next((n for n in m.node_tree.nodes
                         if n.bl_idname == "ShaderNodeOutputMaterial"), None)
            if outn is None or not outn.inputs["Displacement"].is_linked:
                errors.append(f"{mname}: Displacement socket not linked")
        # saved asset must be BUMP (normal-map-based), never true disp
        meth = getattr(m, "displacement_method",
                       getattr(getattr(m, "cycles", None),
                               "displacement_method", "BUMP"))
        if meth != "BUMP":
            errors.append(f"{mname}: displacement_method={meth} at save time "
                          f"(must be BUMP — game-safe invariant)")
        has_objcoord = any(n.bl_idname == "ShaderNodeTexCoord"
                           for n in m.node_tree.nodes)
        if not has_objcoord:
            errors.append(f"{mname}: no object-space Texture Coordinate node")

    # Gold edge-wear must be curvature-driven (Geometry->Pointiness)
    if "Mat_Gold" in bpy.data.materials:
        gnt = bpy.data.materials["Mat_Gold"].node_tree
        if not any(n.bl_idname == "ShaderNodeNewGeometry" for n in gnt.nodes):
            errors.append("Mat_Gold: no Geometry (pointiness edge-wear) node")

    # No BeautyAdaptiveSubdiv modifier may exist at save time
    for oname in DISP_OBJS:
        o = bpy.data.objects.get(oname)
        if o and "BeautyAdaptiveSubdiv" in o.modifiers:
            errors.append(f"{oname}: BeautyAdaptiveSubdiv present at save time")

    # Robe must have NO emission node
    robe = bpy.data.materials.get("Mat_Tabard")
    if robe:
        emit_nodes = [n for n in robe.node_tree.nodes
                      if n.bl_idname == "ShaderNodeEmission"]
        if emit_nodes:
            errors.append("Mat_Tabard has an Emission node (SPEC 340: no emission)")

    # Void crack must exist and have a REAL emissive material bound
    # (a None slot passes len()>0 — that hid the blocker-#2 root cause)
    crack = bpy.data.objects.get("Godwyn_VoidCrack")
    if crack is None:
        errors.append("Godwyn_VoidCrack object missing")
    elif len(crack.data.materials) == 0 or crack.data.materials[0] is None:
        errors.append("Godwyn_VoidCrack has no material bound (empty slot)")
    elif not any(n.bl_idname == "ShaderNodeEmission"
                 for n in crack.data.materials[0].node_tree.nodes):
        errors.append("Godwyn_VoidCrack material has no Emission node")

    if errors:
        for e in errors:
            print(f"[03_materials] FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print("[03_materials] ASSERT OK: All materials built and assigned.")
    print(f"[03_materials]   Skin emit strength = {G.SKIN_EMIT_STR} (subtle glow).")
    print(f"[03_materials]   Blade emit strength = {G.BLADE_EMIT_STR} << skin (restrained).")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[03_materials] Phase 3 — Materials & Shaders")
    print("=" * 60)

    # INV-2: GPU enforced first, before any expensive work
    active_gpu = G.enable_gpu()
    print(f"[03_materials] GPU active: {active_gpu}")

    # Load the saved .blend — it already has all Godwyn_* objects from Phase 2.
    # This is the correct approach: apply materials to existing geometry rather
    # than rebuilding from module scripts (whose API changed in Phase 2).
    import os as _os
    blend_path = _os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
    if not _os.path.isfile(blend_path):
        print(f"[03_materials] FATAL: .blend not found: {blend_path}", file=sys.stderr)
        sys.exit(1)

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    print(f"[03_materials] Opened: {blend_path}")

    # INV-2: re-enable GPU after file open (file open resets scene settings)
    active_gpu = G.enable_gpu()
    print(f"[03_materials] GPU re-enabled after file open: {active_gpu}")

    # Confirm Godwyn objects are present
    expected = ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Tabard",
                "Godwyn_Hair", "Godwyn_Sword", "Godwyn_Eyes")
    missing = [n for n in expected if bpy.data.objects.get(n) is None]
    if missing:
        print(f"[03_materials] FATAL: Objects missing after .blend load: {missing}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[03_materials] Godwyn objects confirmed: {list(expected)}")

    # Assign all materials (INV-3 / INV-6)
    assign_all_materials()

    # Build void world + crack (INV-7).
    # MUST run AFTER assign_all_materials: clear_materials() removes
    # Mat_VoidCrack by name, and when the crack was built first it was left
    # with an EMPTY slot — a default gray plane lit by the rim light. That
    # was the true root cause of blocker #2's "white line, not golden".
    crack = build_void_world()
    col = bpy.data.collections.get("Godwyn")
    if col is None:
        col = G.get_or_create_collection("Godwyn")
    G.move_to_collection(crack, col)
    print("[03_materials] Void world + golden crack plane built.")

    # SAVE the .blend NOW — before any preview-only lights/cameras exist.
    # (Previous revision never saved: Phase 3's SSS/emission/void-crack were
    #  lost and Phase 4+ rendered Phase-2 preview materials. Root cause of
    #  blockers #4/#5.)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    print(f"[03_materials] SAVED materials into {blend_path} "
          f"({os.path.getsize(blend_path) // 1024} KB)")

    # Setup beauty preview camera and lights (in-memory only, NOT saved)
    scene = bpy.context.scene
    setup_beauty_preview(scene)

    # Cycles render config — beauty preview at reduced res for iteration speed
    # (still 2K+ per plan; 1440x2560 = caller target from plan §10 OQ-1)
    G.configure_cycles(
        scene,
        samples=192,             # higher than clay for real material eval
        resolution_x=1440,
        resolution_y=2560,
        use_denoiser=True,
        film_transparent=False,  # keep the void black bg
    )

    # Validate (also gates: BUMP-only + no subdiv modifiers in the SAVED file)
    assert_materials()

    # --- Render 1: full-body beauty, bump-based (the game-safe look) ------
    print(f"[03_materials] Rendering beauty preview -> {_PREVIEW_OUT}")
    G.render_to_path(_PREVIEW_OUT, scene)

    # --- Render 2: close bust, bump-based (micro-detail critique view) ----
    close_out = os.path.join(_WIP_DIR, "03_beauty_close.png")
    scene.camera = bpy.data.objects["Beauty_CamClose"]
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1600
    G.render_to_path(close_out, scene)

    # --- Render 3: tabard/blue cloth critique — front camera at waist height,
    # seeing the front tabard panel + gold embroidery edges clearly.
    tab_out = os.path.join(_WIP_DIR, "03_beauty_tabard.png")
    import mathutils as _mu
    tcam_data = bpy.data.cameras.new("Beauty_CamTabard")
    tcam_data.lens = 85
    tcam_data.clip_end = 60.0
    tcam = bpy.data.objects.new("Beauty_CamTabard", tcam_data)
    scene.collection.objects.link(tcam)
    # Position: front-center, framing the waist->knee region (tabard panel)
    tcam.location = (0.0, -6.0, 1.20)
    ttarget = _mu.Vector((0.0, 0.0, 1.30))
    tdir = _mu.Vector(tcam.location) - ttarget
    tcam.rotation_euler = tdir.to_track_quat("Z", "Y").to_euler()
    scene.camera = tcam
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1400
    G.render_to_path(tab_out, scene)
    bpy.data.cameras.remove(tcam_data, do_unlink=True)
    print(f"[03_materials] Tabard detail render -> {tab_out}")

    # --- Render 4: close bust WITH adaptive micro-displacement ------------
    # BEAUTY-ONLY: happens strictly AFTER the .blend save above; nothing
    # here is written back to disk (set GODWYN_SKIP_DISP=1 to skip).
    disp_out = os.path.join(_WIP_DIR, "03_beauty_close_disp.png")
    if os.environ.get("GODWYN_SKIP_DISP") != "1":
        scene.camera = bpy.data.objects.get("Beauty_CamClose") or \
                       bpy.data.objects.get("Beauty_Cam")
        scene.render.resolution_x = 1600
        scene.render.resolution_y = 1600
        enable_adaptive_disp(scene)
        G.render_to_path(disp_out, scene)
        disable_adaptive_disp(scene)
    else:
        print("[03_materials] GODWYN_SKIP_DISP=1 — skipping disp render.")

    # Verify outputs
    for p in (_PREVIEW_OUT, close_out):
        if not os.path.isfile(p) or os.path.getsize(p) < 1024:
            print(f"[03_materials] FATAL: preview PNG missing/empty: {p}",
                  file=sys.stderr)
            sys.exit(1)

    size_kb = os.path.getsize(_PREVIEW_OUT) // 1024
    print(f"[03_materials] Beauty preview OK: {_PREVIEW_OUT} ({size_kb} KB)")
    print("[03_materials] Object list:",
          sorted(o.name for o in bpy.data.collections["Godwyn"].objects))
    print("[03_materials] Phase 3 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
