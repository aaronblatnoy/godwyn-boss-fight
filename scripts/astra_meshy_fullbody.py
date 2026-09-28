"""Full-body Cycles OptiX portraits of the published character."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT/"renders/astra/char2"
bpy.ops.wm.open_mainfile(filepath=str(ROOT / (sys.argv[sys.argv.index("--")+1] if "--" in sys.argv else "models/astra_character_v2.blend")))
s = bpy.context.scene
s.render.engine = "CYCLES"; s.cycles.samples = 96; s.cycles.use_denoising = True
p = bpy.context.preferences.addons["cycles"].preferences; p.compute_device_type = "OPTIX"; p.get_devices()
for d in p.devices: d.use = d.type == "OPTIX"
assert any(d.use for d in p.devices); s.cycles.device = "GPU"
s.render.resolution_x, s.render.resolution_y = 1200, 1800; s.render.resolution_percentage = 100
s.render.film_transparent = False
w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.01, 0.012, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1
meshes = [o for o in s.objects if o.type == "MESH" and not o.hide_render and "ground" not in o.name.lower() and "stage" not in o.name.lower()]
lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
for o in meshes:
    for c in o.bound_box:
        v = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, v)); hi = Vector(map(max, hi, v))
ctr = (lo+hi)/2; h = hi.z - lo.z
print("BOUNDS", tuple(round(x,2) for x in lo), tuple(round(x,2) for x in hi))
def light(name, loc, energy, color=(1,0.92,0.7), size=2.5):
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.color = color; L.size = size
    o = bpy.data.objects.new(name, L); s.collection.objects.link(o); o.location = loc
    o.rotation_euler = (ctr - o.location).to_track_quat("-Z", "Y").to_euler(); return o
light("KeyFB", ctr + Vector((-2.5, -3.5, 2.2)), 4000)
light("FillFB", ctr + Vector((3.0, -3.0, 0.5)), 1200, (0.8, 0.85, 1.0), 4)
light("RimFB", ctr + Vector((1.5, 3.5, 2.5)), 2500, (1, 0.9, 0.6))
cam = bpy.data.cameras.new("CamFB"); cam.lens = 70; co = bpy.data.objects.new("CamFB", cam); s.collection.objects.link(co); s.camera = co
for name, dirv in [("front", Vector((0, -1, 0))), ("three_quarter", Vector((0.75, -0.75, 0))), ("side", Vector((1, 0, 0)))]:
    co.location = ctr + dirv.normalized() * h * 2.05
    co.rotation_euler = (ctr - co.location).to_track_quat("-Z", "Y").to_euler()
    s.render.filepath = str(OUT/f"{(sys.argv[sys.argv.index("--")+2] if "--" in sys.argv and len(sys.argv)>sys.argv.index("--")+2 else "fullbody")}_{name}.png"); bpy.ops.render.render(write_still=True); print("FULLBODY_PASS", name, flush=True)
