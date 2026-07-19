"""Probe: sweep RightArm (X,Z) inside the CUT1_END / CUT2_END pose context and
print the RightHand world position, to find angles that plant the grip near
hip height (~1.5-1.7 on this boss-scale rig) and across/out front."""
import bpy, os, math
from mathutils import Euler

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB  = os.path.join(REPO, "models", "godwyn_game.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

CTRL = ["RightShoulder", "RightArm", "RightForeArm", "RightHand",
        "LeftShoulder", "LeftArm", "LeftForeArm",
        "Spine", "Spine01", "Spine02", "Hips", "Head",
        "LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg"]
for n in CTRL:
    pb = arm.pose.bones.get(n)
    if pb:
        pb.rotation_mode = 'XYZ'

CUT1_END_CTX = {
    "RightShoulder": (0, 0, 14),
    "RightForeArm":  (-5, 0, 0),
    "Spine":  (5, 0, 22), "Spine01": (3, 0, 12), "Spine02": (2, 0, 6),
    "Hips":   (4, 0, 8),
    "LeftUpLeg": (-18, 0, 0), "LeftLeg": (12, 0, 0), "RightUpLeg": (10, 0, 0),
}
CUT2_END_CTX = {
    "RightShoulder": (0, 0, -16),
    "RightForeArm":  (-8, 10, 0),
    "Spine":  (10, 0, -18), "Spine01": (6, 0, -10), "Spine02": (4, 0, -5),
    "Hips":   (4, 0, -6),
    "LeftUpLeg": (-14, 0, 0), "LeftLeg": (9, 0, 0), "RightUpLeg": (8, 0, 0),
}

def set_ctx(ctx):
    for n in CTRL:
        pb = arm.pose.bones.get(n)
        if not pb:
            continue
        rx, ry, rz = ctx.get(n, (0, 0, 0))
        pb.rotation_euler = Euler((math.radians(rx), math.radians(ry),
                                   math.radians(rz)), 'XYZ')

for label, ctx, sh_zs, arm_zs in (
        ("CUT1_END(left,+X)", CUT1_END_CTX, (14, 6, 0), (-25, -35, -45)),
        ("CUT2_END(right,-X)", CUT2_END_CTX, (-16, -6, 0, 8), (25, 35, 45))):
    print(f"\n[probe] ==== {label} ====   (want hand LOW + slightly across + y<0)")
    for shz in sh_zs:
        for ax in (5, 12, 20):
            for az in arm_zs:
                set_ctx(ctx)
                arm.pose.bones["RightShoulder"].rotation_euler = Euler(
                    (0, 0, math.radians(shz)), 'XYZ')
                arm.pose.bones["RightArm"].rotation_euler = Euler(
                    (math.radians(ax), 0, math.radians(az)), 'XYZ')
                bpy.context.view_layer.update()
                h = arm.matrix_world @ arm.pose.bones["RightHand"].head
                print(f"[probe] Sh Z={shz:+3d} Arm X={ax:+3d} Z={az:+3d} -> hand"
                      f" x={h.x:+.2f} y={h.y:+.2f} z={h.z:+.2f}")
print("[probe] DONE")
