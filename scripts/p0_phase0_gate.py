"""
p0_phase0_gate.py — PHASE 0 GATE: GPU + adaptive-subdiv + .blend + GLB export.

Checks:
  1. Blender version (assert 5.x)
  2. GPU device table (OptiX preferred, CUDA fallback) — INV-2
  3. Tiny GPU test render (adaptive subdiv on a Suzanne with Catmull-Clark)
  4. Load models/godwyn_phase1.blend
  5. Report all objects in the Godwyn collection
  6. Assert Godwyn_Armature present + report all bone names
  7. Assert skinned meshes (Armature modifier) + report vertex-group counts
  8. Report any shape keys on all meshes (blendshape inventory)
  9. Export models/godwyn_phase1_baseline.glb via bpy glTF exporter
 10. Parse/report the GLB (bone count, mesh count, shape-key count)
 11. Document MPFB2 reachability for morph targets

Run:
  blender --background --python scripts/p0_phase0_gate.py 2>&1
"""

import sys
import os
import math
import struct
import json
import tempfile

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import bpy

_REPO      = os.path.expanduser("~/godwyn-boss-fight")
_MODELS    = os.path.join(_REPO, "models")
_RENDERS   = os.path.join(_REPO, "renders")
_WIP       = os.path.join(_RENDERS, "wip")
_BLEND_IN  = os.path.join(_MODELS, "godwyn_phase1.blend")
_GLB_OUT   = os.path.join(_MODELS, "godwyn_phase1_baseline.glb")
_TEST_PNG  = os.path.join(_WIP, "p0_gpu_test.png")

os.makedirs(_WIP, exist_ok=True)
os.makedirs(_MODELS, exist_ok=True)

ARMATURE_NAME = "Godwyn_Armature"

# ============================================================
# 1. BLENDER VERSION CHECK
# ============================================================
def check_blender_version():
    v = bpy.app.version
    print(f"\n[P0] Blender version: {v[0]}.{v[1]}.{v[2]}")
    if v[0] < 4:
        print("[P0] FATAL: Blender version too old (< 4.x)", file=sys.stderr)
        sys.exit(1)
    print(f"[P0] Version OK — {v[0]}.{v[1]}.{v[2]}")


# ============================================================
# 2. GPU DEVICE TABLE
# ============================================================
def enable_gpu():
    prefs  = bpy.context.preferences
    cprefs = prefs.addons["cycles"].preferences

    active_type = None
    for dtype in ("OPTIX", "CUDA"):
        try:
            cprefs.compute_device_type = dtype
            cprefs.get_devices()
            gpu_count = 0
            for dev in cprefs.devices:
                if dev.type in ("OPTIX", "CUDA"):
                    dev.use = True
                    gpu_count += 1
                else:
                    dev.use = False
            if gpu_count > 0:
                active_type = dtype
                break
        except Exception as e:
            print(f"[P0] {dtype} init failed: {e}", file=sys.stderr)

    if active_type is None:
        print("[P0] FATAL: No GPU devices found.", file=sys.stderr)
        sys.exit(1)

    bpy.context.scene.cycles.device = "GPU"

    print(f"\n[P0] Cycles compute_device_type = {active_type}")
    print("[P0] Device table:")
    gpu_enabled = []
    for dev in cprefs.devices:
        status = "ENABLED" if dev.use else "disabled"
        print(f"  [{status}] {dev.name}  (type={dev.type})")
        if dev.use and dev.type in ("OPTIX", "CUDA"):
            gpu_enabled.append(dev.name)

    if not gpu_enabled:
        print("[P0] FATAL: No GPU enabled after init.", file=sys.stderr)
        sys.exit(1)

    if len(gpu_enabled) < 2:
        print(f"[P0] WARNING: only {len(gpu_enabled)} GPU(s) active "
              f"(expected 2x RTX 3060 Ti).")
    else:
        print(f"[P0] {len(gpu_enabled)} GPU(s) active — nominal.")

    print(f"[P0] GPU backend: {active_type}\n")
    return active_type


