"""
anim_video.py — render the WIP animation to ONE full EEVEE mp4.

CLI (after --):
  --glb  <path>       source .glb  (mutually exclusive with --blend)
  --blend <path>      source .blend (opens mainfile directly; action fetched
                      from the scene's NLA or the named action)
  --action <name>     action name to push onto the armature (required for --glb)
  --out <path>        output mp4 path  [default: /tmp/<action>.mp4]

Examples:
  blender --background --python ~/godwyn-boss-fight/scripts/anim_video.py -- \
      --glb ~/godwyn-boss-fight/models/godwyn_xslash.glb --action xslash_combo

  blender --background --python ~/godwyn-boss-fight/scripts/anim_video.py -- \
      --blend ~/godwyn-boss-fight/models/godwyn_xslash.blend --action xslash_combo

INVARIANTS:
  INV-2  EEVEE render; Blender 5.2 slotted actions (scene.frame_set; no action.fcurves)
  INV-3  Idempotent: deletes-by-name any temp camera/light/plane it adds before recreating
  INV-5  READ-ONLY on the rig/materials — never saves the blend
  INV-6  Output stays on the server (/tmp); video never leaves the box

The script prints the final mp4 path as its LAST line.
"""

import bpy
import math
import os
import subprocess
import sys
from mathutils import Vector

# ── Parse CLI args (everything after --) ─────────────────────────────────────
def _parse_args():
    argv = sys.argv
    try:
        idx = argv.index("--") + 1
    except ValueError:
        idx = len(argv)
    args = argv[idx:]

    glb_path = blend_path = action_name = out_path = None
    i = 0
    while i < len(args):
        tok = args[i]
        if tok == "--glb" and i + 1 < len(args):
            glb_path = os.path.expanduser(args[i + 1]); i += 2
        elif tok == "--blend" and i + 1 < len(args):
            blend_path = os.path.expanduser(args[i + 1]); i += 2
        elif tok == "--action" and i + 1 < len(args):
            action_name = args[i + 1]; i += 2
        elif tok == "--out" and i + 1 < len(args):
            out_path = os.path.expanduser(args[i + 1]); i += 2
        else:
            i += 1

    if not glb_path and not blend_path:
        print("[anim_video] ERROR: must supply --glb or --blend")
        sys.exit(1)
    if glb_path and not action_name:
        print("[anim_video] ERROR: --glb requires --action")
        sys.exit(1)

    return glb_path, blend_path, action_name, out_path


glb_path, blend_path, action_name, out_path = _parse_args()

# ── Derived paths ─────────────────────────────────────────────────────────────
_safe_name = (action_name or "anim").replace(" ", "_").replace("/", "_")
if not out_path:
    out_path = f"/tmp/{_safe_name}.mp4"
_frame_dir = os.path.splitext(out_path)[0] + "_frames"
os.makedirs(_frame_dir, exist_ok=True)

print(f"[anim_video] source glb={glb_path}  blend={blend_path}")
print(f"[anim_video] action={action_name}  out={out_path}  frames={_frame_dir}")

# ── Load scene ────────────────────────────────────────────────────────────────
if glb_path:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    print(f"[anim_video] imported {glb_path}")
else:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    print(f"[anim_video] opened {blend_path}")

sc = bpy.context.scene

# ── Find armature ─────────────────────────────────────────────────────────────
arms = [o for o in sc.objects if o.type == "ARMATURE"]
if not arms:
    print("[anim_video] ERROR: no armature found in scene")
    sys.exit(1)
arm = arms[0]
print(f"[anim_video] armature={arm.name}")

# ── Bind the action (slotted, Blender 5.2 — no action.fcurves) ───────────────
if action_name:
    act = bpy.data.actions.get(action_name)
    if act is None:
        print(f"[anim_video] WARNING: action '{action_name}' not found; "
              f"available={[a.name for a in bpy.data.actions]}")
        # Fall through: use the scene's existing frame range (may already be set
        # from the .blend or a prior bake step).
    else:
        # Slotted action assignment — Blender 5.2 API
        if arm.animation_data is None:
            arm.animation_data_create()
        anim_data = arm.animation_data
        anim_data.action = act
        # If the action has a slot (Blender 5.2), bind the first slot
        if hasattr(act, "slots") and act.slots:
            anim_data.action_slot = act.slots[0]
        print(f"[anim_video] bound action '{act.name}' "
              f"range={act.frame_range[0]:.0f}..{act.frame_range[1]:.0f}")
        # Set scene frame range from the action
        sc.frame_start = max(1, int(act.frame_range[0]))
        sc.frame_end   = int(act.frame_range[1])

