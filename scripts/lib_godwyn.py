"""
lib_godwyn.py — Shared helpers for the Godwyn headless Blender pipeline.

Provides:
  - GPU enable + assert (OptiX preferred, CUDA fallback)
  - Scene reset (clear all objects, lights, cams, materials)
  - Void background builder (near-black + faint vertical golden crack plane)
  - Render-to-path (Cycles GPU, 2K portrait or 1080p action)
  - Proportion constants (3.2m height, 1.4x human proportions)
  - Material factory stubs (filled in by 03_materials.py and above)

INV-1: headless-only (no GUI ops).
INV-2: GPU-real — GPU is asserted in enable_gpu(); call it at the top of
        every render script.
INV-5: reproducibility — no RNG here; callers must seed their own.
"""

import sys
import bpy
import mathutils

# ---------------------------------------------------------------------------
# PROPORTION CONSTANTS (SPEC.txt 313: 3.2m, 1.4x human)
# ---------------------------------------------------------------------------
GODWYN_HEIGHT_M   = 3.2          # total height in Blender units (= metres)
HUMAN_HEIGHT_M    = 2.286        # reference human (7'6" heroic figure)
PROPORTION_SCALE  = 1.4          # heroic / demigod scale factor
# Derived proportions (all in metres, based on 3.2m total)
HEAD_H   = GODWYN_HEIGHT_M * 0.115   # ~0.368m  (slightly larger than 1/8 body)
TORSO_H  = GODWYN_HEIGHT_M * 0.310   # ~0.992m
ARM_L    = GODWYN_HEIGHT_M * 0.340   # ~1.088m  (longer than normal)
LEG_H    = GODWYN_HEIGHT_M * 0.435   # ~1.392m
SHOULDER_W = GODWYN_HEIGHT_M * 0.250  # ~0.80m  (heroic shoulder width)

# ---------------------------------------------------------------------------
# SPEC MATERIAL COLORS (linear RGB, SPEC.txt 332-341 + plan Section 4)
# ---------------------------------------------------------------------------
COL_SKIN_BASE    = (0.95, 0.90, 0.82, 1.0)
COL_SKIN_EMIT    = (1.0,  0.88, 0.45, 1.0)
SKIN_EMIT_STR    = 2.5

COL_GOLD         = (0.82, 0.65, 0.15, 1.0)
COL_ROBE         = (0.08, 0.12, 0.35, 1.0)
COL_BLADE        = (0.55, 0.62, 0.75, 1.0)   # steel + subtle blue tint
COL_BLADE_EMIT   = (0.35, 0.50, 0.90, 1.0)   # faint blue emit << skin
BLADE_EMIT_STR   = 0.3

COL_HAIR         = (0.70, 0.55, 0.24, 1.0)   # golden-blonde, lighter/less
                                             # saturated than the armor gold

COL_KEY_LIGHT    = (1.0,  0.92, 0.6,  1.0)   # SPEC 339 / INV-7
COL_VOID_CRACK   = (1.0,  0.85, 0.4,  1.0)   # faint golden crack
COL_WORLD        = (0.008, 0.007, 0.005, 1.0) # near-black void

# ---------------------------------------------------------------------------
# BUILD-SCRIPT MODULE LOADER (INV-5 — reuse earlier phases' builders without
# triggering their entry points)
# ---------------------------------------------------------------------------

def load_build_module(script_filename: str):
    """
    Load a sibling build script (e.g. "01_base_mesh.py") as a module WITHOUT
    executing its top-level `if` blocks (the numbered scripts call main()
    unconditionally from their entry-point guard, which would trigger a full
    build+render on plain import).

    Strategy: parse with ast, drop every top-level ast.If node (the sys.path
    guard and the entry point — both safe to drop when loaded this way),
    compile, exec into a fresh module namespace. Deterministic; the committed
    script stays the single source of truth for its geometry (INV-5).
    """
    import ast
    import os
    import types

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        script_filename)
    with open(path, "r") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=path)
    tree.body = [node for node in tree.body if not isinstance(node, ast.If)]
    mod = types.ModuleType("_godwyn_" + script_filename.rsplit(".", 1)[0])
    mod.__file__ = path
    code = compile(tree, path, "exec")
    exec(code, mod.__dict__)
    return mod


# ---------------------------------------------------------------------------
# GPU ENABLE + ASSERT (INV-2)
# ---------------------------------------------------------------------------

