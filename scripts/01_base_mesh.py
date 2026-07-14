"""
01_base_mesh.py — Phase 1: Godwyn base body mesh.

Builds a procedural humanoid "Godwyn_Body" using primitive + Skin modifier
assembly:
  - A spine-based vertex skeleton (joined mesh) with the Skin modifier
    applied and a Subdivision Surface modifier on top.
  - 3.2m total height, 1.4x heroic-noble proportions (SPEC.txt 313).
  - Neutral A-ish stance (arms ~30° out), barefoot feet modeled (SPEC 311).
  - Object named "Godwyn_Body", placed in the "Godwyn" collection (INV-4).
  - Idempotent: deletes any prior "Godwyn_Body" before rebuilding (INV-6).
  - Clay preview rendered to renders/wip/01_base.png (GPU, INV-2).

INVARIANTS respected:
  INV-1  headless-only (no GUI ops)
  INV-2  GPU render asserted
  INV-3  proportions/barefoot per SPEC 313/311
  INV-4  object name + collection
  INV-5  no randomness (fully deterministic)
  INV-6  idempotent clear-then-build

Run:
  blender --background --python scripts/01_base_mesh.py
"""

import sys
import os
import math
import bpy
import bmesh
import mathutils

# ---------------------------------------------------------------------------
# PATH SETUP — allow importing lib_godwyn from the scripts/ directory
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

# ---------------------------------------------------------------------------
# OUTPUT PATHS
# ---------------------------------------------------------------------------
_REPO_ROOT   = os.path.dirname(_SCRIPT_DIR)
_WIP_DIR     = os.path.join(_REPO_ROOT, "renders", "wip")
_LOG_DIR     = os.path.join(_WIP_DIR, "logs")
_PREVIEW_OUT = os.path.join(_WIP_DIR, "01_base.png")

