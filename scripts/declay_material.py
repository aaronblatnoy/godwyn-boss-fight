# declay_material.py — Phase 1: de-clay godwyn_full_final.glb via materials + lighting ONLY.
# Geometry is NEVER touched. Run headless:
#   blender --background --python ~/godwyn-boss-fight/scripts/declay_material.py -- pass=1 [debug=1]
#
# Strategy:
#   * Import GLB, harvest its baked images (albedo / normal / ORM / emission).
#   * Rebuild Material_0 as a smart PBR shader:
#       - metallic mask derived from albedo (warm hue + saturated + bright => gold)
#       - gold: metallic 1, roughness ~0.2-0.35 with noise variation, slight anisotropy
#       - cloth (blue/dark albedo): matte, roughness ~0.7, sheen, base tinted to a
#         clear royal/indigo blue (target 0.08, 0.12, 0.35) so it reads BLUE not black
#       - skin (warm, low-sat, bright): non-metal + subsurface
#       - fine noise bump chained after the baked normal map so metal isn't a mirror
#   * Dramatic dark-fantasy light rig: warm key, cool fill, gold rims, emissive
#     reflection cards (camera-invisible) + subtle dark gradient world so the gold
#     has something real to reflect while the background stays near-black.
#   * Cycles, OptiX GPU, denoised, portrait. Renders a full-body and a bust view.

import bpy, sys, math, os
from mathutils import Vector

# ------------------------------------------------------------------ config
ARGS = {}
if "--" in sys.argv:
    for a in sys.argv[sys.argv.index("--") + 1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            ARGS[k] = v
PASS = ARGS.get("pass", "1")
MASK_DEBUG = ARGS.get("debug", "0") == "1"
ALBEDO_DEBUG = ARGS.get("debug", "0") == "2"

HOME = os.path.expanduser("~")
GLB = f"{HOME}/godwyn-boss-fight/models/godwyn_full_final.glb"
OUTDIR = f"{HOME}/godwyn-boss-fight/renders/declay"
os.makedirs(OUTDIR, exist_ok=True)

CFG = dict(
    # --- masks (from albedo HSV) ---
    # NOTE: shader HSV runs in LINEAR space (sampled: skin S~0.67 H~0.056 V~0.59;
    # gold armor S~0.85-0.90 H~0.08; sash V<0.02) — thresholds set accordingly.
    gold_hue_lo=0.030, gold_hue_hi=0.160, gold_sat_min=0.740, gold_val_min=0.08,
    skin_hue_lo=0.00, skin_hue_hi=0.090, skin_sat_lo=0.10, skin_sat_hi=0.70,
    skin_val_min=0.20,
    blue_hue_lo=0.50, blue_hue_hi=0.90,
    dark_val_max=0.10,          # near-black albedo also counts as cloth
    mask_soft=0.025,
    # --- gold ---
    gold_rough_lo=0.27, gold_rough_hi=0.43, gold_aniso=0.30,
    gold_tint=(0.95, 0.70, 0.28), gold_tint_mix=0.40,  # push albedo toward rich gold
    # --- cloth / THE BLUE ---
    cloth_rough=0.70, cloth_sheen=0.30,
    blue_target=(0.08, 0.12, 0.35),
    blue_mix=0.97,              # how hard to pull cloth base toward the target blue
    blue_val_boost=0.68,        # deep royal blue, not pastel
    # --- skin ---
    skin_rough=0.45, sss_weight=0.12, sss_scale=0.04,
    # --- micro detail ---
    micro_bump=0.10, micro_scale=180.0,
    rough_noise_scale=60.0,
    # --- emission channel ---
    emit_strength=1.5,
    # --- lighting ---
    world_bot=(0.001, 0.001, 0.002), world_top=(0.010, 0.014, 0.028),
    key_color=(1.0, 0.72, 0.42), key_power=170.0,
    fill_color=(0.35, 0.50, 0.95), fill_power=28.0,
    rim1_color=(1.0, 0.65, 0.28), rim1_power=130.0,
    rim2_color=(0.55, 0.65, 1.0), rim2_power=70.0,
    card_warm=(1.0, 0.75, 0.45), card_warm_str=1.2,
    card_cool=(0.35, 0.45, 0.90), card_cool_str=0.25,
    # --- render ---
    res=(1152, 1536), samples=192,
    cam_full_f=50, cam_bust_f=85,
    cam_yaw_deg=18.0,           # 3/4 view
)

# ------------------------------------------------------------------ scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene

# ------------------------------------------------------------------ GPU / cycles
scn.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = (d.type == "OPTIX")
scn.cycles.device = "GPU"
scn.cycles.samples = CFG["samples"]
scn.cycles.use_denoising = True
scn.cycles.denoiser = "OPTIX"
scn.render.resolution_x, scn.render.resolution_y = CFG["res"]
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"
if ARGS.get("debug", "0") != "0":
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.look = "None"

# ------------------------------------------------------------------ import GLB
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in scn.objects if o.type == "MESH"]
assert meshes, "no meshes imported"

