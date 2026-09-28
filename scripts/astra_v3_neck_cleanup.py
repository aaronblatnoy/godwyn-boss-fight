"""Finalize the neck seam: trim displaced donor shoulder islands and add a rigid gorget trim."""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_neck_cleanup.json"


def assign_idle(rig):
    action = bpy.data.actions["Godwyn_V3_idle_guard"]
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def trim_head(head):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = head.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    assert len(mesh.polygons) == len(head.data.polygons)
    removed_centers = []
    for poly in head.data.polygons:
        center = evaluated.matrix_world @ mesh.polygons[poly.index].center
        poly.select = center.z < 2.825 and not (-0.345 <= center.x <= -0.105)
        if poly.select:
            removed_centers.append(tuple(center))
    evaluated.to_mesh_clear()
    assert removed_centers
    before = len(head.data.polygons)
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.data.update()
    return before, len(head.data.polygons), removed_centers


def make_gorget(rig, material):
    old = bpy.data.objects.get("Astra_V3_Neck_Gorget_Trim")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD", major_segments=64, minor_segments=16,
        location=(-0.225, -0.127, 2.715), major_radius=0.112, minor_radius=0.016,
    )
    gorget = bpy.context.object
    gorget.name = "Astra_V3_Neck_Gorget_Trim"
    gorget.scale.y = 0.78
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    gorget.data.materials.append(material)
    for poly in gorget.data.polygons:
        poly.use_smooth = True
    world = gorget.matrix_world.copy()
    gorget.parent = rig
    gorget.parent_type = "BONE"
    gorget.parent_bone = "Head"
    gorget.matrix_world = world
    return gorget


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    body = bpy.data.objects["char1"]
    assign_idle(rig)
    before, after, centers = trim_head(head)
    blend = bpy.data.objects.get("AstraChar2_Meshy_NeckBlend")
    removed_blend = blend.name if blend else None
    if blend:
        bpy.data.objects.remove(blend, do_unlink=True)
    gorget = make_gorget(rig, body.data.materials[0])
    xs = [item[0] for item in centers]
    ys = [item[1] for item in centers]
    zs = [item[2] for item in centers]
    report = {
        "schema": "astra-v3-neck-cleanup",
        "head_faces_before": before,
        "head_faces_after": after,
        "removed_head_faces": before - after,
        "trim_rule": "idle evaluated center z < 2.825m outside neck x[-0.345,-0.105]m",
        "trimmed_center_bounds_m": {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
        "removed_displaced_neck_blend": removed_blend,
        "gorget": {
            "object": gorget.name,
            "parent_bone": gorget.parent_bone,
            "center_m": [-0.225, -0.127, 2.715],
            "major_radius_m": 0.112,
            "minor_radius_m": 0.016,
            "y_scale": 0.78,
            "material": body.data.materials[0].name,
        },
    }
    bpy.context.scene["astra_v3_neck_cleanup"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_NECK_CLEANUP_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
