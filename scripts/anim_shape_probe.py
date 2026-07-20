"""Objective X-slash-vs-spin probe. Headless.

Answers, from geometry only (no VLM): does the character SPIN (large root Z rotation),
and does the sword hand trace two crossing diagonals (an X) or a circle (a sweep)?

Usage:
  blender --background --python anim_shape_probe.py -- \
      --glb models/godwyn_xslash_v2.glb --action Godwyn_XSlash
"""
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

glb = arg("--glb")
action_name = arg("--action", "Godwyn_XSlash")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
assert arm, "no armature"
act = bpy.data.actions.get(action_name) or next(iter(bpy.data.actions), None)
assert act, "no action"
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
if hasattr(act, "slots") and act.slots:
    arm.animation_data.action_slot = act.slots[0]

sc = bpy.context.scene
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])

def bone(name):
    return arm.pose.bones.get(name)

# pick a root bone (Hips) and the sword hand (RightHand)
root = bone("Hips") or bone("mixamorig:Hips") or arm.pose.bones[0]
hand = bone("RightHand") or bone("mixamorig:RightHand")
# a tip proxy: RightHand head in world; also track the hand direction
def world_head(pb):
    return arm.matrix_world @ pb.head

def root_z_deg(pb):
    m = (arm.matrix_world @ pb.matrix).to_euler('YXZ')
    return math.degrees(m.z)

zs, hand_xy, hand_xyz = [], [], []
for f in range(f0, f1 + 1):
    sc.frame_set(f)
    zs.append(root_z_deg(root))
    h = world_head(hand) if hand else Vector((0, 0, 0))
    hand_xy.append((h.x, h.y))
    hand_xyz.append((h.x, h.y, h.z))

# unwrap the root Z so a spin accumulates instead of wrapping at 180
def unwrap(seq):
    out = [seq[0]]
    for v in seq[1:]:
        d = v - out[-1]
        while d > 180: d -= 360
        while d < -180: d += 360
        out.append(out[-1] + d)
    return out

zu = unwrap(zs)
net_spin = zu[-1] - zu[0]
total_sweep = max(zu) - min(zu)

# hand vertical travel: an X-slash = two clear DOWN strokes (z goes high->low twice).
# count direction reversals in hand height to distinguish two cuts vs one circular arc.
hz = [p[2] for p in hand_xyz]
reversals = 0
for i in range(1, len(hz) - 1):
    if (hz[i] - hz[i-1]) * (hz[i+1] - hz[i]) < 0:
        reversals += 1

# hand horizontal span (left-right): an X crosses the centerline; a spin circles the body
hx = [p[0] for p in hand_xyz]
hy = [p[1] for p in hand_xyz]
span_x = max(hx) - min(hx)
span_y = max(hy) - min(hy)
span_z = max(hz) - min(hz)

fps = sc.render.fps or 24
dur = (f1 - f0 + 1) / fps

print("=== ANIM SHAPE PROBE:", action_name, "===")
print(f"frames {f0}..{f1}  dur={dur:.2f}s  fps={fps}")
print(f"ROOT (Hips) net Z-rotation: {net_spin:.0f} deg   total sweep: {total_sweep:.0f} deg")
print(f"  -> spin rate ~{abs(net_spin)/dur:.0f} deg/s ({abs(net_spin)/dur/360:.2f} rot/s; SPEC cap = 1 rot/s)")
print(f"HAND (RightHand) travel span  X(LR)={span_x:.1f}  Y(FB)={span_y:.1f}  Z(UD)={span_z:.1f}")
print(f"HAND height direction reversals: {reversals}  (X-slash = ~2 clean down-strokes; many small = circular/noisy)")
print("VERDICT:",
      "SPIN/SWEEP (root rotates >120 deg)" if abs(net_spin) > 120 or total_sweep > 150
      else ("looks STATIONARY-ish — check hand path for the X" ))