# world-space bbox
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
H = bb_max.z - bb_min.z
print(f"[declay] bbox H={H:.3f} center={tuple(round(v,3) for v in center)}")

# ------------------------------------------------------------------ harvest images
mat = bpy.data.materials.get("Material_0") or meshes[0].data.materials[0]
nt = mat.node_tree
img_albedo = img_normal = img_orm = img_emit = None
for n in nt.nodes:
    if n.type != "TEX_IMAGE" or not n.image:
        continue
    for lk in [l for out in n.outputs for l in out.links]:
        tn, ts = lk.to_node, lk.to_socket.name
        if ts == "Base Color" or (tn.type in ("MIX", "MIX_RGB") and img_albedo is None):
            img_albedo = n.image
        elif tn.type == "NORMAL_MAP":
            img_normal = n.image
        elif tn.type == "SEPARATE_COLOR":
            img_orm = n.image
        elif "Emission" in ts:
            img_emit = n.image
print(f"[declay] albedo={img_albedo} normal={img_normal} orm={img_orm} emit={img_emit}")
assert img_albedo is not None and img_normal is not None

# ------------------------------------------------------------------ rebuild shader
nt.nodes.clear()
N = nt.nodes.new
L = nt.links.new

def node(t, loc, **props):
    n = N(t)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n

def nmath(op, a, b, loc, clamp=False):
    m = node("ShaderNodeMath", loc, operation=op, use_clamp=clamp)
    for i, s in enumerate((a, b)):
        if s is None:
            continue
        if isinstance(s, (int, float)):
            m.inputs[i].default_value = s
        else:
            L(s, m.inputs[i])
    return m.outputs[0]

def band(x, lo, hi, loc, soft=None):
    """smooth 1 inside [lo,hi], 0 outside"""
    soft = soft if soft is not None else CFG["mask_soft"]
    up = node("ShaderNodeMapRange", loc, interpolation_type="SMOOTHSTEP")
    up.inputs["From Min"].default_value = lo - soft
    up.inputs["From Max"].default_value = lo + soft
    L(x, up.inputs["Value"])
    dn = node("ShaderNodeMapRange", (loc[0], loc[1] - 160), interpolation_type="SMOOTHSTEP")
    dn.inputs["From Min"].default_value = hi - soft
    dn.inputs["From Max"].default_value = hi + soft
    dn.inputs["To Min"].default_value = 1.0
    dn.inputs["To Max"].default_value = 0.0
    L(x, dn.inputs["Value"])
    return nmath("MULTIPLY", up.outputs["Result"], dn.outputs["Result"], (loc[0] + 180, loc[1]))

def smooth_gt(x, thr, loc, soft=None):
    soft = soft if soft is not None else CFG["mask_soft"]
    mr = node("ShaderNodeMapRange", loc, interpolation_type="SMOOTHSTEP")
    mr.inputs["From Min"].default_value = thr - soft
    mr.inputs["From Max"].default_value = thr + soft
    L(x, mr.inputs["Value"])
    return mr.outputs["Result"]

def smooth_lt(x, thr, loc, soft=None):
    g = smooth_gt(x, thr, loc, soft)
    return nmath("SUBTRACT", 1.0, g, (loc[0] + 180, loc[1]), clamp=True)

# ---- textures
uv = node("ShaderNodeTexCoord", (-1700, 0))
t_alb = node("ShaderNodeTexImage", (-1500, 300)); t_alb.image = img_albedo
t_nrm = node("ShaderNodeTexImage", (-1500, -300)); t_nrm.image = img_normal
t_nrm.image.colorspace_settings.name = "Non-Color"
L(uv.outputs["UV"], t_alb.inputs["Vector"])
L(uv.outputs["UV"], t_nrm.inputs["Vector"])
t_emit = None
if img_emit:
    t_emit = node("ShaderNodeTexImage", (-1500, -600)); t_emit.image = img_emit
    L(uv.outputs["UV"], t_emit.inputs["Vector"])