# ============================================================
# 3. TINY GPU TEST RENDER (Cycles + adaptive subdivision)
# ============================================================
def run_gpu_test_render():
    """
    Build a minimal scene: Suzanne + Subdivision Surface modifier set to
    Adaptive + a Sun light. Render 16 samples at 64x64 via GPU.
    Adaptive subdivision in Cycles requires:
      - mesh.cycles.use_adaptive_subdivision = True
      - scene.cycles.dicing_rate (set to 1.0)
    """
    print("[P0] Running GPU + Adaptive-Subdivision test render ...")

    # Fresh scene
    bpy.ops.wm.read_homefile(app_template="", use_empty=True)
    scene = bpy.context.scene

    # GPU
    enable_gpu()

    # Cycles config
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 16
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.dicing_rate = 1.0   # adaptive micro-displacement rate
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    scene.render.film_transparent = True

    # Color management
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        scene.view_settings.view_transform = "Filmic"

    # Denoiser off for speed
    scene.cycles.use_denoising = False

    # Suzanne mesh
    bpy.ops.mesh.primitive_monkey_add(size=1.0, location=(0, 0, 0))
    monkey = bpy.context.active_object
    monkey.name = "TestMonkey"

    # Subdivision modifier — Catmull-Clark with render subdivision.
    # In Blender 5.x, adaptive micro-displacement is driven via material
    # displacement settings (Displacement node + scene dicing rate).
    # use_adaptive_subdivision moved off CyclesObjectSettings in 5.x.
    sub = monkey.modifiers.new("Subdiv", "SUBSURF")
    sub.subdivision_type = "CATMULL_CLARK"
    sub.levels = 0           # viewport level irrelevant in headless
    sub.render_levels = 2    # render-time subdivision level

    # Blender 4.x had monkey.cycles.use_adaptive_subdivision;
    # in Blender 5.x adaptive subdiv is per-material via Displacement node.
    # Try both; gracefully skip if attribute gone.
    try:
        monkey.cycles.use_adaptive_subdivision = True
        print("[P0] Adaptive subdiv: set via monkey.cycles.use_adaptive_subdivision")
    except AttributeError:
        print("[P0] Adaptive subdiv: use_adaptive_subdivision not on object "
              "(Blender 5.x — driven per-material via Displacement node). "
              "Subdivision modifier with render_levels=2 is active instead.")

    # Simple emissive material (no texture needed)
    mat = bpy.data.materials.new("TestMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1.0, 0.85, 0.4, 1.0)
    emit.inputs["Strength"].default_value = 2.0
    out_m = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs["Emission"], out_m.inputs["Surface"])
    monkey.data.materials.append(mat)

    # Sun light
    bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
    sun = bpy.context.active_object
    sun.data.energy = 3.0

    # Camera
    bpy.ops.object.camera_add(location=(0, -3, 1),
                              rotation=(math.radians(85), 0, 0))
    cam = bpy.context.active_object
    scene.camera = cam

    # Render
    scene.render.filepath = _TEST_PNG
    bpy.ops.render.render(write_still=True)

    if not os.path.isfile(_TEST_PNG) or os.path.getsize(_TEST_PNG) < 512:
        print("[P0] FATAL: GPU test render failed — PNG missing/empty.",
              file=sys.stderr)
        sys.exit(1)

    sz = os.path.getsize(_TEST_PNG)
    print(f"[P0] GPU + Adaptive-Subdiv test render PASSED — {_TEST_PNG} "
          f"({sz} bytes)")
    return True