os.makedirs(_WIP_DIR, exist_ok=True)
os.makedirs(_LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# PROPORTION CONSTANTS  (all metres, from lib_godwyn)
# ---------------------------------------------------------------------------
H      = G.GODWYN_HEIGHT_M      # 3.2m total
HEAD_H = G.HEAD_H               # ~0.368m
TORSO_H= G.TORSO_H              # ~0.992m
ARM_L  = G.ARM_L                # ~1.088m  (upper+lower arm)
LEG_H  = G.LEG_H                # ~1.392m
SW     = G.SHOULDER_W           # ~0.80m   shoulder width

# Derived radii for Skin modifier (approximate cross-section half-widths)
R_HEAD   = HEAD_H  * 0.46   # ~0.169m
R_NECK   = HEAD_H  * 0.19   # ~0.070m
R_TORSO  = TORSO_H * 0.165  # ~0.164m
R_PELVIS = TORSO_H * 0.155  # ~0.154m
R_UPPER_ARM = ARM_L * 0.073 # ~0.079m
R_LOWER_ARM = ARM_L * 0.063 # ~0.069m
R_HAND   = ARM_L   * 0.055  # ~0.060m
R_UPPER_LEG = LEG_H * 0.085 # ~0.118m
R_LOWER_LEG = LEG_H * 0.068 # ~0.095m
R_ANKLE  = LEG_H   * 0.045  # ~0.063m
R_FOOT   = LEG_H   * 0.042  # ~0.058m (foot pad - barefoot, SPEC 311)

# Key Z-heights along the body (from ground = 0)
Z_GROUND     = 0.0
Z_ANKLE      = LEG_H * 0.10      # ~0.139m
Z_KNEE       = LEG_H * 0.42      # ~0.585m
Z_HIP        = LEG_H             # ~1.392m
Z_NAVEL      = Z_HIP + TORSO_H * 0.22   # ~1.610m
Z_CHEST      = Z_HIP + TORSO_H * 0.55   # ~1.937m
Z_SHOULDER   = Z_HIP + TORSO_H * 0.90   # ~2.285m
Z_NECK_BASE  = Z_HIP + TORSO_H          # ~2.384m
Z_NECK_TOP   = Z_NECK_BASE + HEAD_H * 0.35  # ~2.513m
Z_HEAD_CTR   = Z_NECK_TOP + HEAD_H * 0.45   # ~2.679m
Z_HEAD_TOP   = H  # 3.2m

# Arm placement (shoulder to wrist, angled ~30° out = A-pose)
ARM_HALF_SPAN   = SW * 0.5 + ARM_L * 0.42   # horizontal reach from centre
ARM_ANGLE_DEG   = 30.0   # outward angle from vertical
ARM_UPPER_L = ARM_L * 0.46  # humerus
ARM_LOWER_L = ARM_L * 0.38  # forearm
ARM_HAND_L  = ARM_L * 0.16  # hand

# ---------------------------------------------------------------------------
# SCENE RESET (INV-6: only wipe if needed; reset_scene wipes everything)
# ---------------------------------------------------------------------------

def clear_godwyn_body():
    """Remove only 'Godwyn_Body' if it exists (leaves other objects intact)."""
    names_to_clear = [n for n in bpy.data.objects.keys()
                      if n.startswith("Godwyn_Body")]
    for name in names_to_clear:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    # Also purge orphan meshes
    for mesh in list(bpy.data.meshes):
        if mesh.name.startswith("Godwyn_Body") and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def full_scene_reset():
    """Full reset for a standalone run — wipe everything and start fresh."""
    G.reset_scene()


# ---------------------------------------------------------------------------
# VERTEX SKELETON BUILDER
# ---------------------------------------------------------------------------

def _add_vertex_at(bm, co):
    return bm.verts.new(co)


def _join_verts(bm, v0, v1):
    """Add an edge between two BMesh verts."""
    try:
        bm.edges.new((v0, v1))
    except ValueError:
        pass  # edge already exists


def build_body_skeleton():
    """
    Build a single-mesh vertex skeleton (edges = limb segments).
    The Skin modifier will inflate each vertex/edge into a tube,
    with per-vertex radius set below.
    Returns: (bmesh, radius_dict) where radius_dict maps vert index -> (rx, ry).
    """
    bm = bmesh.new()

    # ---- SPINE column ----
    v_foot_l    = _add_vertex_at(bm, (-SW * 0.18,  0.0, Z_GROUND))
    v_foot_r    = _add_vertex_at(bm, ( SW * 0.18,  0.0, Z_GROUND))
    v_heel_l    = _add_vertex_at(bm, (-SW * 0.18, -0.06, Z_GROUND))
    v_heel_r    = _add_vertex_at(bm, ( SW * 0.18, -0.06, Z_GROUND))
    v_toe_l     = _add_vertex_at(bm, (-SW * 0.18,  0.10, Z_GROUND))
    v_toe_r     = _add_vertex_at(bm, ( SW * 0.18,  0.10, Z_GROUND))
    v_ankle_l   = _add_vertex_at(bm, (-SW * 0.18,  0.0, Z_ANKLE))
    v_ankle_r   = _add_vertex_at(bm, ( SW * 0.18,  0.0, Z_ANKLE))
    v_knee_l    = _add_vertex_at(bm, (-SW * 0.14,  0.0, Z_KNEE))
    v_knee_r    = _add_vertex_at(bm, ( SW * 0.14,  0.0, Z_KNEE))
    v_hip_l     = _add_vertex_at(bm, (-SW * 0.22,  0.0, Z_HIP))
    v_hip_r     = _add_vertex_at(bm, ( SW * 0.22,  0.0, Z_HIP))
    v_pelvis    = _add_vertex_at(bm, (  0.0,       0.0, Z_HIP   * 0.97))
    v_navel     = _add_vertex_at(bm, (  0.0,       0.0, Z_NAVEL))
    v_chest     = _add_vertex_at(bm, (  0.0,       0.0, Z_CHEST))
    v_sh_l      = _add_vertex_at(bm, (-SW * 0.50,  0.0, Z_SHOULDER))
    v_sh_r      = _add_vertex_at(bm, ( SW * 0.50,  0.0, Z_SHOULDER))
    v_neck_base = _add_vertex_at(bm, (  0.0,       0.0, Z_NECK_BASE))
    v_neck_top  = _add_vertex_at(bm, (  0.0,       0.0, Z_NECK_TOP))
    v_head_ctr  = _add_vertex_at(bm, (  0.0,       0.0, Z_HEAD_CTR))
    v_head_top  = _add_vertex_at(bm, (  0.0,       0.0, Z_HEAD_TOP))

    # Arm (A-pose: 30° from vertical, fanned outward slightly)
    arm_angle = math.radians(ARM_ANGLE_DEG)
    dx_upper  = math.sin(arm_angle) * ARM_UPPER_L
    dz_upper  = -math.cos(arm_angle) * ARM_UPPER_L
    dx_lower  = math.sin(arm_angle * 0.7) * ARM_LOWER_L
    dz_lower  = -math.cos(arm_angle * 0.7) * ARM_LOWER_L

    # Left arm
    elbow_l_x = -SW * 0.50 - dx_upper
    elbow_l_z = Z_SHOULDER + dz_upper
    wrist_l_x = elbow_l_x - dx_lower
    wrist_l_z = elbow_l_z + dz_lower
    hand_l_x  = wrist_l_x - ARM_HAND_L * math.sin(arm_angle * 0.5)
    hand_l_z  = wrist_l_z - ARM_HAND_L * math.cos(arm_angle * 0.5)

    v_elbow_l = _add_vertex_at(bm, (elbow_l_x, 0.0, elbow_l_z))
    v_wrist_l = _add_vertex_at(bm, (wrist_l_x, 0.0, wrist_l_z))
    v_hand_l  = _add_vertex_at(bm, (hand_l_x,  0.0, hand_l_z))

    # Right arm (mirror X)
    v_elbow_r = _add_vertex_at(bm, (-elbow_l_x, 0.0, elbow_l_z))
    v_wrist_r = _add_vertex_at(bm, (-wrist_l_x, 0.0, wrist_l_z))
    v_hand_r  = _add_vertex_at(bm, (-hand_l_x,  0.0, hand_l_z))

    # ---- EDGES (limb connectivity) ----
    # Spine + torso
    _join_verts(bm, v_pelvis,    v_navel)
    _join_verts(bm, v_navel,     v_chest)
    _join_verts(bm, v_chest,     v_sh_l)
    _join_verts(bm, v_chest,     v_sh_r)
    _join_verts(bm, v_chest,     v_neck_base)
    _join_verts(bm, v_neck_base, v_neck_top)
    _join_verts(bm, v_neck_top,  v_head_ctr)
    _join_verts(bm, v_head_ctr,  v_head_top)
    # Hip crossbar
    _join_verts(bm, v_hip_l,  v_pelvis)
    _join_verts(bm, v_hip_r,  v_pelvis)
    # Legs
    _join_verts(bm, v_hip_l,   v_knee_l)
    _join_verts(bm, v_knee_l,  v_ankle_l)
    _join_verts(bm, v_ankle_l, v_foot_l)
    _join_verts(bm, v_hip_r,   v_knee_r)
    _join_verts(bm, v_knee_r,  v_ankle_r)
    _join_verts(bm, v_ankle_r, v_foot_r)
    # Feet (barefoot pad + heel + toe — SPEC 311)
    _join_verts(bm, v_foot_l, v_heel_l)
    _join_verts(bm, v_foot_l, v_toe_l)
    _join_verts(bm, v_foot_r, v_heel_r)
    _join_verts(bm, v_foot_r, v_toe_r)
    # Arms
    _join_verts(bm, v_sh_l, v_elbow_l)
    _join_verts(bm, v_elbow_l, v_wrist_l)
    _join_verts(bm, v_wrist_l, v_hand_l)
    _join_verts(bm, v_sh_r, v_elbow_r)
    _join_verts(bm, v_elbow_r, v_wrist_r)
    _join_verts(bm, v_wrist_r, v_hand_r)

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # ---- Per-vertex radius lookup (index -> (rx, ry)) ----
    radii = {
        v_foot_l.index:    (R_FOOT,      R_FOOT * 0.5),
        v_foot_r.index:    (R_FOOT,      R_FOOT * 0.5),
        v_heel_l.index:    (R_FOOT,      R_FOOT * 0.65),
        v_heel_r.index:    (R_FOOT,      R_FOOT * 0.65),
        v_toe_l.index:     (R_FOOT * 0.75, R_FOOT * 0.35),
        v_toe_r.index:     (R_FOOT * 0.75, R_FOOT * 0.35),
        v_ankle_l.index:   (R_ANKLE,     R_ANKLE),
        v_ankle_r.index:   (R_ANKLE,     R_ANKLE),
        v_knee_l.index:    (R_UPPER_LEG * 0.7, R_UPPER_LEG * 0.7),
        v_knee_r.index:    (R_UPPER_LEG * 0.7, R_UPPER_LEG * 0.7),
        v_hip_l.index:     (R_UPPER_LEG, R_UPPER_LEG),
        v_hip_r.index:     (R_UPPER_LEG, R_UPPER_LEG),
        v_pelvis.index:    (R_PELVIS,    R_PELVIS * 0.8),
        v_navel.index:     (R_TORSO * 0.82, R_TORSO * 0.72),
        v_chest.index:     (R_TORSO,     R_TORSO * 0.80),
        v_sh_l.index:      (R_UPPER_ARM, R_UPPER_ARM),
        v_sh_r.index:      (R_UPPER_ARM, R_UPPER_ARM),
        v_neck_base.index: (R_NECK * 1.2, R_NECK * 1.2),
        v_neck_top.index:  (R_NECK,      R_NECK),
        v_head_ctr.index:  (R_HEAD,      R_HEAD),
        v_head_top.index:  (R_HEAD * 0.55, R_HEAD * 0.55),
        v_elbow_l.index:   (R_UPPER_ARM * 0.75, R_UPPER_ARM * 0.75),
        v_wrist_l.index:   (R_LOWER_ARM * 0.70, R_LOWER_ARM * 0.70),
        v_hand_l.index:    (R_HAND,      R_HAND * 0.45),
        v_elbow_r.index:   (R_UPPER_ARM * 0.75, R_UPPER_ARM * 0.75),
        v_wrist_r.index:   (R_LOWER_ARM * 0.70, R_LOWER_ARM * 0.70),
        v_hand_r.index:    (R_HAND,      R_HAND * 0.45),
    }

    return bm, radii


# ---------------------------------------------------------------------------
# MAIN BUILD
# ---------------------------------------------------------------------------

def build_base_mesh():
    """
    Build the Godwyn_Body object: vertex skeleton -> Skin modifier ->
    Subdivision Surface.  Placed in the 'Godwyn' collection.
    """
    print("[01_base_mesh] Building skeleton bmesh...")
    bm, radii = build_body_skeleton()

    # Create a new mesh and object from the bmesh
    mesh = bpy.data.meshes.new("Godwyn_Body")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("Godwyn_Body", mesh)

    # Link to Godwyn collection (INV-4)
    col = G.get_or_create_collection("Godwyn")
    col.objects.link(obj)

    # Make active for modifier ops
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # ---- SKIN MODIFIER ----
    skin_mod = obj.modifiers.new("Skin", "SKIN")
    skin_mod.use_smooth_shade = True

    # Set per-vertex skin radii (accessed via mesh.skin_vertices)
    # We must access through the object's mesh skin layer
    skin_verts = mesh.skin_vertices[0].data  # type: ignore
    for vi, (rx, ry) in radii.items():
        if vi < len(skin_verts):
            skin_verts[vi].radius = (rx, ry)

    # Mark the head top vert as root (helps Skin modifier orient correctly)
    # Find the topmost vert
    top_vert_i = max(radii.keys(),
                     key=lambda i: mesh.vertices[i].co.z)
    skin_verts[top_vert_i].use_root = True

    # ---- SUBDIVISION SURFACE ----
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = 2          # viewport
    subsurf.render_levels = 2   # render (keep modest for 8GB VRAM)
    subsurf.subdivision_type = "CATMULL_CLARK"

    print(f"[01_base_mesh] Godwyn_Body created. "
          f"Skin+Subsurf applied.  Height: {G.GODWYN_HEIGHT_M}m")
    return obj


# ---------------------------------------------------------------------------
# CLAY PREVIEW CAMERA + LIGHT
# ---------------------------------------------------------------------------

def setup_clay_preview(scene):
    """
    Add a simple 3/4-front camera and a clay light for the WIP preview.
    Not the final character rig (that comes in P4).
    """
    # Camera: 3/4 front view, framing the full 3.2m body with headroom
    cam_data = bpy.data.cameras.new("Clay_Cam")
    cam_data.lens = 85            # short tele, de-distorts a tall figure
    cam_data.clip_end = 100.0
    cam_obj = bpy.data.objects.new("Clay_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    # Position: 7.2m back, 3.2m high (looks at mid-body), 30° angle
    cam_obj.location = (2.8, 7.5, 2.0)
    # Point camera at approx mid-body of the 3.2m figure
    target = mathutils.Vector((0.0, 0.0, 1.6))
    direction = target - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    scene.camera = cam_obj

    # Clay sun light — warm directional
    sun_data = bpy.data.lights.new("Clay_Sun", "SUN")
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.95, 0.85)
    sun_obj = bpy.data.objects.new("Clay_Sun", sun_data)
    bpy.context.scene.collection.objects.link(sun_obj)
    sun_obj.location = (4.0, 3.0, 8.0)
    sun_obj.rotation_euler = (math.radians(-40), math.radians(20), math.radians(30))

    # Soft fill
    fill_data = bpy.data.lights.new("Clay_Fill", "AREA")
    fill_data.energy = 60.0
    fill_data.color = (0.7, 0.85, 1.0)
    fill_data.size = 3.0
    fill_obj = bpy.data.objects.new("Clay_Fill", fill_data)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.location = (-3.0, 4.0, 3.0)


# ---------------------------------------------------------------------------
# ASSERTION (validation gate)
# ---------------------------------------------------------------------------

def assert_body_exists():
    """INV-4 / Section 3 Phase 1 validation: object must exist in collection."""
    obj = bpy.data.objects.get("Godwyn_Body")
    if obj is None:
        print("[01_base_mesh] FATAL: 'Godwyn_Body' object not found after build!",
              file=sys.stderr)
        sys.exit(1)

    col = bpy.data.collections.get("Godwyn")
    if col is None:
        print("[01_base_mesh] FATAL: 'Godwyn' collection not found!", file=sys.stderr)
        sys.exit(1)

    if obj.name not in col.objects:
        print("[01_base_mesh] FATAL: 'Godwyn_Body' not in 'Godwyn' collection!",
              file=sys.stderr)
        sys.exit(1)

    print(f"[01_base_mesh] ASSERT OK: 'Godwyn_Body' exists in 'Godwyn' collection.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[01_base_mesh] Phase 1 — Base Mesh Build")
    print("=" * 60)

    # Enable GPU (INV-2) — asserts GPU is available; fails loud if not
    active_gpu = G.enable_gpu()
    print(f"[01_base_mesh] GPU active: {active_gpu}")

    # Full scene reset for standalone run
    print("[01_base_mesh] Resetting scene...")
    full_scene_reset()

    # Idempotent clear of any prior Godwyn_Body (INV-6)
    clear_godwyn_body()

    # Build the body
    body_obj = build_base_mesh()

    # Build void background for context
    G.build_void_bg()

    # Clay preview setup
    scene = bpy.context.scene
    setup_clay_preview(scene)

    # Add a basic clay material for the preview
    clay_mat = bpy.data.materials.new("Mat_Clay")
    clay_mat.use_nodes = True
    clay_nt = clay_mat.node_tree
    clay_nt.nodes.clear()
    out_node = clay_nt.nodes.new("ShaderNodeOutputMaterial")
    pbsdf = clay_nt.nodes.new("ShaderNodeBsdfPrincipled")
    pbsdf.inputs["Base Color"].default_value = (0.75, 0.65, 0.55, 1.0)
    pbsdf.inputs["Roughness"].default_value = 0.85
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.2
    except KeyError:
        try:
            pbsdf.inputs["Specular"].default_value = 0.2
        except KeyError:
            pass
    clay_nt.links.new(pbsdf.outputs["BSDF"], out_node.inputs["Surface"])
    body_obj.data.materials.append(clay_mat)

    # Configure Cycles (portrait 2K, modest samples for WIP)
    G.configure_cycles(scene,
                       samples=96,
                       resolution_x=1440,
                       resolution_y=2560,
                       use_denoiser=True,
                       film_transparent=False)

    # Assertion before render
    assert_body_exists()

    # GPU render to WIP
    print(f"[01_base_mesh] Rendering clay preview -> {_PREVIEW_OUT}")
    G.render_to_path(_PREVIEW_OUT, scene)

    # Final assertion: output PNG must exist and be non-empty
    if not os.path.isfile(_PREVIEW_OUT):
        print(f"[01_base_mesh] FATAL: preview PNG not written: {_PREVIEW_OUT}",
              file=sys.stderr)
        sys.exit(1)
    size = os.path.getsize(_PREVIEW_OUT)
    if size < 1024:
        print(f"[01_base_mesh] FATAL: preview PNG suspiciously small ({size}B): "
              f"{_PREVIEW_OUT}", file=sys.stderr)
        sys.exit(1)

    print(f"[01_base_mesh] Preview OK: {_PREVIEW_OUT} ({size // 1024} KB)")
    print("[01_base_mesh] Phase 1 complete. Godwyn_Body built and previewed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    # When executed by Blender's python: __name__ is not '__main__'
    main()
