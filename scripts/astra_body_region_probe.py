"""Color the candidate body by Y bands to localize residual source hair."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "models/astra_character_v2_body_i01.blend"))
scene = bpy.context.scene
body = bpy.data.objects["char1"]
for obj in scene.objects:
    if obj.type == "MESH":
        obj.hide_render = obj != body
colors = [(1.0, 0.02, 0.02, 1), (0.02, 1.0, 0.02, 1),
          (0.02, 0.12, 1.0, 1), (1.0, 0.8, 0.02, 1)]
for index, color in enumerate(colors):
    material = bpy.data.materials.new(f"Body Y band {index}")
    material.diffuse_color = color
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = 0.35
    bsdf.inputs["Roughness"].default_value = 1.0
    body.data.materials.append(material)
for polygon in body.data.polygons:
    y = polygon.center.y
    polygon.material_index = 1 + (0 if y < -0.30 else 1 if y < 0.0 else 2 if y < 0.30 else 3)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 768, 1152
scene.render.resolution_percentage = 100
world = scene.world or bpy.data.worlds.new("Body region world")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.005, 0.005, 0.008, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.4
camera_data = bpy.data.cameras.new("Body region camera")
camera_data.lens = 70
camera = bpy.data.objects.new("Body region camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
center = Vector((0, -0.16, 1.58))
for label, direction in (("front", Vector((0, -1, 0))), ("side", Vector((1, 0, 0)))):
    camera.location = center + direction * 6.5
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"meshy_body_ybands_{label}.png")
    bpy.ops.render.render(write_still=True)
print("BODY_REGION_PROBE_PASS", flush=True)