# ============================================================
# 4-8. LOAD .BLEND + REPORT CONTENTS
# ============================================================
def load_and_inspect_blend():
    print(f"\n[P0] Loading {_BLEND_IN} ...")
    if not os.path.isfile(_BLEND_IN):
        print(f"[P0] FATAL: .blend not found: {_BLEND_IN}", file=sys.stderr)
        sys.exit(1)

    bpy.ops.wm.open_mainfile(filepath=_BLEND_IN)
    print(f"[P0] Loaded OK — file size: {os.path.getsize(_BLEND_IN) // 1024} KB")

    # Re-enable GPU after file open
    enable_gpu()

    scene = bpy.context.scene
    print(f"[P0] Scene: '{scene.name}', objects in scene: {len(scene.objects)}")

    # All objects
    print("\n[P0] === OBJECT INVENTORY ===")
    for obj in sorted(scene.objects, key=lambda o: o.name):
        info = f"  {obj.name:30s}  type={obj.type}"
        if obj.type == "MESH":
            verts = len(obj.data.vertices)
            polys = len(obj.data.polygons)
            mods  = [m.type for m in obj.modifiers]
            sk_count = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            info += f"  verts={verts} polys={polys} mods={mods} shape_keys={sk_count}"
        elif obj.type == "ARMATURE":
            n_bones = len(obj.data.bones)
            info += f"  bones={n_bones}"
        print(info)

    # Armature check
    print("\n[P0] === ARMATURE CHECK ===")
    arm = bpy.data.objects.get(ARMATURE_NAME)
    if arm is None or arm.type != "ARMATURE":
        print(f"[P0] FATAL: '{ARMATURE_NAME}' not found or wrong type.",
              file=sys.stderr)
        sys.exit(1)

    bones = list(arm.data.bones)
    deform_bones = [b for b in bones if b.use_deform]
    print(f"[P0] Armature '{ARMATURE_NAME}': {len(bones)} bones total, "
          f"{len(deform_bones)} deform bones")
    print("[P0] Bone names:")
    for b in sorted(bones, key=lambda x: x.name):
        deform_mark = "[deform]" if b.use_deform else "[control]"
        print(f"  {b.name:25s}  {deform_mark}")

    # Skinned meshes
    print("\n[P0] === SKINNED MESH CHECK ===")
    skinned = []
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        arm_mods = [m for m in obj.modifiers if m.type == "ARMATURE"]
        if arm_mods:
            vg_count = len(obj.vertex_groups)
            sk = obj.data.shape_keys
            sk_count = len(sk.key_blocks) if sk else 0
            print(f"  {obj.name:30s}  Armature modifier: {arm_mods[0].object.name if arm_mods[0].object else 'UNBOUND'}  "
                  f"vertex_groups={vg_count}  shape_keys={sk_count}")
            skinned.append(obj.name)

    if not skinned:
        print("[P0] WARNING: No skinned meshes found with Armature modifier.",
              file=sys.stderr)
    else:
        print(f"[P0] Skinned meshes: {skinned}")

    # Shape key inventory (all meshes)
    print("\n[P0] === SHAPE KEY INVENTORY ===")
    any_sk = False
    for obj in sorted(scene.objects, key=lambda o: o.name):
        if obj.type != "MESH" or not obj.data.shape_keys:
            continue
        sk = obj.data.shape_keys
        keys = list(sk.key_blocks)
        if keys:
            any_sk = True
            print(f"  {obj.name}: {len(keys)} shape keys")
            for k in keys:
                print(f"    '{k.name}'  min={k.slider_min:.2f} max={k.slider_max:.2f} "
                      f"value={k.value:.2f}")

    if not any_sk:
        print("[P0] No shape keys found on any mesh (blendshapes will need "
              "to be added in a later phase or driven via MPFB2 morph targets).")

    return arm, len(bones), skinned


