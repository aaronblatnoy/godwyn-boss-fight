"""Render object-ID colors to diagnose the head/neck seam."""

from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import astra_v3_render as render


BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_semantic_collar.png"


def emission(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeEmission")
    shader.inputs["Color"].default_value = (*color, 1.0)
    shader.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(shader.outputs["Emission"], output.inputs["Surface"])
    return material


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    scene = bpy.context.scene
    rig = bpy.data.objects["Astra_V3_Rig"]
    colors = {
        "char1": (0.85, 0.03, 0.03),
        "AstraChar2_Meshy_HeadHair": (0.03, 0.80, 0.08),
        "AstraChar2_Meshy_NeckBlend": (0.04, 0.20, 0.95),
        "Astra_V3_SeamSleeve": (0.95, 0.03, 0.80),
        "Godwyn_Sword": (0.95, 0.55, 0.03),
    }
    for name, color in colors.items():
        obj = bpy.data.objects.get(name)
        if not obj or obj.type != "MESH":
            continue
        obj.data.materials.clear()
        obj.data.materials.append(emission(f"V3 semantic {name}", color))
        for poly in obj.data.polygons:
            poly.material_index = 0
    camera = render.studio(scene)
    render.assign_action(rig, "idle_guard", 1)
    render.configure_common(scene, 600, 900)
    render.configure_cycles(scene, 8)
    collar = Vector((0.0, -0.24, 2.69))
    render.set_camera(camera, Vector((collar.x, collar.y - 4.0, collar.z)), collar, 0.72)
    render.render_one(scene, OUT)
    print("V3_SEMANTIC_PREVIEW_PASS", OUT, flush=True)


if __name__ == "__main__":
    main()
