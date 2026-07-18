"""
PHASE 4 — FINAL RENDER + GLB EXPORT

  blender --background models/godwyn_mocap.blend \
          --python scripts/phase4_final_render_export.py

Outputs:
  renders/game/mocap_combo.mp4   — EEVEE clip, ffmpeg -framerate 30
  models/godwyn_mocap_combo.glb  — animated glTF (+Y up, baked textures)

GLB includes:
  - Armature (base rig + cape chain bones)
  - char1, CapeGrid, RobeGrid skinned meshes
  - Godwyn_Sword
  - GodwynGameMat with baked textures
  - Godwyn_DoubleCombo action
"""
import bpy
import os
import subprocess
from mathutils import Vector

BLEND_DIR = os.path.dirname(bpy.data.filepath)
ROOT = os.path.dirname(BLEND_DIR)
FRAMES_DIR = "/tmp/mocap_combo_frames"
MP4_OUT = os.path.join(ROOT, "renders", "game", "mocap_combo.mp4")
GLB_OUT = os.path.join(ROOT, "models", "godwyn_mocap_combo.glb")

os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MP4_OUT), exist_ok=True)

scene = bpy.context.scene
print(f"Scene fps={scene.render.fps}, frames {scene.frame_start}..{scene.frame_end}")
arm = next(o for o in scene.objects if o.type == "ARMATURE")
print(f"Armature: {arm.name}, action: {arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else 'NONE'}")

# Verify cloth caches baked
for g in ("CapeGrid", "RobeGrid"):
    if g in bpy.data.objects:
        obj = bpy.data.objects[g]
        for mod in obj.modifiers:
            if mod.type == "CLOTH":
                pc = mod.point_cache
                print(f"{g} cloth cache: baked={pc.is_baked} ({pc.frame_start}..{pc.frame_end})")
                assert pc.is_baked, f"{g} cloth cache not baked!"

frames = list(range(scene.frame_start, scene.frame_end + 1))
s = arm.scale.x

# ── Compute per-frame hips + radius ─────────────────────────────
BONES = ("Hips", "Head", "LeftFoot", "RightFoot", "LeftHand",
         "RightHand", "LeftToeBase", "RightToeBase")
hips = {}
rad = {}
for f in frames:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    hp = (ae.pose.bones["Hips"].head * s).copy()
    hips[f] = hp
    r = 0.0
    for bn in BONES:
        pb = ae.pose.bones.get(bn)
        if pb:
            r = max(r, ((pb.head * s) - hp).length)
    rad[f] = r

pc_center = sum((hips[f] for f in frames), Vector()) / len(frames)
rmax = max(rad.values())
print(f"Character center: {pc_center}, max radius: {rmax:.3f}m")


def smooth(d, passes):
    K = (1.0, 4.0, 6.0, 4.0, 1.0)
    sm = dict(d)
    for _ in range(passes):
        nx = {}
        for f in frames:
            acc = sm[frames[0]] * 0.0
            wacc = 0.0
            for k, w in zip(range(-2, 3), K):
                fk = min(max(f + k, frames[0]), frames[-1])
                acc = acc + w * sm[fk]
                wacc += w
            nx[f] = acc / wacc
        sm = nx
    return sm


sm_hips = smooth(hips, 12)
sm_rad = smooth(rad, 20)

# ── Remove any old camera/lights ─────────────────────────────────
for name in ("EvalCam", "TrackCam", "KeyLight", "RimLight", "FillLight",
             "GroundR1", "GroundR2", "GroundR3", "GroundR4", "Cam", "Sun",
             "Fill", "Ground"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ── Per-frame tracked camera ──────────────────────────────────────
cd = bpy.data.cameras.new("PhCam")
cam = bpy.data.objects.new("PhCam", cd)
scene.collection.objects.link(cam)

prev_dist = None
for f in frames:
    hp = sm_hips[f]
    r = sm_rad[f]
    dist = max(r * 2.8, rmax * 2.2)
    if prev_dist is not None:
        dist = prev_dist + max(-0.06, min(0.06, dist - prev_dist))
    prev_dist = dist
    off_dir = Vector((0.55, -1.0, 0.18)).normalized()
    loc = hp + off_dir * dist
    cam.location = loc
    aim = hp + Vector((0, 0, 0.9))
    direction = (aim - Vector(loc)).normalized()
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=f)
    cam.keyframe_insert(data_path="rotation_euler", frame=f)

