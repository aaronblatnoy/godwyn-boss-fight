"""
Phase 1 — PASS 2: ground + verify + render.

Run as a SEPARATE blender invocation on the blend saved by mocap_retarget.py:
    blender --background models/godwyn_mocap.blend --python scripts/mocap_ground_render.py

(Pose evaluation inside the process that did the glTF imports is corrupt —
hips translation off ~10x — so all measurement happens here, in a fresh
process where the file evaluates correctly.)

- Measure min foot/toe world-Z across the clip, bake a constant offset into
  the Hips location fcurves so the lowest contact sits at Z=0
- Verify sword stays rigidly attached to RightHand
- Save the blend, render an EEVEE frame strip to /tmp/godwyn_retarget/
"""

import bpy
import os
import math
from mathutils import Vector

OUT_DIR = "/tmp/godwyn_retarget"
os.makedirs(OUT_DIR, exist_ok=True)

scene = bpy.context.scene
our_arm = next(o for o in scene.objects if o.type == "ARMATURE")
sword = next((o for o in scene.objects if "sword" in o.name.lower()), None)
act = our_arm.animation_data.action
slot = our_arm.animation_data.action_slot
cb = None
for layer in act.layers:
    for strip in layer.strips:
        c = strip.channelbag(slot)
        if c:
            cb = c
assert cb is not None and len(cb.fcurves) > 0
s = our_arm.scale.x  # uniform scale, no object rotation → armature Z is world up
print(f"action={act.name!r} fcurves={len(cb.fcurves)} arm scale={s:.4f}")

FOOT = ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase")

def min_foot_z(frame):
    # HEADS only — the glTF importer assigned bogus huge bone lengths, so
    # tails are thousands of units off and must never be used for measurement.
    scene.frame_set(frame)
    ae = our_arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return min(ae.pose.bones[bn].head.z for bn in FOOT) * s  # world units

frames = list(range(scene.frame_start, scene.frame_end + 1))
zs = [min_foot_z(f) for f in frames]
zmin = min(zs)
print(f"foot min-Z (world): min={zmin:.4f} max={max(zs):.4f} "
      f"(start={zs[0]:.4f} end={zs[-1]:.4f})")

already = bool(act.get("godwyn_grounded"))
if already:
    print("grounding: already applied previously, skipping")
elif abs(zmin) > 2e-2:
    pb = our_arm.pose.bones["Hips"]
    M = pb.bone.matrix_local.to_3x3().inverted()
    delta = M @ Vector((0.0, 0.0, -zmin / s))  # armature units
    print(f"grounding: world dz={-zmin:.4f} -> hips-local delta="
          f"{tuple(round(c, 4) for c in delta)}")
    for fc in cb.fcurves:
        if fc.data_path == 'pose.bones["Hips"].location':
            d = delta[fc.array_index]
            if abs(d) < 1e-6:
                continue
            for kp in fc.keyframe_points:
                kp.co.y += d
                kp.handle_left.y += d
                kp.handle_right.y += d
            fc.update()
    zs2 = [min_foot_z(f) for f in frames]
    print(f"after grounding (world): min={min(zs2):.4f} max={max(zs2):.4f} "
          f"(start={zs2[0]:.4f} end={zs2[-1]:.4f})")
else:
    print("grounding: already grounded (within 2cm)")
act["godwyn_grounded"] = True

def hips_pos(frame):
    scene.frame_set(frame)
    ae = our_arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return (ae.pose.bones["Hips"].head * s).copy()

h0, h1 = hips_pos(frames[0]), hips_pos(frames[-1])
print(f"hips travel start->end (world): dx={h1.x-h0.x:.3f} "
      f"dy={h1.y-h0.y:.3f} dz={h1.z-h0.z:.3f}")

if sword:
    gaps = []
    for f in (frames[0], frames[len(frames) // 3], frames[len(frames) // 2],
              frames[2 * len(frames) // 3], frames[-1]):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        sw = sword.evaluated_get(dg).matrix_world.translation
        ae = our_arm.evaluated_get(dg)
        hd = ae.pose.bones["RightHand"].head * s
        gaps.append((sw - Vector(hd)).length)
        print(f"f{f}: sword=({sw.x:.3f},{sw.y:.3f},{sw.z:.3f}) "
              f"hand=({hd.x:.3f},{hd.y:.3f},{hd.z:.3f}) gap={gaps[-1]:.4f}")
    spread = max(gaps) - min(gaps)
    print(f"sword-hand: gap spread={spread:.5f} "
          f"({'RIGID - OK' if spread < 0.01 else 'NOT RIGID - PROBLEM'}), "
          f"max gap={max(gaps):.3f} world "
          f"({'IN HAND - OK' if max(gaps) < 3.0 else 'DETACHED - PROBLEM'})")

blend_path = bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print(f"saved {blend_path}")

# ── camera framing from world-space bone bbox across the clip ────
n = len(frames)
strip_frames = [frames[0], frames[n // 6], frames[n * 2 // 6], frames[n * 3 // 6],
                frames[n * 4 // 6], frames[n * 5 // 6], frames[-1]]
mn = Vector((1e9, 1e9, 1e9))
mx = Vector((-1e9, -1e9, -1e9))
for f in strip_frames:
    scene.frame_set(f)
    ae = our_arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for bn in ("Hips", "Head", "LeftFoot", "RightFoot", "LeftHand", "RightHand",
               "LeftToeBase", "RightToeBase", "head_end"):
        pb = ae.pose.bones.get(bn)
        if not pb:
            continue
        p = pb.head * s  # heads only — tails are bogus (huge importer lengths)
        mn = Vector(map(min, mn, p))
        mx = Vector(map(max, mx, p))
# include sword sweep
if sword:
    for f in strip_frames:
        scene.frame_set(f)
        p = sword.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation
        mn = Vector(map(min, mn, p))
        mx = Vector(map(max, mx, p))
center = (mn + mx) / 2
size = max(mx - mn)
print(f"bone+sword bbox (world) center={tuple(round(c, 3) for c in center)} size={size:.3f}")

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
dist = size * 1.9
cam.location = center + Vector((dist * 0.75, -dist * 0.75, size * 0.25))
direc = (center - cam.location).normalized()
cam.rotation_euler = direc.to_track_quat('-Z', 'Y').to_euler()
cam_data.clip_start = 0.01
cam_data.clip_end = max(100.0, dist * 20)
scene.camera = cam

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), math.radians(20), math.radians(-140))
scene.collection.objects.link(fill)
if not scene.world:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.12, 0.12, 0.14, 1)

# ground plane at Z=0 for foot-contact reading
if "Ground" not in bpy.data.objects:
    pm = bpy.data.meshes.new("Ground")
    ext = size * 4
    pm.from_pydata([(-ext, -ext, 0), (ext, -ext, 0), (ext, ext, 0), (-ext, ext, 0)],
                   [], [(0, 1, 2, 3)])
    plane = bpy.data.objects.new("Ground", pm)
    scene.collection.objects.link(plane)
    gmat = bpy.data.materials.new("GroundMat")
    gmat.diffuse_color = (0.25, 0.25, 0.27, 1)
    pm.materials.append(gmat)

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print(f"engine: {scene.render.engine}")
scene.render.resolution_x = 540
scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'

for f in strip_frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT_DIR, f"f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered f{f}")

print("DONE")
