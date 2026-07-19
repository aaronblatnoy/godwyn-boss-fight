"""p_fixer_r2b_cut2_probe.py — sweep RightArm X/Z for the CUT2_END pose and
print the RightHand head world z (the grip height). Goal: grip z <= 1.6."""
import bpy, os, math
from mathutils import Euler

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB  = os.path.join(REPO, "models", "godwyn_game.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

BASE = {                              # CUT2_END minus RightArm
    "RightShoulder": (0, 0, -16),
    "RightForeArm":  (-8, 10, 0),
    "LeftShoulder":  (0, 0, 6),
    "LeftArm":       (20, 0, 14),
    "LeftForeArm":   (-16, 0, 0),
    "Spine":         (10, 0, -18),
    "Spine01":       (6, 0, -10),
    "Spine02":       (4, 0, -5),
    "Hips":          (4, 0, -6),
    "Head":          (2, 0, 8),
    "LeftUpLeg":     (-14, 0, 0),
    "LeftLeg":       (9, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

def set_pose(ra):
    for pb in arm.pose.bones:
        pb.rotation_euler = Euler((0, 0, 0), 'XYZ')
    for n, (rx, ry, rz) in BASE.items():
        arm.pose.bones[n].rotation_euler = Euler(
            (math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ')
    arm.pose.bones["RightArm"].rotation_euler = Euler(
        (math.radians(ra[0]), math.radians(ra[1]), math.radians(ra[2])), 'XYZ')
    bpy.context.view_layer.update()
    M = arm.matrix_world @ arm.pose.bones["RightHand"].matrix
    return M.translation

# chosen CUT2_END candidate
BASE["RightForeArm"] = (-20, 10, 0)
for x, z in ((8, -24), (5, -18), (10, -28)):
    p = set_pose((x, 0, z))
    print(f"[probe] CUT2END RightArm X={x} Z={z} -> grip=({p.x:+.2f},{p.y:+.2f},z={p.z:.2f})")

# WINDUP2 grip height — the real reason cut2's stroke is short (grip@f40~1.9
# vs windup1's 2.79). Sweep arm raise on his LEFT side.
BASE2 = {
    "RightShoulder": (0, 0, 16),
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (26, 0, 16),
    "LeftForeArm":   (-22, 0, 0),
    "Spine":         (0, 0, 26),
    "Spine01":       (0, 0, 10),
    "Spine02":       (-4, 0, 5),
    "Hips":          (0, 0, 6),
    "Head":          (0, 0, -16),
    "LeftUpLeg":     (-14, 0, 0),
    "LeftLeg":       (9, 0, 0),
    "RightUpLeg":    (7, 0, 0),
}
BASE2["RightForeArm"] = (-25, -15, 0)
BASE.clear(); BASE.update(BASE2)
best = []
for x in (-100, -85, -70, -55):
    for y in (-45, 0, 45):
        for z in (-120, -80, -40, 0, 40, 80, 120):
            p = set_pose((x, y, z))
            tag = " <== CAND" if (p.x > 0.15 and p.z > 2.45) else ""
            print(f"[probe] W2 RightArm X={x:4d} Y={y:3d} Z={z:4d}"
                  f" -> grip=({p.x:+.2f},{p.y:+.2f},z={p.z:.2f}){tag}")