scene.camera = cam

# ── Reflective dark-fantasy environment ──────────────────────────
L = rmax * 2.2
gm = bpy.data.materials.new("GroundMat_Ph4")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.12
ext = L * 10
pm = bpy.data.meshes.new("GroundMeshPh4")
pm.from_pydata(
    [(-ext + pc_center.x, -ext + pc_center.y, 0),
     (ext + pc_center.x, -ext + pc_center.y, 0),
     (ext + pc_center.x, ext + pc_center.y, 0),
     (-ext + pc_center.x, ext + pc_center.y, 0)],
    [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GroundPh4", pm)
scene.collection.objects.link(plane)
pm.materials.append(gm)


def add_area_light(name, energy, color, loc, sz):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = sz
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    d = (pc_center + Vector((0, 0, rmax * 0.5)) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)


add_area_light("KeyLight4", 2800, (1.0, 0.85, 0.55),
               pc_center + Vector((L * 0.9, -L * 0.9, L * 1.1)), L * 0.9)
add_area_light("RimLight4", 1600, (0.45, 0.6, 1.0),
               pc_center + Vector((-L * 1.0, L * 1.1, L * 0.8)), L * 0.7)
add_area_light("FillLight4", 380, (0.8, 0.82, 0.9),
               pc_center + Vector((-L * 0.6, -L * 1.2, L * 0.4)), L * 1.2)

# Reflective world (dark + slight rim env)
if not scene.world:
    scene.world = bpy.data.worlds.new("W4")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.008, 0.008, 0.012, 1)
    bg.inputs[1].default_value = 1.0

# ── EEVEE renderer with raytracing ───────────────────────────────
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print(f"Render engine: {scene.render.engine}")

ee = scene.eevee
if hasattr(ee, "use_raytracing"):
    ee.use_raytracing = True
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 32
if hasattr(ee, "shadow_ray_count"):
    ee.shadow_ray_count = 2

scene.render.resolution_x = 960
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.use_stamp = False

# ── Render all frames ─────────────────────────────────────────────
print(f"Rendering {len(frames)} frames to {FRAMES_DIR}...")
for f in frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FRAMES_DIR, f"f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"  frame {f}/{frames[-1]} done")
print(f"Rendered {len(frames)} frames")

# ── Encode to mp4 at 30fps ────────────────────────────────────────
# Scene is 24fps native; ffmpeg -framerate 30 re-times to 30fps (spec req)
cmd = [
    "ffmpeg", "-y",
    "-framerate", "30",
    "-start_number", str(frames[0]),
    "-i", os.path.join(FRAMES_DIR, "f%03d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "18",
    "-preset", "slow",
    MP4_OUT
]
print("Encoding:", " ".join(cmd))
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("ffmpeg stderr:", result.stderr[-2000:])
    raise RuntimeError("ffmpeg failed")
print(f"MP4 written: {MP4_OUT}")

# ── GLB Export ────────────────────────────────────────────────────
# Select: armature + skinned meshes + sword only (no floor, no colliders, no wind)
EXPORT_OBJECTS = {"char1", "CapeGrid", "RobeGrid", "Armature", "Godwyn_Sword"}
for obj in bpy.data.objects:
    obj.select_set(obj.name in EXPORT_OBJECTS)
bpy.context.view_layer.objects.active = arm

print("Exporting GLB:", GLB_OUT)

# Determine available glTF export parameters for Blender 5.2
try:
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        use_selection=True,
        export_format="GLB",
        # Animation
        export_animations=True,
        export_nla_strips=False,
        export_current_frame=False,
        export_frame_range=False,
        # Skinning
        export_skins=True,
        export_all_influences=False,
        # Morph targets
        export_morph=False,
        # Materials / textures
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        # Coordinate system
        export_yup=True,
        # Draco compression off for compatibility
        export_draco_mesh_compression_enable=False,
        # Keep armature
        export_def_bones=False,
    )
except Exception as e:
    print(f"Full param export failed ({e}), trying minimal...")
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        use_selection=True,
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_yup=True,
    )

glb_size = os.path.getsize(GLB_OUT)
print(f"GLB exported: {GLB_OUT} ({glb_size / 1024 / 1024:.1f} MB)")
print("PHASE4_RENDER_EXPORT_DONE")