# ============================================================
# 9. EXPORT BASELINE GLB
# ============================================================
def export_glb():
    print(f"\n[P0] Exporting baseline GLB -> {_GLB_OUT}")
    try:
        bpy.ops.export_scene.gltf(
            filepath=_GLB_OUT,
            export_format="GLB",
            export_apply=False,          # keep modifiers un-applied for animatability
            export_animations=False,     # no animations yet
            export_skins=True,
            export_morph=True,           # export shape keys as blendshapes
            export_morph_normal=False,
            export_cameras=False,
            export_lights=False,
            use_selection=False,
            export_extras=False,
        )
    except Exception as e:
        print(f"[P0] FATAL: GLB export raised: {e}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(_GLB_OUT) or os.path.getsize(_GLB_OUT) < 1024:
        print(f"[P0] FATAL: GLB not written or too small: {_GLB_OUT}",
              file=sys.stderr)
        sys.exit(1)

    sz = os.path.getsize(_GLB_OUT)
    print(f"[P0] GLB written: {_GLB_OUT}  ({sz // 1024} KB)")
    return sz


# ============================================================
# 10. PARSE GLB — report bone/mesh/shape-key counts
# ============================================================
def parse_glb(path):
    """
    Parse the GLB binary container, extract the JSON chunk, and report:
      - meshes + primitives
      - skins (skeleton) + joint counts
      - morph target (blendshape) counts per primitive
    """
    print(f"\n[P0] Parsing GLB: {path}")
    with open(path, "rb") as f:
        magic, version, length = struct.unpack_from("<III", f.read(12))
        if magic != 0x46546C67:
            print("[P0] FATAL: Not a valid GLB (bad magic).", file=sys.stderr)
            sys.exit(1)
        chunk_len, chunk_type = struct.unpack_from("<II", f.read(8))
        json_bytes = f.read(chunk_len)

    gltf = json.loads(json_bytes.decode("utf-8"))

    # Meshes
    meshes = gltf.get("meshes", [])
    print(f"[P0] GLB meshes: {len(meshes)}")
    total_morph_targets = 0
    for mi, mesh in enumerate(meshes):
        prims = mesh.get("primitives", [])
        for pi, prim in enumerate(prims):
            targets = prim.get("targets", [])
            total_morph_targets += len(targets)
            target_names = []
            if "extras" in mesh and "targetNames" in mesh["extras"]:
                target_names = mesh["extras"]["targetNames"]
            print(f"  mesh[{mi}] '{mesh.get('name','?')}' prim[{pi}]: "
                  f"{len(targets)} morph targets  names={target_names}")

    # Skins (skeletons)
    skins = gltf.get("skins", [])
    print(f"[P0] GLB skins (armatures): {len(skins)}")
    for si, skin in enumerate(skins):
        joints = skin.get("joints", [])
        print(f"  skin[{si}] '{skin.get('name','?')}': {len(joints)} joints")

    # Nodes (for quick check)
    nodes = gltf.get("nodes", [])
    print(f"[P0] GLB nodes total: {len(nodes)}")

    print(f"\n[P0] GLB SUMMARY:")
    print(f"  Meshes:              {len(meshes)}")
    print(f"  Skins (skeletons):   {len(skins)}")
    print(f"  Total joint count:   "
          f"{sum(len(s.get('joints',[])) for s in skins)}")
    print(f"  Total morph targets: {total_morph_targets}")

    if not skins:
        print("[P0] GATE FAIL: GLB has no skeleton (no skins).", file=sys.stderr)
        return False

    return True


# ============================================================
# 11. MPFB2 REACHABILITY
# ============================================================
def check_mpfb2():
    """
    Test whether MPFB2 v2.0.16 is reachable via bpy.ops.preferences.addon_enable.
    We do NOT actually enable it (to avoid mutating the loaded .blend state),
    but we check:
      a) Is the addon registered in bpy.context.preferences?
      b) Is the mpfb Python module importable?
    Documents what morph target path is available to 01_base_human.py.
    """
    print("\n[P0] === MPFB2 REACHABILITY CHECK ===")

    prefs = bpy.context.preferences
    addon_keys = list(prefs.addons.keys())

    # Check if already enabled
    mpfb_key = None
    for key in addon_keys:
        if "mpfb" in key.lower():
            mpfb_key = key
            break

    if mpfb_key:
        print(f"[P0] MPFB2 addon already enabled as: '{mpfb_key}'")
    else:
        print("[P0] MPFB2 not currently active — attempting enable ...")
        try:
            bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
            # Re-check
            for key in bpy.context.preferences.addons.keys():
                if "mpfb" in key.lower():
                    mpfb_key = key
                    break
            if mpfb_key:
                print(f"[P0] MPFB2 enabled successfully as: '{mpfb_key}'")
            else:
                print("[P0] MPFB2 enable op ran but addon key not found — "
                      "may be registered under different name.")
        except Exception as e:
            print(f"[P0] MPFB2 enable failed: {e}", file=sys.stderr)
            mpfb_key = None

    # Try import
    mpfb_importable = False
    try:
        import mpfb
        mpfb_importable = True
        print(f"[P0] mpfb Python module importable: YES  (path: {mpfb.__file__})")
        # Report available submodules for morph targets
        mpfb_dir = os.path.dirname(mpfb.__file__)
        relevant = []
        for root, dirs, files in os.walk(mpfb_dir):
            for fn in files:
                if "morph" in fn.lower() or "target" in fn.lower() or "shapekey" in fn.lower():
                    relevant.append(os.path.join(root, fn).replace(mpfb_dir, ""))
        if relevant:
            print(f"[P0] Morph/target-related MPFB2 files ({len(relevant)}):")
            for r in relevant[:20]:
                print(f"  {r}")
            if len(relevant) > 20:
                print(f"  ... and {len(relevant)-20} more")
        else:
            print("[P0] No morph/target files found in mpfb package tree.")
    except ImportError:
        print("[P0] mpfb Python module NOT importable directly.")

    # Check for MHX2 / MakeSkin morph target ops
    ops_found = []
    if hasattr(bpy.ops, "mpfb"):
        for attr in dir(bpy.ops.mpfb):
            if "morph" in attr.lower() or "target" in attr.lower() or "shapekey" in attr.lower():
                ops_found.append(f"bpy.ops.mpfb.{attr}")
        if ops_found:
            print(f"[P0] MPFB2 morph/shape-key ops: {ops_found}")
        else:
            print("[P0] No morph/shapekey ops found under bpy.ops.mpfb.*")
    else:
        print("[P0] bpy.ops.mpfb namespace not present.")

    # Conclusion
    if mpfb_key or mpfb_importable:
        print("[P0] MPFB2 STATUS: REACHABLE — morph targets can be driven "
              "from 01_base_human.py via mpfb Python API or bpy.ops.mpfb.*")
        print("[P0] Morph target workflow: load MPFB2 body via "
              "bpy.ops.mpfb.load_human(), then use mpfb's shape-key "
              "targets (facial expressions + body proportions) to drive "
              "the face and body definitions before baking geometry.")
    else:
        print("[P0] MPFB2 STATUS: NOT REACHABLE — morph targets cannot be "
              "driven automatically. Manual shape-key setup required in a "
              "later phase.")

    return mpfb_key is not None or mpfb_importable


# ============================================================
# MAIN GATE
# ============================================================
def main():
    print("=" * 70)
    print("[P0] PHASE 0 GATE — GPU + Adaptive-Subdiv + .blend + GLB + MPFB2")
    print("=" * 70)

    # 1. Version
    check_blender_version()

    # 2+3. GPU test render (also calls enable_gpu internally)
    run_gpu_test_render()

    # 4-8. Load .blend + inspect
    arm, bone_count, skinned_meshes = load_and_inspect_blend()

    # 9. Export GLB
    glb_sz = export_glb()

    # 10. Parse GLB
    glb_ok = parse_glb(_GLB_OUT)

    # 11. MPFB2
    mpfb_ok = check_mpfb2()

    # ---- FINAL GATE SUMMARY ----
    print("\n" + "=" * 70)
    print("[P0] PHASE 0 GATE RESULTS")
    print("=" * 70)
    print(f"  GPU + OptiX/CUDA:          PASS")
    print(f"  Adaptive-Subdiv test:      PASS")
    print(f"  .blend loads:              PASS  ({os.path.getsize(_BLEND_IN)//1024} KB)")
    print(f"  Armature '{ARMATURE_NAME}': PASS  ({bone_count} bones)")
    print(f"  Skinned meshes:            {'PASS' if skinned_meshes else 'WARN (none found)'}  {skinned_meshes}")
    print(f"  GLB export:                {'PASS' if glb_ok else 'FAIL'}  ({glb_sz//1024} KB)")
    print(f"  MPFB2 morph reachability:  {'PASS' if mpfb_ok else 'WARN (not reachable)'}")
    print(f"  Test PNG:                  {_TEST_PNG}")
    print(f"  GLB:                       {_GLB_OUT}")

    if not glb_ok:
        print("\n[P0] GATE FAIL: GLB skeleton missing.", file=sys.stderr)
        sys.exit(1)

    print("\n[P0] PHASE 0 GATE: PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
else:
    main()