# ---- HSV split of albedo
hsv = node("ShaderNodeSeparateColor", (-1250, 300), mode="HSV")
L(t_alb.outputs["Color"], hsv.inputs["Color"])
Hh, Ss, Vv = hsv.outputs[0], hsv.outputs[1], hsv.outputs[2]

# ---- GOLD mask: warm hue AND saturated AND not-too-dark
g_h = band(Hh, CFG["gold_hue_lo"], CFG["gold_hue_hi"], (-1000, 500))
g_s = smooth_gt(Ss, CFG["gold_sat_min"], (-1000, 250))
g_v = smooth_gt(Vv, CFG["gold_val_min"], (-1000, 100))
gold = nmath("MULTIPLY", nmath("MULTIPLY", g_h, g_s, (-700, 400)), g_v, (-550, 400), clamp=True)

# ---- SKIN mask: warm hue, LOW sat, bright, and not gold
k_h = band(Hh, CFG["skin_hue_lo"], CFG["skin_hue_hi"], (-1000, -50))
k_s = band(Ss, CFG["skin_sat_lo"], CFG["skin_sat_hi"], (-1000, -250))
k_v = smooth_gt(Vv, CFG["skin_val_min"], (-1000, -430))
skin = nmath("MULTIPLY", nmath("MULTIPLY", k_h, k_s, (-700, -150)), k_v, (-550, -150), clamp=True)
skin = nmath("MULTIPLY", skin, nmath("SUBTRACT", 1.0, gold, (-560, -260), clamp=True), (-400, -150), clamp=True)

# ---- CLOTH mask: blue hue OR very dark; excluded from gold/skin
c_b = band(Hh, CFG["blue_hue_lo"], CFG["blue_hue_hi"], (-1000, -650))
c_d = smooth_lt(Vv, CFG["dark_val_max"], (-1000, -850))
cloth = nmath("MAXIMUM", c_b, c_d, (-700, -700))
not_gs = nmath("SUBTRACT", nmath("SUBTRACT", 1.0, gold, (-720, -820), clamp=True), skin, (-560, -820), clamp=True)
cloth = nmath("MULTIPLY", cloth, not_gs, (-400, -700), clamp=True)

# ---- base color: gold tint on gold, deep royal blue on cloth
goldize = node("ShaderNodeMix", (-700, 700), data_type="RGBA", blend_type="MIX")
goldize.inputs["Factor"].default_value = CFG["gold_tint_mix"]
L(t_alb.outputs["Color"], goldize.inputs["A"])
goldize.inputs["B"].default_value = (*CFG["gold_tint"], 1.0)

base1 = node("ShaderNodeMix", (-450, 700), data_type="RGBA", blend_type="MIX")
L(gold, base1.inputs["Factor"])
L(t_alb.outputs["Color"], base1.inputs["A"])
L(goldize.outputs["Result"], base1.inputs["B"])

# cloth branch: mix albedo toward the target blue, then lift value so it's clearly blue
blued = node("ShaderNodeMix", (-450, 480), data_type="RGBA", blend_type="MIX")
blued.inputs["Factor"].default_value = CFG["blue_mix"]
L(t_alb.outputs["Color"], blued.inputs["A"])
blued.inputs["B"].default_value = (*CFG["blue_target"], 1.0)
blift = node("ShaderNodeHueSaturation", (-260, 480))
blift.inputs["Saturation"].default_value = 1.55
blift.inputs["Value"].default_value = CFG["blue_val_boost"]
L(blued.outputs["Result"], blift.inputs["Color"])

base2 = node("ShaderNodeMix", (-80, 640), data_type="RGBA", blend_type="MIX")
L(cloth, base2.inputs["Factor"])
L(base1.outputs["Result"], base2.inputs["A"])
L(blift.outputs["Color"], base2.inputs["B"])

