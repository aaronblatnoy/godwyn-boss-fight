"""
anim_xslash_probe2.py — hard data on sword geometry vs RightHand bone.
Prints sword evaluated world bbox + hand bone axes for several poses,
and renders close-ups of the hand so the blade direction is visible.
"""
import bpy, os, math
from mathutils import Euler, Vector

REPO   = os.path.expanduser("~/godwyn-boss-fight")
GLB    = os.path.join(REPO, "models", "godwyn_game.glb")
OUTDIR = os.path.join(REPO, "renders", "xslash", "probe2")
os.makedirs(OUTDIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm   = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sword = bpy.data.objects["Godwyn_Sword"]

print(f"[p2] sword matrix_world: {[tuple(round(v,3) for v in r) for r in sword.matrix_world]}")
print(f"[p2] sword parent={sword.parent.name} parent_type={sword.parent_type} parent_bone={sword.parent_bone}")
print(f"[p2] sword local bbox: {[tuple(round(c,2) for c in b) for b in sword.bound_box]}")
print(f"[p2] sword modifiers: {[m.type for m in sword.modifiers]}")
print(f"[p2] armature matrix_world: {[tuple(round(v,3) for v in r) for r in arm.matrix_world]}")

sc = bpy.context.scene
bpy.ops.object.light_add(type='SUN', location=(4, -6, 10))
sun = bpy.context.active_object
sun.data.energy = 6.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)), 'XYZ')
bpy.ops.object.light_add(type='AREA', location=(-3, -5, 4))
fill = bpy.context.active_object
fill.data.energy = 400
fill.data.size = 5

bpy.ops.object.camera_add(location=(2.8, -4.5, 2.0))
cam = bpy.context.active_object
sc.camera = cam

try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 640
sc.render.resolution_y = 640
sc.render.image_settings.file_format = 'PNG'
sc.render.use_stamp = True
for attr in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_scene", "use_stamp_camera",
             "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note = True
sc.render.stamp_font_size = 20
sc.render.stamp_background = (0, 0, 0, 0.7)

for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

def report(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    sw = sword.evaluated_get(dg)
    mw = sw.matrix_world
    corners = [mw @ Vector(c) for c in sw.bound_box]
    cx = sum((c for c in corners), Vector()) / 8
    hand = arm.pose.bones["RightHand"]
    hw  = arm.matrix_world @ hand.head
    tw  = arm.matrix_world @ hand.tail
    far = max(corners, key=lambda c: (c - hw).length)
    print(f"[p2:{tag}] hand head=({hw.x:+.2f},{hw.y:+.2f},{hw.z:+.2f}) "
          f"tail=({tw.x:+.2f},{tw.y:+.2f},{tw.z:+.2f})")
    print(f"[p2:{tag}] sword bbox center=({cx.x:+.2f},{cx.y:+.2f},{cx.z:+.2f}) "
          f"far corner=({far.x:+.2f},{far.y:+.2f},{far.z:+.2f}) "
          f"dist(far,hand)={(far-hw).length:.2f}")
    for i, c in enumerate(corners):
        print(f"[p2:{tag}]   corner{i}: ({c.x:+.2f},{c.y:+.2f},{c.z:+.2f})")

def set_pose(pose):
    for pb in arm.pose.bones:
        pb.rotation_euler = Euler((0, 0, 0), 'XYZ')
    for n, (rx, ry, rz) in pose.items():
        pb = arm.pose.bones.get(n)
        if pb:
            pb.rotation_euler = Euler((math.radians(rx), math.radians(ry),
                                       math.radians(rz)), 'XYZ')
        else:
            print(f"[p2] MISSING {n}")
    bpy.context.view_layer.update()

POSES = {
    "rest":    {},
    "anchor":  {"RightArm": (-80, 0, -40), "RightForeArm": (-30, 25, 0)},
    "fore90":  {"RightForeArm": (-90, 0, 0)},          # isolate forearm effect
    "hand45":  {"RightHand": (-45, 0, 0)},             # isolate wrist effect
    "armY60":  {"RightArm": (0, 60, 0)},               # isolate arm roll
}

for tag, pose in POSES.items():
    set_pose(pose)
    report(tag)
    # aim camera at the hand
    hw = arm.matrix_world @ arm.pose.bones["RightHand"].head
    cam.rotation_euler = (hw - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.stamp_note_text = tag
    sc.render.filepath = os.path.join(OUTDIR, f"{tag}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[p2] rendered {tag}")
print("[p2] DONE")
