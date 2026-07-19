"""
st_feet_qa.py — QA renders of godwyn_st_feet.blend feet from tight angles.
Headless: blender --background --python ~/godwyn-boss-fight/scripts/st_feet_qa.py 2>&1
"""
import bpy
import os
import math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
OUT = "/tmp/st_feet"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_st_feet.blend"))

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
pbs = arm.pose.bones
for side in ("Left", "Right"):
    pb = pbs[side + "ToeBase"]
    d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
    print(f"[{side}] toe yaw {math.degrees(math.atan2(d.x, -d.y)):+.1f} deg from forward")

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, target, dist, elev, azim, lens=50):
    cam.data.lens = lens
    el, a = math.radians(elev), math.radians(azim)
    off = Vector((dist * math.cos(el) * math.sin(a),
                  -dist * math.cos(el) * math.cos(a),
                  dist * math.sin(el)))
    cam.location = target + off
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")


lf = Vector((0.38, -0.40, 0.10))
rf = Vector((-0.38, -0.40, 0.10))
shoot("q_lfoot_close.png", lf, 1.1, 12, 25, 60)
shoot("q_rfoot_close.png", rf, 1.1, 12, -25, 60)
shoot("q_feet_ground.png", Vector((0, -0.45, 0.08)), 2.0, 2, 0, 60)
shoot("q_feet_inside3q.png", Vector((0, -0.35, 0.10)), 2.2, 6, 30, 55)
print("ST_FEET_QA DONE")