# ---- roughness: gold = noisy low; cloth = 0.7; skin = 0.45; else mid
noise = node("ShaderNodeTexNoise", (-1000, 900))
noise.inputs["Scale"].default_value = CFG["rough_noise_scale"]
g_rough_mr = node("ShaderNodeMapRange", (-800, 900))
g_rough_mr.inputs["To Min"].default_value = CFG["gold_rough_lo"]
g_rough_mr.inputs["To Max"].default_value = CFG["gold_rough_hi"]
L(noise.outputs["Fac"], g_rough_mr.inputs["Value"])
r1 = node("ShaderNodeMix", (-500, 900), data_type="FLOAT")   # base 0.55 -> gold rough
r1.inputs["A"].default_value = 0.55
L(g_rough_mr.outputs["Result"], r1.inputs["B"])
L(gold, r1.inputs["Factor"])
r2 = node("ShaderNodeMix", (-320, 900), data_type="FLOAT")
L(r1.outputs["Result"], r2.inputs["A"])
r2.inputs["B"].default_value = CFG["cloth_rough"]
L(cloth, r2.inputs["Factor"])
r3 = node("ShaderNodeMix", (-140, 900), data_type="FLOAT")
L(r2.outputs["Result"], r3.inputs["A"])
r3.inputs["B"].default_value = CFG["skin_rough"]
L(skin, r3.inputs["Factor"])

# ---- normal: baked normal map + fine micro bump on top
nmap = node("ShaderNodeNormalMap", (-1000, -1050))
L(t_nrm.outputs["Color"], nmap.inputs["Color"])
micro = node("ShaderNodeTexNoise", (-1000, -1250))
micro.inputs["Scale"].default_value = CFG["micro_scale"]
bump = node("ShaderNodeBump", (-700, -1100))
bump.inputs["Strength"].default_value = CFG["micro_bump"]
L(micro.outputs["Fac"], bump.inputs["Height"])
L(nmap.outputs["Normal"], bump.inputs["Normal"])

