"""Record the published rig/body donor landmarks used by the Meshy body fit."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/astra_character_v2_meshy_i03_defrag.blend"
OUT = ROOT / "renders/astra/char2/meshy_body_rig_probe.json"


def bounds(obj):
    if obj.type != "MESH" or not obj.data.vertices:
        return None
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    lo = [min(p[k] for p in points) for k in range(3)]
    hi = [max(p[k] for p in points) for k in range(3)]
    return {"min": lo, "max": hi, "extent": [hi[k] - lo[k] for k in range(3)]}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    rig_world = rig.matrix_world
    bones = {}
    for bone in rig.data.bones:
        bones[bone.name] = {
            "head_world": list(rig_world @ bone.head_local),
            "tail_world": list(rig_world @ bone.tail_local),
            "parent": bone.parent.name if bone.parent else None,
            "use_deform": bone.use_deform,
        }
    objects = {}
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        row = {
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "bounds": bounds(obj),
            "hidden_render": obj.hide_render,
            "materials": [material.name if material else None for material in obj.data.materials],
            "vertex_groups": [group.name for group in obj.vertex_groups],
            "armature_modifiers": [modifier.object.name if modifier.object else None
                                   for modifier in obj.modifiers if modifier.type == "ARMATURE"],
        }
        objects[obj.name] = row
    body = bpy.data.objects["char1"]
    groups = {group.index: group.name for group in body.vertex_groups}
    group_counts = {name: 0 for name in groups.values()}
    for vertex in body.data.vertices:
        for membership in vertex.groups:
            if membership.weight > 1e-8:
                group_counts[groups[membership.group]] += 1
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "blender_version": bpy.app.version_string,
        "bones": bones,
        "bone_count": len(bones),
        "actions": len(bpy.data.actions),
        "rig_matrix_world": [list(row) for row in rig.matrix_world],
        "objects": objects,
        "char1_group_nonzero_vertex_counts": group_counts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("RIG_PROBE", json.dumps({"bones": len(bones), "actions": len(bpy.data.actions),
                                   "objects": len(objects), "char1": objects["char1"]}), flush=True)


if __name__ == "__main__":
    main()
