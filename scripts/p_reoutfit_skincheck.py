"""p_reoutfit_skincheck.py — coverage diagnostic. Opens the built blend,
turns the skin PURE RED (emission, unmistakable), hides the cape + hair so
nothing masks gaps, renders quick GPU views to /tmp/skincheck_*.png.
Does NOT save the blend."""
import bpy, os, sys, math
from mathutils import Vector

sys.path.insert(0, os.path.expanduser("~/godwyn-boss-fight/scripts"))
import lib_godwyn as G

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_phase1.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
print("[skincheck] GPU:", G.enable_gpu())

# skin -> screaming red emission (force-assigned to the body's slots)
red = bpy.data.materials.new("SC_Red")
red.use_nodes = True
nt = red.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
em = nt.nodes.new("ShaderNodeBsdfDiffuse")
em.inputs[0].default_value = (1, 0, 0, 1)   # matte red: no emission bleed
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(em.outputs[0], out.inputs[0])
body = bpy.data.objects["Godwyn_Body"]
body.data.materials.clear()
body.data.materials.append(red)

# hide cape + hair (they legally cover skin; we want worst-case)
for name in ("Godwyn_Cape", "Godwyn_Hair"):
    if name in bpy.data.objects:
        bpy.data.objects[name].hide_render = True

scene = bpy.context.scene
li = bpy.data.lights.new("SC_Key", "SUN")
li.energy = 3.0
ob = bpy.data.objects.new("SC_Key", li)
ob.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(ob)
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.15, 0.15, 0.17, 1.0)
bg.inputs[1].default_value = 1.0

cam_data = bpy.data.cameras.new("SC_Cam")
cam_data.lens = 70
cam_data.clip_end = 100
cam = bpy.data.objects.new("SC_Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

def aim(t):
    d = Vector(t) - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

shots = [
    ("front", (0.0, -7.5, 1.65), (0, 0, 1.60)),
    ("back",  (0.0, 7.8, 1.75),  (0, 0.2, 1.60)),
    ("right", (7.5, 0.2, 1.7),   (0, 0.1, 1.60)),
    ("upfront", (0.9, -3.4, 2.5), (0, 0.10, 2.35)),
    ("lowback", (1.4, 4.4, 0.9),  (0, 0.15, 1.00)),
    ("armpitR", (2.4, -2.4, 2.35), (0.42, 0.12, 2.42)),
    ("armpitRb", (2.6, 2.4, 2.5), (0.42, 0.28, 2.42)),
    ("elbowR", (2.3, -1.9, 1.95), (0.76, 0.10, 2.18)),
    ("crotch", (0.9, -2.9, 1.30), (0.0, 0.05, 1.42)),
]
for name, loc, tgt in shots:
    cam.location = loc
    aim(tgt)
    G.configure_cycles(scene, samples=24, resolution_x=800,
                       resolution_y=1100 if name in ("front", "back", "right")
                       else 800, use_denoiser=True)
    assert scene.cycles.device == "GPU"
    out_p = f"/tmp/skincheck_{name}.png"
    G.render_to_path(out_p, scene)
    print("[skincheck] wrote", out_p, os.path.getsize(out_p))
print("[skincheck] done")
