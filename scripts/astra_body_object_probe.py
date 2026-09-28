"""Isolate evaluated body and published head/hair geometry in quick evidence renders."""
import bpy
import json
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/astra_character_v2_body_i01.blend"
OUT = ROOT / "renders/astra/char2"


def evaluated_bounds(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return {"min": coords.min(axis=0).tolist(), "max": coords.max(axis=0).tolist(),
            "extent": np.ptp(coords, axis=0).tolist(), "vertices": len(coords)}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(MODEL))
    scene = bpy.context.scene
    targets = [bpy.data.objects["char1"], bpy.data.objects["AstraChar2_Meshy_HeadHair"],
               bpy.data.objects["AstraChar2_Meshy_NeckBlend"]]
    report = {obj.name: evaluated_bounds(obj) for obj in targets}
    (OUT / "meshy_body_object_probe.json").write_text(json.dumps(report, indent=2) + "\n")
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 768, 1152
    scene.render.resolution_percentage = 100
    world = scene.world or bpy.data.worlds.new("Body object probe world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.01, 0.015, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    center = Vector((0, -0.16, 1.58))
    for name, location, energy in (("Probe Key", (-2.5, -3.6, 3.8), 3000),
                                   ("Probe Fill", (3.0, -3.0, 2.0), 1200),
                                   ("Probe Rim", (1.5, 3.5, 4.0), 2200)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.size = energy, 3.0
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Object probe camera")
    camera_data.lens = 70
    camera = bpy.data.objects.new("Object probe camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    character_meshes = [obj for obj in scene.objects if obj.type == "MESH" and obj.name != "Astra evaluation ground"]
    for target in targets[:2]:
        for obj in character_meshes:
            obj.hide_render = obj != target
        for label, direction in (("front", Vector((0, -1, 0))), ("side", Vector((1, 0, 0)))):
            camera.location = center + direction * 6.5
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str(OUT / f"meshy_body_probe_{target.name}_{label}.png")
            bpy.ops.render.render(write_still=True)
    print("BODY_OBJECT_PROBE", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