# ---- principled
p = node("ShaderNodeBsdfPrincipled", (250, 300))
L(base2.outputs["Result"], p.inputs["Base Color"])
L(gold, p.inputs["Metallic"])
L(r3.outputs["Result"], p.inputs["Roughness"])
L(bump.outputs["Normal"], p.inputs["Normal"])
# anisotropy on gold
an = nmath("MULTIPLY", gold, CFG["gold_aniso"], (0, 60))
L(an, p.inputs["Anisotropic"])
# sheen on cloth
sh = nmath("MULTIPLY", cloth, CFG["cloth_sheen"], (0, -60))
L(sh, p.inputs["Sheen Weight"])
# subsurface on skin
ss = nmath("MULTIPLY", skin, CFG["sss_weight"], (0, -180))
L(ss, p.inputs["Subsurface Weight"])
p.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.18)
p.inputs["Subsurface Scale"].default_value = CFG["sss_scale"]
if t_emit is not None:
    L(t_emit.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = CFG["emit_strength"]

out = node("ShaderNodeOutputMaterial", (700, 300))

if MASK_DEBUG:
    # visualize masks: R=gold G=skin B=cloth
    comb = node("ShaderNodeCombineColor", (250, -400))
    L(gold, comb.inputs[0]); L(skin, comb.inputs[1]); L(cloth, comb.inputs[2])
    em = node("ShaderNodeEmission", (450, -400))
    L(comb.outputs[0], em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
elif ALBEDO_DEBUG:
    em = node("ShaderNodeEmission", (450, -400))
    L(t_alb.outputs["Color"], em.inputs["Color"])
    L(em.outputs[0], out.inputs["Surface"])
else:
    L(p.outputs[0], out.inputs["Surface"])

# ------------------------------------------------------------------ world (dark gradient)
w = bpy.data.worlds.new("DeclayWorld")
scn.world = w
w.use_nodes = True
wn, wl = w.node_tree.nodes, w.node_tree.links
wn.clear()
tc = wn.new("ShaderNodeTexCoord"); tc.location = (-800, 0)
sep = wn.new("ShaderNodeSeparateXYZ"); sep.location = (-600, 0)
wl.new(tc.outputs["Generated"], sep.inputs[0])
mr = wn.new("ShaderNodeMapRange"); mr.location = (-400, 0)
mr.inputs["From Min"].default_value = -1.0
mr.inputs["From Max"].default_value = 1.0
wl.new(sep.outputs["Z"], mr.inputs["Value"])
ramp = wn.new("ShaderNodeValToRGB"); ramp.location = (-200, 0)
ramp.color_ramp.elements[0].color = (*CFG["world_bot"], 1.0)
ramp.color_ramp.elements[1].color = (*CFG["world_top"], 1.0)
wl.new(mr.outputs["Result"], ramp.inputs["Fac"])
bg = wn.new("ShaderNodeBackground"); bg.location = (0, 0)
wl.new(ramp.outputs["Color"], bg.inputs["Color"])
wout = wn.new("ShaderNodeOutputWorld"); wout.location = (200, 0)
wl.new(bg.outputs[0], wout.inputs["Surface"])

# ------------------------------------------------------------------ lights
def area(name, loc, target, size, color, power, shape="SQUARE", size_y=None, cam_vis=False):
    d = bpy.data.lights.new(name, "AREA")
    d.shape = shape
    d.size = size
    if size_y:
        d.size_y = size_y
    d.color = color
    d.energy = power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    o.visible_camera = cam_vis
    return o

tgt = (center.x, center.y, center.z + 0.1 * H)
Hs = H  # scale helper
area("Key", (center.x - 1.1 * Hs, center.y - 1.2 * Hs, bb_max.z + 0.5 * Hs), tgt,
     1.2 * Hs, CFG["key_color"], CFG["key_power"] * Hs * Hs)
area("Fill", (center.x + 1.3 * Hs, center.y - 1.0 * Hs, center.z), tgt,
     1.6 * Hs, CFG["fill_color"], CFG["fill_power"] * Hs * Hs)
area("RimWarm", (center.x - 0.9 * Hs, center.y + 1.1 * Hs, bb_max.z + 0.2 * Hs), tgt,
     0.8 * Hs, CFG["rim1_color"], CFG["rim1_power"] * Hs * Hs)
area("RimCool", (center.x + 1.0 * Hs, center.y + 1.0 * Hs, center.z + 0.4 * Hs), tgt,
     0.8 * Hs, CFG["rim2_color"], CFG["rim2_power"] * Hs * Hs)

# emissive reflection cards (camera-invisible, exist so the gold has streaks to reflect)
def card(name, loc, target, sx, sy, color, strength):
    m = bpy.data.meshes.new(name)
    o = bpy.data.objects.new(name, m)
    scn.collection.objects.link(o)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bm.to_mesh(m); bm.free()
    o.scale = (sx, sy, 1)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    cm = bpy.data.materials.new(name + "_mat")
    cm.use_nodes = True
    cm.node_tree.nodes.clear()
    e = cm.node_tree.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1.0)
    e.inputs["Strength"].default_value = strength
    oo = cm.node_tree.nodes.new("ShaderNodeOutputMaterial")
    cm.node_tree.links.new(e.outputs[0], oo.inputs["Surface"])
    o.data.materials.append(cm)
    o.visible_camera = False
    o.visible_shadow = False
    return o

card("CardWarm", (center.x - 1.6 * Hs, center.y - 0.6 * Hs, center.z + 0.6 * Hs), tgt,
     0.5 * Hs, 2.2 * Hs, CFG["card_warm"], CFG["card_warm_str"])
card("CardCool", (center.x + 1.7 * Hs, center.y - 0.4 * Hs, center.z + 0.3 * Hs), tgt,
     0.4 * Hs, 2.0 * Hs, CFG["card_cool"], CFG["card_cool_str"])
card("CardTop", (center.x, center.y - 0.3 * Hs, bb_max.z + 1.0 * Hs), tgt,
     2.0 * Hs, 0.8 * Hs, (1.0, 0.82, 0.58), 0.55)

# ------------------------------------------------------------------ cameras + render
def shoot(name, focal, look_z, fit_h, suffix):
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36.0
    cam = bpy.data.objects.new(name, cd)
    scn.collection.objects.link(cam)
    look = Vector((center.x, center.y, look_z))
    fov = 2 * math.atan(36.0 / (2 * focal))
    dist = (fit_h / 2 * 1.18) / math.tan(fov / 2)
    yaw = math.radians(CFG["cam_yaw_deg"])
    off = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * dist
    cam.location = look + off + Vector((0, 0, 0.02 * H))
    direc = (look - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam
    path = f"{OUTDIR}/p{PASS}_{suffix}{'_mask' if MASK_DEBUG else ''}.png"
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[declay] wrote {path}")

shoot("CamFull", CFG["cam_full_f"], center.z, H, "full")
shoot("CamBust", CFG["cam_bust_f"], bb_min.z + 0.82 * H, 0.42 * H, "bust")
print("[declay] DONE")