def enable_gpu(prefer_optix: bool = True) -> str:
    """
    Enable all GPU devices in Cycles preferences.
    Tries OptiX first; falls back to CUDA.
    Asserts that at least one GPU is enabled — raises SystemExit on failure
    (fail loud per INV-2; never silently render on CPU).

    Returns the active compute_device_type string ("OPTIX" or "CUDA").
    """
    prefs = bpy.context.preferences
    cprefs = prefs.addons["cycles"].preferences

    # Try OptiX first, then CUDA
    device_types = ["OPTIX", "CUDA"] if prefer_optix else ["CUDA", "OPTIX"]
    active_type = None

    for dtype in device_types:
        try:
            cprefs.compute_device_type = dtype
            cprefs.get_devices()
            devices = cprefs.devices
            # Enable every device
            gpu_count = 0
            for dev in devices:
                if dev.type in ("OPTIX", "CUDA"):
                    dev.use = True
                    gpu_count += 1
                else:
                    dev.use = False  # disable CPU so GPU renders GPU-only
            if gpu_count > 0:
                active_type = dtype
                break
        except Exception as e:
            print(f"[lib_godwyn] {dtype} init failed: {e}", file=sys.stderr)
            continue

    if active_type is None:
        print("[lib_godwyn] FATAL: No GPU devices found under OptiX or CUDA.",
              file=sys.stderr)
        print("[lib_godwyn] Device list:", file=sys.stderr)
        for dev in cprefs.devices:
            print(f"  {dev.name} type={dev.type} use={dev.use}", file=sys.stderr)
        sys.exit(1)

    # Set scene to GPU
    bpy.context.scene.cycles.device = "GPU"

    # Print device table (validation evidence for INV-2)
    print(f"\n[lib_godwyn] Cycles compute_device_type = {active_type}")
    print("[lib_godwyn] Enabled devices:")
    gpu_enabled = []
    for dev in cprefs.devices:
        status = "ENABLED" if dev.use else "disabled"
        print(f"  [{status}] {dev.name}  (type={dev.type})")
        if dev.use and dev.type in ("OPTIX", "CUDA"):
            gpu_enabled.append(dev.name)

    if not gpu_enabled:
        print("[lib_godwyn] FATAL: enable_gpu() ran but no GPU device is ENABLED.",
              file=sys.stderr)
        sys.exit(1)

    if len(gpu_enabled) < 2:
        print(f"[lib_godwyn] WARNING: only {len(gpu_enabled)} GPU(s) enabled "
              f"(expected 2x RTX 3060 Ti).")
    else:
        print(f"[lib_godwyn] {len(gpu_enabled)} GPU(s) enabled — nominal.")

    print(f"[lib_godwyn] Using {active_type}\n")
    return active_type


# ---------------------------------------------------------------------------
# SCENE RESET
# ---------------------------------------------------------------------------

def reset_scene():
    """
    Delete ALL objects, meshes, materials, lights, cameras, collections
    (except the master Scene Collection) and reset world to black.
    Call at the top of every build script for idempotency (INV-6).
    """
    # Deselect all first
    bpy.ops.object.select_all(action="DESELECT")

    # Delete all objects
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # Purge orphan data blocks
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)
    for block in list(bpy.data.materials):
        bpy.data.materials.remove(block)
    for block in list(bpy.data.lights):
        bpy.data.lights.remove(block)
    for block in list(bpy.data.cameras):
        bpy.data.cameras.remove(block)
    for block in list(bpy.data.curves):
        bpy.data.curves.remove(block)
    for block in list(bpy.data.armatures):
        bpy.data.armatures.remove(block)

    # Remove all non-default collections
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)

    # Reset world to near-black void
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()
    bg_node = wnt.nodes.new("ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = COL_WORLD
    bg_node.inputs["Strength"].default_value = 1.0
    out_node = wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])


# ---------------------------------------------------------------------------
# VOID BACKGROUND BUILDER (INV-7 / SPEC 337-341)
# ---------------------------------------------------------------------------

def build_void_bg(scene=None):
    """
    Build the void world: near-black + a faint vertical golden light crack
    plane positioned ~8m behind Godwyn (z=0 center, x=0, y=-6m relative
    to camera lookAt Godwyn).  Returns the crack plane object.
    """
    if scene is None:
        scene = bpy.context.scene

    # World shader: near-black
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("VoidWorld")
        scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()
    bg = wnt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = COL_WORLD
    bg.inputs["Strength"].default_value = 1.0
    out = wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # Faint vertical golden crack: a thin emissive plane behind Godwyn
    # Dimensions: 0.12m wide, 6.0m tall, placed at y=-8m (behind character)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -8.0, GODWYN_HEIGHT_M * 0.5))
    crack = bpy.context.active_object
    crack.name = "Godwyn_VoidCrack"
    crack.scale = (0.06, 0.001, GODWYN_HEIGHT_M * 0.93)
    bpy.ops.object.transform_apply(scale=True)

    # Material: emissive golden crack
    mat = bpy.data.materials.new("Mat_VoidCrack")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = COL_VOID_CRACK
    emit.inputs["Strength"].default_value = 4.0
    out_m = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs["Emission"], out_m.inputs["Surface"])
    crack.data.materials.append(mat)

    return crack


# ---------------------------------------------------------------------------
# COLLECTION HELPER
# ---------------------------------------------------------------------------

