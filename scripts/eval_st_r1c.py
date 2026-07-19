"""eval_st_r1c.py — evaluator follow-up shots: cleaner grip views + milder deform."""
import bpy, os, math
from mathutils import Vector, Matrix

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_st_feet.blend")
OUT = "/tmp/eval_st_r1c"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
pbs = arm.pose.bones

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("W"); world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03,0.03,0.035,1)
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun",'SUN'))
sun.data.energy = 4.0; sun.data.color = (1.0,0.92,0.6)
sun.rotation_euler = (math.radians(50),0,math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill",'SUN'))
fill.data.energy = 2.0
fill.rotation_euler = (math.radians(60),0,math.radians(-140))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam); scene.camera = cam

def shoot(name, target, dist, elev, azim, lens=50):
    cam.data.lens = lens
    el, a = math.radians(elev), math.radians(azim)
    cam.location = target + Vector((dist*math.cos(el)*math.sin(a),
                                    -dist*math.cos(el)*math.cos(a),
                                    dist*math.sin(el)))
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")

hand_w = arm.matrix_world @ pbs["RightHand"].head
# wider grip views, several azimuths, moderate distance
shoot("g_grip_a.png", hand_w, 1.8, 5, -30, 60)
shoot("g_grip_b.png", hand_w, 1.8, 5, -90, 60)
shoot("g_grip_c.png", hand_w, 1.8, 20, -150, 60)
shoot("g_grip_d.png", hand_w, 1.8, -25, -60, 60)
# sword alone with hand: hide nothing, but shoot along blade
shoot("g_grip_low.png", hand_w + Vector((-0.15,-0.2,-0.3)), 2.2, 0, -70, 50)

# milder deform: 40 deg raise, 15 spine, 25 leg
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
def rotw(pb, axis, deg):
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    Aw = arm.matrix_world; Mw = Aw @ pb.matrix
    T = Matrix.Translation(Mw.translation.copy())
    pb.matrix = Aw.inverted() @ (T @ R @ T.inverted() @ Mw)
    bpy.context.view_layer.update()
rotw(pbs["RightArm"], (1,0,0), 40)
rotw(pbs["Spine01"], (0,0,1), 15)
rotw(pbs["LeftUpLeg"], (1,0,0), -25)
rotw(pbs["LeftLeg"], (1,0,0), 18)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

shoot("m_pose_front.png", Vector((0,0,1.5)), 8.0, 8, -20, 35)
shoot("m_pose_3q.png", Vector((0,0,1.5)), 8.0, 10, -55, 35)
hw2 = arm.matrix_world @ pbs["RightHand"].head
shoot("m_shoulder.png", arm.matrix_world @ pbs["RightArm"].head, 1.6, 10, -60, 50)
shoot("m_hand.png", hw2, 1.8, 5, -60, 55)
shoot("m_legs.png", Vector((0,-0.3,0.5)), 3.0, 5, -30, 45)
print("EVAL_ST_R1C DONE")
