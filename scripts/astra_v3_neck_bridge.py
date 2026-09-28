"""Add a rigid, bone-parented neck bridge and clean gold seam trim."""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_neck_bridge.json"


def principled(name, base_color, metallic, roughness):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return material


def bone_parent(object_, rig, bone):
    world = object_.matrix_world.copy()
    object_.parent = rig
    object_.parent_type = "BONE"
    object_.parent_bone = bone
    object_.matrix_world = world


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    for name in ("Astra_V3_Rigid_Neck_Bridge", "Astra_V3_Neck_Gorget_Trim"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    skin = principled("Astra V3 Neck Bridge Skin", (0.61, 0.43, 0.25), 0.0, 0.48)
    gold = principled("Astra V3 Gorget Gold", (0.42, 0.22, 0.045), 0.78, 0.33)
    center = (-0.225, -0.127, 2.665)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.092, depth=0.210, end_fill_type="NGON", location=center)
    bridge = bpy.context.object
    bridge.name = "Astra_V3_Rigid_Neck_Bridge"
    bridge.scale.y = 0.82
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bridge.data.materials.append(skin)
    for poly in bridge.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    bone_parent(bridge, rig, "Head")
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD", major_segments=64, minor_segments=16,
        location=(-0.225, -0.127, 2.585), major_radius=0.104, minor_radius=0.014,
    )
    gorget = bpy.context.object
    gorget.name = "Astra_V3_Neck_Gorget_Trim"
    gorget.scale.y = 0.82
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    gorget.data.materials.append(gold)
    for poly in gorget.data.polygons:
        poly.use_smooth = True
    bone_parent(gorget, rig, "Head")
    report = {
        "schema": "astra-v3-neck-bridge",
        "bridge": {"object": bridge.name, "center_m": list(center), "radius_m": 0.092, "depth_m": 0.210, "y_scale": 0.82, "parent_bone": "Head", "material": skin.name},
        "gorget": {"object": gorget.name, "center_m": [-0.225, -0.127, 2.585], "major_radius_m": 0.104, "minor_radius_m": 0.014, "y_scale": 0.82, "parent_bone": "Head", "material": gold.name},
        "design": "closed rigid neck bridge behind armor; metallic torus hides lower join without armature distortion",
    }
    bpy.context.scene["astra_v3_neck_bridge"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_NECK_BRIDGE_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
