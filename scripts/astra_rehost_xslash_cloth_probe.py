"""Quarter-frame deformed-geometry cloth/floor audit for rehosted X-slash."""
import bpy
import json
import numpy as np
import sys
from collections import defaultdict
from pathlib import Path


args = sys.argv[sys.argv.index("--") + 1:]
model, destination = Path(args[0]), Path(args[1])
bpy.ops.wm.open_mainfile(filepath=str(model))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
stage = next(obj for obj in scene.objects if obj.name in {"Astra_Move_Stage", "Astra_Stage"})
floor_z = max(float((stage.matrix_world @ vertex.co).z) for vertex in stage.data.vertices)
end = int(round(rig.animation_data.action.frame_range[1]))

group_names = {group.index: group.name for group in body.vertex_groups}
families = defaultdict(list)
for bone in rig.pose.bones:
    if bone.name.startswith(("phys_robe", "phys_cape")):
        families[bone.name.rsplit("_", 1)[0]].append(bone.name)
families = {name: sorted(bones) for name, bones in families.items()}

# The modeled blue woven surface includes the arm-bound undersleeves.  Robe and
# cape ownership follows the same >0.55 per-family rule used by the delivered
# surface audit, with each vertex assigned to its strongest secondary family.
blue_slots = {index for index, slot in enumerate(body.material_slots)
              if slot.material and ("royal blue" in slot.material.name.lower()
                                    or "woven silk" in slot.material.name.lower())}
blue_vertices = set()
for polygon in body.data.polygons:
    if polygon.material_index in blue_slots:
        blue_vertices.update(polygon.vertices)

family_vertices = defaultdict(list)
component_vertices = {"robe_hem": [], "cape": [], "undersleeves": []}
vertex_owner = {}
arm_groups = {side + part for side in ("Left", "Right")
              for part in ("Arm", "ForeArm", "Hand")}
for vertex in body.data.vertices:
    rest_world_z = float((body.matrix_world @ vertex.co).z)
    weights = defaultdict(float)
    arm_weight = 0.0
    for membership in vertex.groups:
        group_name = group_names[membership.group]
        family = group_name.rsplit("_", 1)[0]
        if family in families:
            weights[family] += float(membership.weight)
        if group_name in arm_groups:
            arm_weight += float(membership.weight)
    if weights and rest_world_z <= 0.4:
        family, weight = max(weights.items(), key=lambda item: item[1])
        if weight > 0.55:
            component = "cape" if family.startswith("phys_cape") else "robe_hem"
            family_vertices[family].append(vertex.index)
            component_vertices[component].append(vertex.index)
            vertex_owner[vertex.index] = {"component": component, "family": family,
                                          "family_weight": weight}
            continue
    if vertex.index in blue_vertices and arm_weight > 0.55:
        component_vertices["undersleeves"].append(vertex.index)
        vertex_owner[vertex.index] = {"component": "undersleeves", "family": None,
                                      "family_weight": arm_weight}

family_vertices = {name: indices for name, indices in sorted(family_vertices.items())
                   if len(indices) > 10}
for name in list(vertex_owner):
    owner = vertex_owner[name]
    if owner["family"] is not None and owner["family"] not in family_vertices:
        component_vertices[owner["component"]].remove(name)
        del vertex_owner[name]
all_ids = np.asarray(sorted(vertex_owner), dtype=np.int32)
component_arrays = {name: np.asarray(sorted(set(indices) & set(vertex_owner)), dtype=np.int32)
                    for name, indices in component_vertices.items()}
family_arrays = {name: np.asarray(indices, dtype=np.int32)
                 for name, indices in family_vertices.items()}
assert len(all_ids) and all(len(ids) for ids in component_arrays.values())


def evaluated_world_coordinates():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coordinates)
    coordinates = coordinates.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coordinates = coordinates @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coordinates


