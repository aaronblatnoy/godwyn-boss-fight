"""Fast EEVEE full-body review renders for segmentation iterations on black-sky."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
args = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / args[0]))
prefix = args[1] if len(args) > 1 else "meshy_body_preview"
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 768, 1152
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = scene.world or bpy.data.worlds.new("Astra body preview world")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.01, 0.015, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render
          and "ground" not in obj.name.lower() and "stage" not in obj.name.lower()]
lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for obj in meshes:
    for corner in obj.bound_box:
        point = obj.matrix_world @ Vector(corner)
        lo = Vector((min(lo[i], point[i]) for i in range(3)))
        hi = Vector((max(hi[i], point[i]) for i in range(3)))
center = (lo + hi) * 0.5
height = hi.z - lo.z
for name, offset, energy, color, size in [
    ("Body preview key", Vector((-2.5, -3.5, 2.2)), 3000, (1.0, 0.9, 0.7), 2.5),
    ("Body preview fill", Vector((3.0, -3.0, 0.5)), 1100, (0.8, 0.85, 1.0), 4.0),
    ("Body preview rim", Vector((1.5, 3.5, 2.5)), 2200, (1.0, 0.9, 0.6), 2.5),
]:
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color, data.size = energy, color, size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = center + offset
    obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
camera_data = bpy.data.cameras.new("Body preview camera")
camera_data.lens = 70
camera = bpy.data.objects.new("Body preview camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
for label, direction in (("front", Vector((0, -1, 0))), ("side", Vector((1, 0, 0))),
                         ("three_quarter", Vector((0.75, -0.75, 0)))):
    camera.location = center + direction.normalized() * height * 2.05
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{prefix}_{label}.png")
    bpy.ops.render.render(write_still=True)
    print("BODY_PREVIEW", label, flush=True)