frames = list(range(sc.frame_start, sc.frame_end + 1))
print(f"[anim_video] scene frames {sc.frame_start}..{sc.frame_end}  "
      f"({len(frames)} frames)  fps={sc.render.fps}")
if len(frames) < 2:
    print("[anim_video] ERROR: clip has fewer than 2 frames — aborting")
    sys.exit(1)

# ── Measure motion bbox (sample every 4th frame for speed) ───────────────────
_TRACK_BONES = ("Hips", "Head", "head_end", "LeftFoot", "RightFoot",
                "LeftHand", "RightHand", "LeftToeBase", "RightToeBase")
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
_scale = arm.scale.x
for _f in frames[::4] + [frames[-1]]:
    sc.frame_set(_f)
    _dg = bpy.context.evaluated_depsgraph_get()
    _ae = arm.evaluated_get(_dg)
    for _bn in _TRACK_BONES:
        _pb = _ae.pose.bones.get(_bn)
        if _pb:
            _p = _pb.head * _scale
            mn = Vector(map(min, mn, _p))
            mx = Vector(map(max, mx, _p))
center = (mn + mx) / 2
size   = max((mx - mn).x, (mx - mn).y, (mx - mn).z)
size   = max(size, 0.5)   # guard against degenerate T-pose
print(f"[anim_video] bbox center={tuple(round(v,2) for v in center)}  size={size:.2f}")

# ── Idempotent: remove any temp objects from a prior run ─────────────────────
_TEMP_NAMES = ("AnimVidCam", "AnimVidKey", "AnimVidRim", "AnimVidFill",
               "AnimVidGround", "AnimVidWorld")
for _name in _TEMP_NAMES:
    if _name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[_name], do_unlink=True)
        print(f"[anim_video] removed prior temp object '{_name}'")
if "AnimVidWorld" in bpy.data.worlds:
    bpy.data.worlds.remove(bpy.data.worlds["AnimVidWorld"])

# ── Dark-fantasy env: glossy black ground + key/rim/fill lights ──────────────
# Convention from mocap_combo_render_r4.py — gold + blue read on near-black.
_L = size * 2.2

# Ground plane
_gm = bpy.data.materials.new("AnimVidGroundMat")
_gm.use_nodes = True
_bsdf = _gm.node_tree.nodes.get("Principled BSDF")
if _bsdf is None:
    _bsdf = _gm.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
_bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
_bsdf.inputs["Metallic"].default_value   = 0.85
_bsdf.inputs["Roughness"].default_value  = 0.12
_ext = _L * 10
_pm = bpy.data.meshes.new("AnimVidGround")
_pm.from_pydata(
    [(-_ext + center.x, -_ext + center.y, 0),
     ( _ext + center.x, -_ext + center.y, 0),
     ( _ext + center.x,  _ext + center.y, 0),
     (-_ext + center.x,  _ext + center.y, 0)],
    [], [(0, 1, 2, 3)])
_plane = bpy.data.objects.new("AnimVidGround", _pm)
sc.collection.objects.link(_plane)
_pm.materials.append(_gm)

def _add_area_light(name, energy, color, loc, sz):
    _ld = bpy.data.lights.new(name, "AREA")
    _ld.energy = energy
    _ld.color  = color
    _ld.size   = sz
    _ob = bpy.data.objects.new(name, _ld)
    _aim_at = center + Vector((0, 0, size * 0.5))
    _d = (_aim_at - Vector(loc)).normalized()
    _ob.rotation_euler = _d.to_track_quat("-Z", "Y").to_euler()
    _ob.location = loc
    sc.collection.objects.link(_ob)
    return _ob

# Key: warm golden above-right
_add_area_light("AnimVidKey", 2600, (1.0, 0.85, 0.55),
                center + Vector((_L * 0.9, -_L * 0.9, _L * 1.1)), _L * 0.9)
# Rim: cool blue-silver from upper-left (makes the blue robe sing)
_add_area_light("AnimVidRim", 1500, (0.45, 0.60, 1.0),
                center + Vector((-_L * 1.0,  _L * 1.1, _L * 0.8)), _L * 0.7)