rows = []
events = []
penetrating_by_component = defaultdict(set)
penetrating_by_family = defaultdict(set)
for quarter_index in range(4, 4 * end + 1):
    frame = quarter_index / 4.0
    scene.frame_set(int(frame), subframe=frame % 1.0)
    bpy.context.view_layer.update()
    coordinates = evaluated_world_coordinates()
    component_minima = {}
    family_minima = {}
    for component, indices in component_arrays.items():
        clearance = coordinates[indices, 2] - floor_z
        component_minima[component] = float(clearance.min())
        local = np.flatnonzero(clearance < 0.0)
        if len(local):
            penetrating_by_component[component].update(int(indices[i]) for i in local)
            if component == "undersleeves":
                vertex_ids = [int(indices[i]) for i in local]
                events.append({
                    "frame": frame,
                    "component": component,
                    "family": None,
                    "vertex_count": len(vertex_ids),
                    "vertices": [
                        {
                            "index": vertex_id,
                            "clearance_m": float(coordinates[vertex_id, 2] - floor_z),
                            "world_coordinate_m": [float(value) for value in coordinates[vertex_id]],
                            "family_weight": vertex_owner[vertex_id]["family_weight"],
                        }
                        for vertex_id in vertex_ids
                    ],
                })
    for family, indices in family_arrays.items():
        clearance = coordinates[indices, 2] - floor_z
        family_minima[family] = float(clearance.min())
        local = np.flatnonzero(clearance < 0.0)
        if not len(local):
            continue
        vertex_ids = [int(indices[i]) for i in local]
        penetrating_by_family[family].update(vertex_ids)
        events.append({
            "frame": frame,
            "component": "cape" if family.startswith("phys_cape") else "robe_hem",
            "family": family,
            "vertex_count": len(vertex_ids),
            "vertices": [
                {
                    "index": vertex_id,
                    "clearance_m": float(coordinates[vertex_id, 2] - floor_z),
                    "world_coordinate_m": [float(value) for value in coordinates[vertex_id]],
                    "family_weight": vertex_owner[vertex_id]["family_weight"],
                }
                for vertex_id in vertex_ids
            ],
        })
    all_clearance = coordinates[all_ids, 2] - floor_z
    minimum_local = int(np.argmin(all_clearance))
    minimum_vertex = int(all_ids[minimum_local])
    rows.append({
        "frame": frame,
        "minimum_clearance_m": float(all_clearance[minimum_local]),
        "minimum_vertex": minimum_vertex,
        "minimum_component": vertex_owner[minimum_vertex]["component"],
        "minimum_family": vertex_owner[minimum_vertex]["family"],
        "component_minimum_clearance_m": component_minima,
        "family_minimum_clearance_m": family_minima,
    })
    if quarter_index % 20 == 0:
        print("XSLASH CLOTH PROBE", destination.name, frame,
              f"min={rows[-1]['minimum_clearance_m']:.9f}", flush=True)

worst = min(rows, key=lambda row: row["minimum_clearance_m"])
worst_three = sorted(rows, key=lambda row: row["minimum_clearance_m"])[:3]
result = {
    "model": str(model),
    "action": rig.animation_data.action.name,
    "frame_range": [1, end],
    "sample_step_frames": 0.25,
    "samples": len(rows),
    "floor_z_m": floor_z,
    "selection_method": {
        "robe_cape": "rest world Z <= 0.4 m and strongest phys_robe/phys_cape family weight > 0.55; disjoint strongest-family assignment",
        "undersleeves": "blue/woven material adjacency and combined Arm/ForeArm/Hand weight > 0.55; no secondary sleeve chain exists",
        "coordinates": "evaluated char1 mesh in world space at every quarter frame",
    },
    "vertex_counts": {
        "all_cloth": len(all_ids),
        "components": {name: len(indices) for name, indices in component_arrays.items()},
        "families": {name: len(indices) for name, indices in family_arrays.items()},
    },
    "minimum_clearance_m": worst["minimum_clearance_m"],
    "worst_frame": worst["frame"],
    "worst_vertex": worst["minimum_vertex"],
    "worst_component": worst["minimum_component"],
    "worst_family": worst["minimum_family"],
    "three_worst_samples": worst_three,
    "penetrating_frames": sorted({event["frame"] for event in events}),
    "penetrating_vertices": {
        "components": {name: sorted(indices) for name, indices in penetrating_by_component.items()},
        "families": {name: sorted(indices) for name, indices in penetrating_by_family.items()},
    },
    "penetration_events": events,
    "rows": rows,
}
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(result, indent=2) + "\n")
print("XSLASH CLOTH PROBE COMPLETE", json.dumps({
    "destination": str(destination),
    "minimum_clearance_m": result["minimum_clearance_m"],
    "worst_frame": result["worst_frame"],
    "worst_vertex": result["worst_vertex"],
    "worst_component": result["worst_component"],
    "worst_family": result["worst_family"],
    "penetrating_frames": result["penetrating_frames"],
    "penetrating_vertex_counts": {
        name: len(indices) for name, indices in result["penetrating_vertices"]["components"].items()
    },
}), flush=True)
