"""Inspect the saved I03 body before the I04 topological split (black-sky only)."""
import bpy
import json
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/astra_character_v2_body_i03.blend"
OUT = ROOT / "renders/astra/char2/meshy_body_i04_probe.json"


def vertex_weights(obj, index):
    names = {group.index: group.name for group in obj.vertex_groups}
    return {names[item.group]: float(item.weight) for item in obj.data.vertices[index].groups
            if item.weight > 1e-8}


def face_components(mesh, face_ids):
    face_ids = set(face_ids)
    edge_faces = defaultdict(list)
    for face_id in face_ids:
        vertices = list(mesh.polygons[face_id].vertices)
        for slot, a in enumerate(vertices):
            edge_faces[tuple(sorted((a, vertices[(slot + 1) % len(vertices)])))].append(face_id)
    adjacency = defaultdict(set)
    for faces in edge_faces.values():
        for a in faces:
            adjacency[a].update(value for value in faces if value != a)
    unseen = set(face_ids)
    components = []
    while unseen:
        root = unseen.pop()
        component = {root}
        queue = deque([root])
        while queue:
            current = queue.popleft()
            found = adjacency[current] & unseen
            unseen.difference_update(found)
            component.update(found)
            queue.extend(found)
        components.append(component)
    return components


def component_row(body, faces, component_id):
    vertex_ids = sorted({index for face_id in faces for index in body.data.polygons[face_id].vertices})
    world = [body.matrix_world @ body.data.vertices[index].co for index in vertex_ids]
    totals = defaultdict(float)
    for index in vertex_ids:
        for name, weight in vertex_weights(body, index).items():
            totals[name] += weight
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return {
        "component": component_id,
        "faces": len(faces),
        "vertices": len(vertex_ids),
        "bounds_world_m": {
            "min": [min(point[axis] for point in world) for axis in range(3)],
            "max": [max(point[axis] for point in world) for axis in range(3)],
        },
        "centroid_world_m": [sum(point[axis] for point in world) / len(world) for axis in range(3)],
        "summed_i03_heat_weights_top8": ordered[:8],
    }


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    body = bpy.data.objects["char1"]
    rig = bpy.data.objects["Armature"]
    mesh = body.data
    plate_attribute = mesh.attributes["astra_body_plate"]
    plate_faces = [poly.index for poly in mesh.polygons if plate_attribute.data[poly.index].value]
    nonplate_faces = [poly.index for poly in mesh.polygons if not plate_attribute.data[poly.index].value]
    plate_components = face_components(mesh, plate_faces)
    nonplate_components = face_components(mesh, nonplate_faces)
    plate_rows = [component_row(body, faces, index)
                  for index, faces in enumerate(plate_components)]
    plate_rows.sort(key=lambda row: row["vertices"], reverse=True)
    nonplate_rows = [component_row(body, faces, index)
                     for index, faces in enumerate(nonplate_components)]
    nonplate_rows.sort(key=lambda row: row["vertices"], reverse=True)
    materials = []
    for material in mesh.materials:
        nodes = []
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                row = {"name": node.name, "type": node.bl_idname, "label": node.label}
                if hasattr(node, "image") and node.image:
                    row["image"] = node.image.name
                    row["image_size"] = list(node.image.size)
                    row["image_filepath"] = node.image.filepath
                    row["image_packed"] = node.image.packed_file is not None
                nodes.append(row)
        materials.append({"name": material.name if material else None, "nodes": nodes})
    payload = {
        "source": str(SOURCE.relative_to(ROOT)),
        "body": {"vertices": len(mesh.vertices), "edges": len(mesh.edges),
                 "faces": len(mesh.polygons), "materials": materials,
                 "uv_layers": [layer.name for layer in mesh.uv_layers],
                 "attributes": [{"name": item.name, "domain": item.domain,
                                 "data_type": item.data_type, "length": len(item.data)}
                                for item in mesh.attributes],
                 "custom_properties": {key: body[key] for key in body.keys()},
                 "vertex_groups": list(body.vertex_groups.keys())},
        "rig_bones": len(rig.data.bones),
        "plate_faces": len(plate_faces),
        "nonplate_faces": len(nonplate_faces),
        "plate_component_count": len(plate_rows),
        "plate_components": plate_rows,
        "nonplate_component_count": len(nonplate_rows),
        "nonplate_components_top20": nonplate_rows[:20],
        "bones_world": {name: list(rig.matrix_world @ rig.data.bones[name].head_local)
                        for name in ["Hips", "Spine02", "Spine01", "Spine",
                                     "LeftUpLeg", "RightUpLeg"]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print("BODY_I04_PROBE", json.dumps({
        "plate_components": len(plate_rows),
        "plate_small_lt30": sum(row["vertices"] < 30 for row in plate_rows),
        "plate_vertices_largest": [row["vertices"] for row in plate_rows[:20]],
        "nonplate_components": len(nonplate_rows),
        "attributes": [item.name for item in mesh.attributes],
    }), flush=True)


if __name__ == "__main__":
    main()