def get_or_create_collection(name: str, parent=None):
    """
    Return existing collection by name, or create it and link to parent
    (defaults to scene master collection).
    """
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    if parent is None:
        parent = bpy.context.scene.collection
    parent.children.link(col)
    return col


def move_to_collection(obj, col):
    """Move obj to col, removing it from all other collections."""
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


# ---------------------------------------------------------------------------
# CYCLES RENDER CONFIG
# ---------------------------------------------------------------------------

def configure_cycles(scene=None, samples: int = 128, resolution_x: int = 2048,
                     resolution_y: int = 2560, use_denoiser: bool = True,
                     film_transparent: bool = False):
    """
    Apply standard Cycles GPU render settings per the build plan:
      - Engine: CYCLES, device: GPU
      - Samples: 128-256 (caller sets)
      - Resolution: 2K portrait default (2048x2560)
      - OptiX denoiser ON (falls back to OIDN if unavailable)
      - Film transparent: OFF (keep the void black bg)
      - Color management: Filmic or AgX
    """
    if scene is None:
        scene = bpy.context.scene

    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.01

    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = film_transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"

    # Denoiser
    if use_denoiser:
        scene.cycles.use_denoising = True
        # Prefer OptiX denoiser; fall back to OIDN
        try:
            scene.cycles.denoiser = "OPTIX"
        except Exception:
            try:
                scene.cycles.denoiser = "OPENIMAGEDENOISE"
            except Exception:
                pass  # older builds: attribute not present, denoiser still active

    # Color management: try AgX first (Blender 4.0+), fall back to Filmic
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


# ---------------------------------------------------------------------------
# RENDER TO PATH
# ---------------------------------------------------------------------------

def render_to_path(filepath: str, scene=None):
    """
    Render the current scene (active camera) to filepath (absolute path).
    Asserts at least one GPU device is enabled before rendering (INV-2).
    """
    if scene is None:
        scene = bpy.context.scene

    # Safety-assert GPU is still set
    if scene.cycles.device != "GPU":
        print("[lib_godwyn] FATAL: render_to_path called but cycles.device != GPU",
              file=sys.stderr)
        sys.exit(1)

    scene.render.filepath = filepath
    print(f"[lib_godwyn] Rendering -> {filepath}  "
          f"({scene.render.resolution_x}x{scene.render.resolution_y}, "
          f"{scene.cycles.samples} samples)")
    bpy.ops.render.render(write_still=True)
    print(f"[lib_godwyn] Render complete: {filepath}")


# ---------------------------------------------------------------------------
# MATERIAL FACTORY — basic Principled BSDF helpers
# ---------------------------------------------------------------------------

def make_emission_material(name: str, base_color, emit_color, emit_strength: float):
    """
    Create (or reuse) a material with Principled BSDF + emission mix.
    Used for Godwyn's luminous skin.
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    add = nt.nodes.new("ShaderNodeAddShader")

    pbsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pbsdf.inputs["Base Color"].default_value = base_color
    # Subsurface (Blender 4+ uses 'Subsurface Weight' not 'Subsurface')
    try:
        pbsdf.inputs["Subsurface Weight"].default_value = 0.15
        pbsdf.inputs["Subsurface Radius"].default_value = (0.08, 0.04, 0.02)
        pbsdf.inputs["Subsurface Color"].default_value = (1.0, 0.85, 0.65, 1.0)
    except KeyError:
        try:
            pbsdf.inputs["Subsurface"].default_value = 0.15
        except KeyError:
            pass

    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = emit_color
    emit.inputs["Strength"].default_value = emit_strength

    nt.links.new(pbsdf.outputs["BSDF"], add.inputs[0])
    nt.links.new(emit.outputs["Emission"], add.inputs[1])
    nt.links.new(add.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_metallic_material(name: str, base_color, roughness: float = 0.25):
    """
    Create (or reuse) a fully-metallic PBR material (gold armor, hilt, etc).
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pbsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pbsdf.inputs["Base Color"].default_value = base_color
    pbsdf.inputs["Metallic"].default_value = 1.0
    pbsdf.inputs["Roughness"].default_value = roughness
    # Slight anisotropy for metallic sheen
    try:
        pbsdf.inputs["Anisotropic"].default_value = 0.2
    except KeyError:
        pass
    nt.links.new(pbsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_diffuse_material(name: str, base_color, roughness: float = 0.7):
    """
    Create (or reuse) a simple diffuse/cloth material (robe, etc).
    """
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pbsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pbsdf.inputs["Base Color"].default_value = base_color
    pbsdf.inputs["Roughness"].default_value = roughness
    pbsdf.inputs["Metallic"].default_value = 0.0
    # Slight sheen for fabric read
    try:
        pbsdf.inputs["Sheen Weight"].default_value = 0.15
    except KeyError:
        try:
            pbsdf.inputs["Sheen"].default_value = 0.15
        except KeyError:
            pass
    nt.links.new(pbsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat
