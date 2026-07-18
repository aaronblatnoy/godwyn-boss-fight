# bake_gameasset.py — Phase 1: bake the de-clay PBR into the RIGGED asset.
#
# Imports models/godwyn_rigged_raw.glb (Armature + skinned char1, Meshy baseColor
# texture_0 on Material_1), derives the de-clay masks from the albedo (same logic
# family as declay_material.py: warm+saturated => GOLD metal, blue/near-black =>
# CLOTH with the royal-blue fix, warm low-sat => SKIN), bakes ALBEDO / METALLIC /
# ROUGHNESS (+ a mask-debug RGB) to new UV images via the Cycles EMIT trick,
# assigns a clean glTF-friendly Principled material, removes strays (Icosphere),
# and saves models/godwyn_gameasset.blend + PNG maps.
#
# Rig hardening (round 1 fixes): armature/bones/modifiers are NEVER modified,
# but the raw Meshy VERTEX WEIGHTS are hardened after import — hand/arm groups
# are smoothed (candy-wrapper fix), robe-cloth verts are rebound off the arm
# chain onto Shoulder/Spine + pushed slightly proud of the body (clip fix),
# influences capped at 4 and re-normalized (asserted).
#
# Headless:
#   blender --background --python ~/godwyn-boss-fight/scripts/bake_gameasset.py -- \
#       [res=2048] [samples=8] [skip_bake=1] [preview=1] [debugmat=mask|albedo]
#
#   default run = bake + save + EEVEE previews (full + bust).
#   skip_bake=1 reopens the saved .blend and just re-renders previews.
#   debugmat=mask previews the RGB mask bake (R=gold G=skin B=cloth).

import bpy, sys, os, math
from mathutils import Vector

ARGS = {}
if "--" in sys.argv:
    for a in sys.argv[sys.argv.index("--") + 1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            ARGS[k] = v

RES = int(ARGS.get("res", "2048"))
SAMPLES = int(ARGS.get("samples", "8"))
SKIP_BAKE = ARGS.get("skip_bake", "0") == "1"
DEBUGMAT = ARGS.get("debugmat", "")  # "", "mask", "albedo"

HOME = os.path.expanduser("~")
GLB = f"{HOME}/godwyn-boss-fight/models/godwyn_rigged_raw.glb"
BLEND = f"{HOME}/godwyn-boss-fight/models/godwyn_gameasset.blend"
TEXDIR = f"{HOME}/godwyn-boss-fight/models/textures_gameasset"
OUTDIR = f"{HOME}/godwyn-boss-fight/renders/gameasset"
os.makedirs(TEXDIR, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

CFG = dict(
    # masks from albedo HSV (linear space) — start from declay_material.py values,
    # to be tuned per-iteration for the Meshy rigged texture.
    gold_hue_lo=0.030, gold_hue_hi=0.160, gold_sat_min=0.550, gold_val_min=0.08,
    skin_hue_lo=0.00, skin_hue_hi=0.090, skin_sat_lo=0.10, skin_sat_hi=0.70,
    skin_val_min=0.20,
    blue_hue_lo=0.50, blue_hue_hi=0.90,
    dark_val_max=0.10,
    mask_soft=0.025,
    # gold
    gold_rough_lo=0.30, gold_rough_hi=0.46,
    gold_tint=(0.82, 0.60, 0.15), gold_tint_mix=0.85,  # SPEC gold armor family
    rough_noise_scale=60.0,
    # cloth / THE BLUE FIX
    cloth_rough=0.70,
    blue_target=(0.08, 0.12, 0.35),
    blue_mix=0.97,
    blue_val_boost=0.68,
    blue_sat_boost=1.55,
    # skin
    skin_rough=0.45,
    base_rough=0.55,
    bake_margin=8,
)

# ---------------------------------------------------------------- GPU helper
def setup_cycles_gpu(scn, samples):
    scn.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    n_gpu = 0
    for d in prefs.devices:
        d.use = (d.type == "OPTIX")
        if d.use:
            n_gpu += 1
    assert n_gpu > 0, "FATAL: no OptiX GPU available — refusing CPU fallback"
    scn.cycles.device = "GPU"
    scn.cycles.samples = samples
    print(f"[bake] OptiX GPUs enabled: {n_gpu}")

def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[bake] preview engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine id worked")

# ================================================================ BAKE STAGE
if not SKIP_BAKE:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    setup_cycles_gpu(scn, SAMPLES)

    bpy.ops.import_scene.gltf(filepath=GLB)

    # ---- identify objects
    arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
    assert arm is not None, "no armature imported"
    char = None
    strays = []
    for o in list(scn.objects):
        if o.type == "MESH":
            if len(o.vertex_groups) > 0 and o.data.uv_layers:
                char = o
            else:
                strays.append(o)
    assert char is not None, "no skinned mesh found"
    print(f"[bake] char={char.name} verts={len(char.data.vertices)} "
          f"vgroups={len(char.vertex_groups)} uv={[u.name for u in char.data.uv_layers]}")
    print(f"[bake] armature={arm.name} bones={len(arm.data.bones)}")

    # ---- remove strays (Icosphere etc.)
    for o in strays:
        print(f"[bake] removing stray object: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)

    # ---- harvest albedo image from Material_1
    assert char.data.materials, "char has no material"
    src_mat = char.data.materials[0]
    img_albedo = None
    for n in src_mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            img_albedo = n.image
            break
    assert img_albedo is not None, "no albedo image found on source material"
    print(f"[bake] albedo image: {img_albedo.name} {tuple(img_albedo.size)}")

    # ================= RIG HARDENING (Phase 2 round-1 fixes #1 + #2) =========
    # The raw Meshy weights candy-wrap at the wrists/fingers, and the robe is
    # skinned to the arm chain so it gets dragged through the forearm on a
    # raised-arm pose. Fix IN THE MESH WEIGHTS ONLY — the armature, bones and
    # modifier stack are never modified, so the rig stays intact.
    import re
    import numpy as np

    def _cloth_mask_per_vertex(mesh, img):
        """Boolean per-vertex mask: True where the albedo under the vertex's UV
        is robe cloth (blue hue band, or near-black) — same CFG family as the
        shader-side cloth mask."""
        W, H = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        nv = len(mesh.vertices)
        uv = np.zeros((nv, 2), dtype=np.float32)
        seen = np.zeros(nv, dtype=bool)
        uvd = mesh.uv_layers.active.data
        for lp in mesh.loops:
            vi = lp.vertex_index
            if not seen[vi]:
                u, v = uvd[lp.index].uv
                uv[vi] = (u % 1.0, v % 1.0)
                seen[vi] = True
        xi = np.clip((uv[:, 0] * W).astype(np.int32), 0, W - 1)
        yi = np.clip((uv[:, 1] * H).astype(np.int32), 0, H - 1)
        rgb = px[yi, xi, :3]
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
        mx = rgb.max(axis=1)
        mn = rgb.min(axis=1)
        C = mx - mn
        S = np.where(mx > 1e-6, C / np.maximum(mx, 1e-6), 0.0)
        Hu = np.zeros(nv, dtype=np.float32)
        m = (mx == r) & (C > 1e-6); Hu[m] = ((g - b)[m] / C[m]) % 6.0
        m = (mx == g) & (C > 1e-6); Hu[m] = ((b - r)[m] / C[m]) + 2.0
        m = (mx == b) & (C > 1e-6); Hu[m] = ((r - g)[m] / C[m]) + 4.0
        Hu /= 6.0
        blue = (Hu >= CFG["blue_hue_lo"]) & (Hu <= CFG["blue_hue_hi"]) & (S > 0.15)
        dark = mx < CFG["dark_val_max"]
        return blue | dark

    def harden_rig(char, arm, img_albedo):
        mesh = char.data
        bpy.ops.object.select_all(action="DESELECT")
        char.select_set(True)
        bpy.context.view_layer.objects.active = char

        gnames = [g.name for g in char.vertex_groups]
        RX_FINGER = re.compile(r"(Thumb|Index|Middle|Ring|Pinky)")
        RX_HANDCHAIN = re.compile(r"(Hand|ForeArm|\bArm|Arm$|Shoulder)")
        # r2 fix #2: include neck/Head so the collar boundary behind the turned
        # head is smoothed too (collar pinch at the neck/RightShoulder seam)
        RX_NECK = re.compile(r"(neck|Neck|Head)")
        smooth_targets = [n for n in gnames
                          if RX_FINGER.search(n) or RX_HANDCHAIN.search(n)
                          or RX_NECK.search(n)
                          or ("Arm" in n) or ("Hand" in n) or ("Shoulder" in n)]
        print(f"[rig] weight-smoothing {len(smooth_targets)} hand/arm/neck groups")

        # 1) smooth hand/finger/arm weights (kills the candy-wrapper crimp)
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
        for n in smooth_targets:
            char.vertex_groups.active_index = char.vertex_groups[n].index
            bpy.ops.object.vertex_group_smooth(
                group_select_mode="ACTIVE", factor=0.5, repeat=4, expand=0.15)
        bpy.ops.object.mode_set(mode="OBJECT")

        # 2) robe rebind: cloth verts influenced by the arm chain get a
        #    SMOOTHLY-VARYING fraction of that weight transferred to the
        #    same-side Shoulder so the robe hangs from the torso instead of
        #    being dragged through the forearm. The raw texture-sampled cloth
        #    mask is NOISY (gold trim on the robe), so it is first DIFFUSED
        #    over the mesh adjacency graph — a binary/noisy transfer shears
        #    neighboring verts apart and shreds the robe in pose (r2 lesson).
        nv = len(mesh.vertices)
        cloth = _cloth_mask_per_vertex(mesh, img_albedo)
        print(f"[rig] raw cloth verts: {int(cloth.sum())}/{nv}")

        ne = len(mesh.edges)
        ev = np.empty(ne * 2, dtype=np.int32)
        mesh.edges.foreach_get("vertices", ev)
        e0, e1 = ev[0::2], ev[1::2]
        deg = np.zeros(nv, dtype=np.float32)
        np.add.at(deg, e0, 1.0)
        np.add.at(deg, e1, 1.0)
        deg = np.maximum(deg, 1.0)
        f = cloth.astype(np.float32)
        for _ in range(15):
            acc = np.zeros(nv, dtype=np.float32)
            np.add.at(acc, e0, f[e1])
            np.add.at(acc, e1, f[e0])
            f = 0.5 * f + 0.5 * (acc / deg)
        # r2 fix #1: threshold LOWERED (was (f-0.35)/(0.90-0.35)) so clear robe
        # verts reach t ~= 1.0 and shed essentially ALL Arm/ForeArm influence —
        # residual arm weight was still dragging the drape into spikes.
        t = np.clip((f - 0.20) / (0.70 - 0.20), 0.0, 1.0)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep -> continuous transfer field
        print(f"[rig] diffused cloth field: full-transfer verts (t>0.99): "
              f"{int((t > 0.99).sum())}, partial (0.01<t<=0.99): "
              f"{int(((t > 0.01) & (t <= 0.99)).sum())}")

        gi = {g.index: g.name for g in char.vertex_groups}
        byname = {g.name: g for g in char.vertex_groups}
        # transfer ONLY Arm/ForeArm influence — never Hand/finger weights (the
        # sword + scabbard are rigid hand-held parts; touching Hand weights
        # shreds them, r2 lesson #2)
        RX_ARMCHAIN = re.compile(r"^(Left|Right)(Arm|ForeArm)$")
        RX_HANDGRP = re.compile(r"^(Left|Right)Hand")

        # ---- connected components (union-find) so hand-held equipment
        #      components (dominant Hand weight, e.g. the blue-bladed sword)
        #      are excluded from the robe rebind entirely.
        parent = np.arange(nv, dtype=np.int64)

        def find(a):
            root = a
            while parent[root] != root:
                root = parent[root]
            while parent[a] != root:
                parent[a], a = root, parent[a]
            return root

        for i in range(ne):
            ra, rb = find(int(e0[i])), find(int(e1[i]))
            if ra != rb:
                parent[rb] = ra

        comp = np.array([find(i) for i in range(nv)], dtype=np.int64)
        hand_w = np.zeros(nv, dtype=np.float32)
        total_w = np.zeros(nv, dtype=np.float32)
        for v in mesh.vertices:
            for ge in v.groups:
                total_w[v.index] += ge.weight
                if RX_HANDGRP.match(gi[ge.group]):
                    hand_w[v.index] += ge.weight
        comp_ids, comp_inv = np.unique(comp, return_inverse=True)
        ch = np.zeros(len(comp_ids)); ct = np.zeros(len(comp_ids))
        np.add.at(ch, comp_inv, hand_w)
        np.add.at(ct, comp_inv, total_w)
        comp_hand_frac = ch / np.maximum(ct, 1e-6)
        # r2 fix #1b: the old whole-component exclusion (comp_hand_frac>0.25)
        # also dropped ROBE verts that merely share a connected component with
        # the sword hand, so they kept full arm weight and TORE in the swing.
        # Exclude per-vertex (hand_w>0.25 -> genuinely gripped/held geometry),
        # plus only STRONGLY hand-dominated components (>0.6 = the rigid sword
        # / scabbard themselves) — never a merged robe+hand component.
        held = (hand_w > 0.25) | (comp_hand_frac[comp_inv] > 0.60)
        n_held_comps = int((comp_hand_frac > 0.60).sum())
        print(f"[rig] components: {len(comp_ids)}, rigid held comps (excluded): "
              f"{n_held_comps}; per-vertex held total: {int(held.sum())} verts")
        t[held] = 0.0

        def side_target(side):
            g = byname.get(f"{side}Shoulder")
            if g is not None:
                return g
            for n in ("Spine02", "Spine01", "Spine"):
                if n in byname:
                    return byname[n]
            return None

        # r2 fix #2: collar cloth must hang from the TORSO/NECK, not the arm
        # chain or even the Shoulder — shoulder rotation was crimping the
        # collar behind the turned head. Collar region = cloth verts above the
        # neck-bone line; their transfer ALSO strips Shoulder weight and lands
        # on Spine02/neck instead.
        def collar_target():
            for n in ("Spine02", "neck", "Neck", "Spine01", "Spine"):
                if n in byname:
                    return byname[n]
            return None

        zs_all = np.array([v.co.z for v in mesh.vertices], dtype=np.float32)
        z_lo, z_hi = float(zs_all.min()), float(zs_all.max())
        Hloc = max(z_hi - z_lo, 1e-6)
        collar_z = z_lo + 0.82 * Hloc
        nb = arm.data.bones.get("neck") or arm.data.bones.get("Neck")
        if nb is not None:
            try:
                import mathutils
                wz = (char.matrix_world.inverted() @ (arm.matrix_world @ nb.head_local)).z
                collar_z = wz - 0.02 * Hloc
            except Exception as ex:
                print(f"[rig] collar_z fallback ({ex})")
        print(f"[rig] collar_z={collar_z:.4f} (mesh z {z_lo:.3f}..{z_hi:.3f})")

        RX_ARMCHAIN_COLLAR = re.compile(r"^(Left|Right)(Arm|ForeArm|Shoulder)$")

        armw_before = np.zeros(nv, dtype=np.float32)
        rebound = collar_rebound = 0
        for v in mesh.vertices:
            tv = float(t[v.index])
            if tv <= 0.01:
                continue
            is_collar = v.co.z >= collar_z
            rx = RX_ARMCHAIN_COLLAR if is_collar else RX_ARMCHAIN
            moves = []  # (group_name, old_weight)
            for ge in v.groups:
                n = gi[ge.group]
                if ge.weight > 0.0 and rx.match(n):
                    moves.append((n, ge.weight))
            if not moves:
                continue
            armw_before[v.index] = sum(w for _, w in moves)
            moved = {"Left": 0.0, "Right": 0.0}
            for n, w in moves:
                side = "Left" if n.startswith("Left") else "Right"
                keep = w * (1.0 - tv)
                moved[side] += w * tv
                if keep > 1e-5:
                    byname[n].add([v.index], keep, "REPLACE")
                else:
                    byname[n].remove([v.index])
            for side, mw in moved.items():
                if mw > 1e-5:
                    tgt = collar_target() if is_collar else side_target(side)
                    if tgt is not None:
                        tgt.add([v.index], mw, "ADD")
            rebound += 1
            if is_collar:
                collar_rebound += 1
        print(f"[rig] robe verts partially rebound off arm chain: {rebound} "
              f"(collar->Spine02/neck: {collar_rebound})")

        # r2 fix #1c: extra smoothing pass over the REBIND TARGET groups
        # (Shoulder/Spine/neck) to erase the shear seam where transferred
        # weight meets untouched weight.
        RX_TGT = re.compile(r"(Shoulder|Spine|neck|Neck)")
        tgt_groups = [n for n in [g.name for g in char.vertex_groups]
                      if RX_TGT.search(n)]
        bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
        for n in tgt_groups:
            char.vertex_groups.active_index = char.vertex_groups[n].index
            bpy.ops.object.vertex_group_smooth(
                group_select_mode="ACTIVE", factor=0.5, repeat=5, expand=0.10)
        bpy.ops.object.mode_set(mode="OBJECT")
        print(f"[rig] post-rebind smoothing on {len(tgt_groups)} target groups")

        # 3) push the rebound robe region slightly proud of the body; the
        #    offset follows the SMOOTH t-field * prior arm weight so there is
        #    no seam step anywhere.
        # r2 fix #3: 0.002*H was too small for the raised forearm to clear the
        # cloth — scale the proud offset up through the swing-affected
        # upper-robe/collar region (up to ~3x at chest/collar height).
        Hgt_local = Hloc
        max_off = 0.003 * Hgt_local
        for v in mesh.vertices:
            k = float(t[v.index]) * min(float(armw_before[v.index]), 1.0)
            if k > 0.0:
                zn = (v.co.z - z_lo) / Hgt_local
                up = min(max((zn - 0.45) / 0.30, 0.0), 1.0)  # 0 below waist, 1 at chest+
                v.co += v.normal * (max_off * (1.0 + 2.0 * up) * k)
        print(f"[rig] robe proud-offset: base {max_off:.4f}, "
              f"upper-region max {max_off * 3.0:.4f} (local units)")

        # 4) cap influences at 4 (game-engine budget) + renormalize everything
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL",
                                                  lock_active=False)

        # 5) HARD ASSERT: every vertex normalized to 1.0 with <=4 influences
        bad_norm = bad_infl = orphans = 0
        for v in mesh.vertices:
            ws = [ge.weight for ge in v.groups if ge.weight > 0.0]
            if not ws:
                orphans += 1
                continue
            if abs(sum(ws) - 1.0) > 1e-3:
                bad_norm += 1
            if len(ws) > 4:
                bad_infl += 1
        print(f"[rig] normalize check: bad_norm={bad_norm} bad_infl={bad_infl} "
              f"orphans={orphans}")
        assert bad_norm == 0, f"{bad_norm} verts not weight-normalized"
        assert bad_infl == 0, f"{bad_infl} verts exceed 4 influences"
        assert orphans == 0, f"{orphans} verts have no bone weights"

    harden_rig(char, arm, img_albedo)

    # ---- build BAKE SOURCE material (masks + channels, emission-switchable)
    bmat = bpy.data.materials.new("GodwynBakeSrc")
    bmat.use_nodes = True
    nt = bmat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new

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

    uvn = node("ShaderNodeTexCoord", (-1700, 0))
    t_alb = node("ShaderNodeTexImage", (-1500, 300))
    t_alb.image = img_albedo
    L(uvn.outputs["UV"], t_alb.inputs["Vector"])

    hsv = node("ShaderNodeSeparateColor", (-1250, 300), mode="HSV")
    L(t_alb.outputs["Color"], hsv.inputs["Color"])
    Hh, Ss, Vv = hsv.outputs[0], hsv.outputs[1], hsv.outputs[2]

    # GOLD
    g_h = band(Hh, CFG["gold_hue_lo"], CFG["gold_hue_hi"], (-1000, 500))
    g_s = smooth_gt(Ss, CFG["gold_sat_min"], (-1000, 250))
    g_v = smooth_gt(Vv, CFG["gold_val_min"], (-1000, 100))
    gold = nmath("MULTIPLY", nmath("MULTIPLY", g_h, g_s, (-700, 400)), g_v, (-550, 400), clamp=True)

    # SKIN
    k_h = band(Hh, CFG["skin_hue_lo"], CFG["skin_hue_hi"], (-1000, -50))
    k_s = band(Ss, CFG["skin_sat_lo"], CFG["skin_sat_hi"], (-1000, -250))
    k_v = smooth_gt(Vv, CFG["skin_val_min"], (-1000, -430))
    skin = nmath("MULTIPLY", nmath("MULTIPLY", k_h, k_s, (-700, -150)), k_v, (-550, -150), clamp=True)
    skin = nmath("MULTIPLY", skin, nmath("SUBTRACT", 1.0, gold, (-560, -260), clamp=True), (-400, -150), clamp=True)

    # CLOTH: blue hue OR near-black
    c_b = band(Hh, CFG["blue_hue_lo"], CFG["blue_hue_hi"], (-1000, -650))
    c_d = smooth_lt(Vv, CFG["dark_val_max"], (-1000, -850))
    cloth = nmath("MAXIMUM", c_b, c_d, (-700, -700))
    not_gs = nmath("SUBTRACT", nmath("SUBTRACT", 1.0, gold, (-720, -820), clamp=True), skin, (-560, -820), clamp=True)
    cloth = nmath("MULTIPLY", cloth, not_gs, (-400, -700), clamp=True)

    # ---- ALBEDO channel (blue-fixed base color)
    goldize = node("ShaderNodeMix", (-700, 700), data_type="RGBA", blend_type="MIX")
    goldize.inputs["Factor"].default_value = CFG["gold_tint_mix"]
    L(t_alb.outputs["Color"], goldize.inputs["A"])
    goldize.inputs["B"].default_value = (*CFG["gold_tint"], 1.0)

    base1 = node("ShaderNodeMix", (-450, 700), data_type="RGBA", blend_type="MIX")
    L(gold, base1.inputs["Factor"])
    L(t_alb.outputs["Color"], base1.inputs["A"])
    L(goldize.outputs["Result"], base1.inputs["B"])

    blued = node("ShaderNodeMix", (-450, 480), data_type="RGBA", blend_type="MIX")
    blued.inputs["Factor"].default_value = CFG["blue_mix"]
    L(t_alb.outputs["Color"], blued.inputs["A"])
    blued.inputs["B"].default_value = (*CFG["blue_target"], 1.0)
    blift = node("ShaderNodeHueSaturation", (-260, 480))
    blift.inputs["Saturation"].default_value = CFG["blue_sat_boost"]
    blift.inputs["Value"].default_value = CFG["blue_val_boost"]
    L(blued.outputs["Result"], blift.inputs["Color"])

    base2 = node("ShaderNodeMix", (-80, 640), data_type="RGBA", blend_type="MIX")
    L(cloth, base2.inputs["Factor"])
    L(base1.outputs["Result"], base2.inputs["A"])
    L(blift.outputs["Color"], base2.inputs["B"])

    # ---- ROUGHNESS channel
    noise = node("ShaderNodeTexNoise", (-1000, 900))
    noise.inputs["Scale"].default_value = CFG["rough_noise_scale"]
    g_rough_mr = node("ShaderNodeMapRange", (-800, 900))
    g_rough_mr.inputs["To Min"].default_value = CFG["gold_rough_lo"]
    g_rough_mr.inputs["To Max"].default_value = CFG["gold_rough_hi"]
    L(noise.outputs["Fac"], g_rough_mr.inputs["Value"])
    r1 = node("ShaderNodeMix", (-500, 900), data_type="FLOAT")
    r1.inputs["A"].default_value = CFG["base_rough"]
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

    # ---- mask debug RGB
    comb = node("ShaderNodeCombineColor", (0, -400))
    L(gold, comb.inputs[0]); L(skin, comb.inputs[1]); L(cloth, comb.inputs[2])

    emit = node("ShaderNodeEmission", (300, 300))
    outn = node("ShaderNodeOutputMaterial", (550, 300))
    L(emit.outputs[0], outn.inputs["Surface"])

    # bake target image node (active)
    t_bake = node("ShaderNodeTexImage", (300, -100))

    # assign bake material to char
    char.data.materials.clear()
    char.data.materials.append(bmat)

    # select char only
    bpy.ops.object.select_all(action="DESELECT")
    char.select_set(True)
    bpy.context.view_layer.objects.active = char

    scn.render.bake.margin = CFG["bake_margin"]
    scn.cycles.use_denoising = False

    def bake_channel(sock, name, colorspace, is_color):
        img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
        img.colorspace_settings.name = colorspace
        t_bake.image = img
        # wire channel -> emission
        for lk in list(emit.inputs["Color"].links):
            nt.links.remove(lk)
        L(sock, emit.inputs["Color"])
        for n in nt.nodes:
            n.select = False
        t_bake.select = True
        nt.nodes.active = t_bake
        print(f"[bake] baking {name} ({RES}x{RES}, {SAMPLES} spp)...")
        bpy.ops.object.bake(type="EMIT", use_clear=True,
                            margin=CFG["bake_margin"])
        path = f"{TEXDIR}/{name}.png"
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        img.pack()
        print(f"[bake] wrote {path}")
        return img

    img_alb_baked = bake_channel(base2.outputs["Result"], "godwyn_albedo", "sRGB", True)
    img_met_baked = bake_channel(gold, "godwyn_metallic", "Non-Color", False)
    img_rgh_baked = bake_channel(r3.outputs["Result"], "godwyn_roughness", "Non-Color", False)
    img_msk_baked = bake_channel(comb.outputs[0], "godwyn_maskdebug", "sRGB", True)

    # ---- assign CLEAN glTF-friendly material
    fmat = bpy.data.materials.new("GodwynGameMat")
    fmat.use_nodes = True
    fnt = fmat.node_tree
    fnt.nodes.clear()

    def fnode(t, loc, **props):
        n = fnt.nodes.new(t)
        n.location = loc
        for k, v in props.items():
            setattr(n, k, v)
        return n

    ft_alb = fnode("ShaderNodeTexImage", (-600, 300)); ft_alb.image = img_alb_baked
    ft_met = fnode("ShaderNodeTexImage", (-600, 0)); ft_met.image = img_met_baked
    ft_rgh = fnode("ShaderNodeTexImage", (-600, -300)); ft_rgh.image = img_rgh_baked
    fp = fnode("ShaderNodeBsdfPrincipled", (-100, 200))
    fout = fnode("ShaderNodeOutputMaterial", (300, 200))
    FL = fnt.links.new
    FL(ft_alb.outputs["Color"], fp.inputs["Base Color"])
    FL(ft_met.outputs["Color"], fp.inputs["Metallic"])
    FL(ft_rgh.outputs["Color"], fp.inputs["Roughness"])
    FL(fp.outputs[0], fout.inputs["Surface"])

    char.data.materials.clear()
    char.data.materials.append(fmat)

    # keep debug mats around (fake user) for preview modes
    bmat.use_fake_user = True

    # ---- rig sanity
    mods = [m for m in char.modifiers if m.type == "ARMATURE"]
    print(f"[bake] RIG CHECK: armature_mod={len(mods)} vgroups={len(char.vertex_groups)} "
          f"bones={len(arm.data.bones)}")
    assert len(char.vertex_groups) >= 24 and len(arm.data.bones) >= 24

    # ---- save blend
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"[bake] saved {BLEND}")
else:
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scn = bpy.context.scene
    print(f"[bake] reopened {BLEND}")

# ================================================================ PREVIEW STAGE
scn = bpy.context.scene
char = next(o for o in scn.objects if o.type == "MESH" and len(o.vertex_groups) > 0)
arm = next(o for o in scn.objects if o.type == "ARMATURE")

if DEBUGMAT == "mask":
    # swap to an emission-view of the baked mask debug image
    dm = bpy.data.materials.new("GodwynMaskView")
    dm.use_nodes = True
    dnt = dm.node_tree
    dnt.nodes.clear()
    ti = dnt.nodes.new("ShaderNodeTexImage")
    ti.image = bpy.data.images["godwyn_maskdebug"]
    em = dnt.nodes.new("ShaderNodeEmission")
    oo = dnt.nodes.new("ShaderNodeOutputMaterial")
    dnt.links.new(ti.outputs["Color"], em.inputs["Color"])
    dnt.links.new(em.outputs[0], oo.inputs["Surface"])
    char.data.materials.clear()
    char.data.materials.append(dm)
elif DEBUGMAT == "albedo":
    dm = bpy.data.materials.new("GodwynAlbedoView")
    dm.use_nodes = True
    dnt = dm.node_tree
    dnt.nodes.clear()
    ti = dnt.nodes.new("ShaderNodeTexImage")
    ti.image = bpy.data.images["godwyn_albedo"]
    em = dnt.nodes.new("ShaderNodeEmission")
    oo = dnt.nodes.new("ShaderNodeOutputMaterial")
    dnt.links.new(ti.outputs["Color"], em.inputs["Color"])
    dnt.links.new(em.outputs[0], oo.inputs["Surface"])
    char.data.materials.clear()
    char.data.materials.append(dm)

pick_eevee(scn)
scn.render.resolution_x, scn.render.resolution_y = 1024, 1365
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"
if DEBUGMAT:
    scn.view_settings.view_transform = "Standard"
    scn.view_settings.look = "None"

# bbox
pts = [char.matrix_world @ Vector(c) for c in char.bound_box]
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z
print(f"[bake] preview bbox H={Hgt:.3f} center={tuple(round(v,3) for v in center)}")

# world
w = bpy.data.worlds.get("GamePreviewWorld") or bpy.data.worlds.new("GamePreviewWorld")
scn.world = w
w.use_nodes = True
wbg = w.node_tree.nodes.get("Background")
if wbg:
    wbg.inputs["Color"].default_value = (0.010, 0.012, 0.020, 1.0)
    wbg.inputs["Strength"].default_value = 1.0

# lights (idempotent by name)
def area(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size = size
    d.color = color
    d.energy = power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    return o

tgt = (center.x, center.y, center.z + 0.1 * Hgt)
Hs = Hgt
area("PKey", (center.x - 1.1 * Hs, center.y - 1.2 * Hs, bb_max.z + 0.5 * Hs), tgt,
     1.2 * Hs, (1.0, 0.72, 0.42), 170.0 * Hs * Hs)
area("PFill", (center.x + 1.3 * Hs, center.y - 1.0 * Hs, center.z), tgt,
     1.6 * Hs, (0.35, 0.50, 0.95), 28.0 * Hs * Hs)
area("PRimW", (center.x - 0.9 * Hs, center.y + 1.1 * Hs, bb_max.z + 0.2 * Hs), tgt,
     0.8 * Hs, (1.0, 0.65, 0.28), 130.0 * Hs * Hs)
area("PRimC", (center.x + 1.0 * Hs, center.y + 1.0 * Hs, center.z + 0.4 * Hs), tgt,
     0.8 * Hs, (0.55, 0.65, 1.0), 70.0 * Hs * Hs)

def shoot(name, focal, look_z, fit_h, suffix):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36.0
    cam = bpy.data.objects.new(name, cd)
    scn.collection.objects.link(cam)
    look = Vector((center.x, center.y, look_z))
    fov = 2 * math.atan(36.0 / (2 * focal))
    dist = (fit_h / 2 * 1.18) / math.tan(fov / 2)
    yaw = math.radians(18.0)
    off = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * dist
    cam.location = look + off + Vector((0, 0, 0.02 * Hgt))
    direc = (look - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam
    tag = f"_{DEBUGMAT}" if DEBUGMAT else ""
    path = f"{OUTDIR}/preview_{suffix}{tag}.png"
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[bake] wrote {path}")

shoot("PCamFull", 50, center.z, Hgt, "full")
shoot("PCamBust", 85, bb_min.z + 0.82 * Hgt, 0.42 * Hgt, "bust")
print("[bake] DONE")