# Fill: soft warm fill
_add_area_light("AnimVidFill", 350, (0.80, 0.82, 0.90),
                center + Vector((-_L * 0.6, -_L * 1.2, _L * 0.4)), _L * 1.2)

# World background: near-black void
_w = bpy.data.worlds.new("AnimVidWorld")
sc.world = _w
_w.use_nodes = True
_bg = _w.node_tree.nodes.get("Background")
if _bg is None:
    _bg = _w.node_tree.nodes.new("ShaderNodeBackground")
_bg.inputs[0].default_value = (0.008, 0.008, 0.012, 1)
_bg.inputs[1].default_value = 1.0

# ── Camera: front/moveset framing showing full silhouette ────────────────────
# Near-frontal, slightly offset right so the sword arc is visible.
# Elevation 0.22*size below hips-to-head center keeps the silhouette centred.
_cam_data = bpy.data.cameras.new("AnimVidCam")
_cam_data.lens       = 45
_cam_data.clip_start = 0.01
_cam_data.clip_end   = 800
_cam = bpy.data.objects.new("AnimVidCam", _cam_data)
sc.collection.objects.link(_cam)
_dist = size * 1.9
_off_dir = Vector((0.15, -1.0, 0.18)).normalized()   # near-frontal, slight right offset
_cam.location = center + _off_dir * _dist
_aim_target   = center + Vector((0, 0, size * 0.05))   # aim ~chest height
_cam.rotation_euler = (
    (_aim_target - _cam.location).normalized()
    .to_track_quat("-Z", "Y").to_euler()
)
sc.camera = _cam
print(f"[anim_video] camera at {tuple(round(v,2) for v in _cam.location)}  "
      f"dist={_dist:.2f}m")

# ── EEVEE render settings ─────────────────────────────────────────────────────
for _eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = _eng
        break
    except TypeError:
        continue
print(f"[anim_video] engine={sc.render.engine}")

_ee = sc.eevee
if hasattr(_ee, "use_raytracing"):
    _ee.use_raytracing = True
if hasattr(_ee, "taa_render_samples"):
    _ee.taa_render_samples = 32

sc.render.resolution_x          = 960
sc.render.resolution_y          = 1080
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.use_stamp = False
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass   # not fatal

fps = sc.render.fps
if fps < 24 or fps > 30:
    sc.render.fps = 30
    fps = 30
print(f"[anim_video] fps={fps}  resolution={sc.render.resolution_x}x{sc.render.resolution_y}")

# ── Render every frame to PNG ─────────────────────────────────────────────────
print(f"[anim_video] rendering {len(frames)} frames to {_frame_dir} ...")
for _f in frames:
    sc.frame_set(_f)
    sc.render.filepath = os.path.join(_frame_dir, f"f{_f:04d}.png")
    bpy.ops.render.render(write_still=True)
    if _f == frames[0] or _f == frames[-1] or (_f - frames[0]) % 20 == 0:
        print(f"[anim_video]   frame {_f}/{frames[-1]}")

_rendered = len([x for x in os.listdir(_frame_dir) if x.endswith(".png")])
print(f"[anim_video] rendered {_rendered} PNG frames")
if _rendered < 2:
    print(f"[anim_video] ERROR: only {_rendered} frame(s) produced — aborting encode")
    sys.exit(1)

# ── Encode mp4 via ffmpeg ─────────────────────────────────────────────────────
# Pattern: _frame_dir/f{frame_start:04d}.png .. f{frame_end:04d}.png
_ffmpeg = [
    "ffmpeg", "-y",
    "-framerate", str(fps),
    "-start_number", str(sc.frame_start),
    "-i", os.path.join(_frame_dir, "f%04d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "18",
    "-movflags", "+faststart",
    out_path,
]
print(f"[ffmpeg] {' '.join(_ffmpeg)}")
_res = subprocess.run(_ffmpeg, capture_output=True, text=True)
if _res.stdout:
    print(_res.stdout[-2000:])
if _res.stderr:
    print(_res.stderr[-2000:])
if _res.returncode != 0:
    print(f"[anim_video] ERROR: ffmpeg failed (rc={_res.returncode})")
    sys.exit(1)

_sz = os.path.getsize(out_path)
print(f"[anim_video] wrote mp4  size={_sz:,} bytes  frames={_rendered}  fps={fps}")
print(out_path)
