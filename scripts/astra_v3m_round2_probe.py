"""Probe Round 2 head, hair-component, collar, sash, and hem geometry.

Blender/black-sky only.
"""

import json
from collections import defaultdict, deque
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_round2_probe.json"


def reset(rig):
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def world_points(obj):
    return np.asarray([(obj.matrix_world @ vertex.co)[:] for vertex in obj.data.vertices], dtype=float)


def welded_ids(obj, precision=4):
    canonical = {}
    representative = {}
    members = defaultdict(set)
    for vertex in obj.data.vertices:
        key = tuple(round(float(value), precision) for value in vertex.co)
        rep = representative.setdefault(key, vertex.index)
        canonical[vertex.index] = rep
        members[rep].add(vertex.index)
    return canonical, members


def components(obj):
    canonical, members = welded_ids(obj)
    adjacency = defaultdict(set)
    used = set()
    for edge in obj.data.edges:
        a, b = (canonical[index] for index in edge.vertices)
        if a == b:
            continue
        adjacency[a].add(b)
        adjacency[b].add(a)
        used.update((a, b))
    result = []
    unseen = set(used)
    while unseen:
        seed = unseen.pop()
        found = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    found.add(other)
                    queue.append(other)
        result.append(set().union(*(members[index] for index in found)))
    result.sort(key=len, reverse=True)
    return result


def bounds(points, ids):
    selected = points[list(ids)]
    return {
        "vertices": len(ids),
        "min_m": selected.min(axis=0).tolist(),
        "max_m": selected.max(axis=0).tolist(),
        "center_m": selected.mean(axis=0).tolist(),
    }


def boundary_components(obj):
    canonical, _ = welded_ids(obj)
    edge_faces = defaultdict(int)
    for polygon in obj.data.polygons:
        verts = list(polygon.vertices)
        for index, a in enumerate(verts):
            b = verts[(index + 1) % len(verts)]
            a, b = canonical[a], canonical[b]
            if a != b:
                edge_faces[tuple(sorted((a, b)))] += 1
    adjacency = defaultdict(set)
    for (a, b), count in edge_faces.items():
        if count == 1:
            adjacency[a].add(b)
            adjacency[b].add(a)
    unseen = set(adjacency)
    result = []
    while unseen:
        seed = unseen.pop()
        found = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    found.add(other)
                    queue.append(other)
        result.append(found)
    result.sort(key=len, reverse=True)
    return result


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    reset(rig)
    hp = world_points(head)
    bp = world_points(body)

    skin_attr = head.data.color_attributes["meshy_skin_mask"]
    hair_attr = head.data.color_attributes["meshy_hair_mask"]
    skin_ids, hair_ids = set(), set()
    for poly in head.data.polygons:
        skin = float(np.mean([skin_attr.data[index].color[0] for index in poly.loop_indices]))
        hair = float(np.mean([hair_attr.data[index].color[0] for index in poly.loop_indices]))
        if skin >= 0.5:
            skin_ids.update(poly.vertices)
        if hair >= 0.5:
            hair_ids.update(poly.vertices)
    skin_points = hp[list(skin_ids)]
    low, high = skin_points.min(axis=0), skin_points.max(axis=0)
    candidates = skin_points[skin_points[:, 2] >= low[2] + 0.12 * (high[2] - low[2])]
    chin_z = float(np.percentile(candidates[:, 2], 2.0))

    # Find boundary vertices of plate-classified faces.  The front of this model
    # faces -Y; the central high boundary supplies an actual visible front rim,
    # unlike the old stored "lowest rim" value.
    plate_attr = body.data.color_attributes["astra_v3_plate_mask"]
    plate_faces = set()
    edge_plate_count = defaultdict(int)
    for poly in body.data.polygons:
        value = float(np.mean([plate_attr.data[index].color[0] for index in poly.loop_indices]))
        if value < 0.5:
            continue
        plate_faces.add(poly.index)
        verts = list(poly.vertices)
        for index, a in enumerate(verts):
            edge_plate_count[tuple(sorted((a, verts[(index + 1) % len(verts)])))] += 1
    rim_ids = {index for edge, count in edge_plate_count.items() if count == 1 for index in edge}
    rim = bp[list(rim_ids)]
    front = rim[(np.abs(rim[:, 0]) <= 0.34) & (rim[:, 1] <= -0.15) & (rim[:, 2] >= 2.45)]
    assert len(front), "No central front collar rim candidates"
    # Highest boundary points are frequently pauldron edges. Restrict to the
    # central forward strip, then use the upper decile as the visible gorget lip.
    rim_z = float(np.percentile(front[:, 2], 90.0))

    head_components = components(head)
    hair_component_rows = []
    for component in head_components:
        hair_count = len(component & hair_ids)
        if not hair_count:
            continue
        row = bounds(hp, component)
        row["hair_vertices"] = hair_count
        hair_component_rows.append(row)

    holes = []
    for component in boundary_components(body):
        row = bounds(bp, component)
        center = np.asarray(row["center_m"])
        row["region"] = (
            "upper_torso" if center[2] >= 2.2 else
            "belt" if 1.45 <= center[2] < 2.2 else
            "hem" if center[2] <= 0.45 else "other"
        )
        holes.append(row)

    report = {
        "schema": "astra-v3m-round2-probe",
        "blend": str(BLEND.relative_to(ROOT)),
        "chin_underside_z_m": chin_z,
        "front_rim": {
            "selection": "plate-boundary vertices, |x|<=0.34 m, y<=-0.15 m, z>=2.45 m",
            "candidate_vertices": len(front),
            "z_min_m": float(front[:, 2].min()),
            "z_median_m": float(np.median(front[:, 2])),
            "z_90th_m": rim_z,
            "z_max_m": float(front[:, 2].max()),
            "chin_minus_rim90_m": chin_z - rim_z,
        },
        "head_components": hair_component_rows,
        "hair_components_under_40_vertices": sum(row["vertices"] < 40 for row in hair_component_rows),
        "body_boundary_components": holes,
        "body_boundary_region_counts": {
            region: sum(row["region"] == region for row in holes)
            for region in ("upper_torso", "belt", "hem", "other")
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_R2_PROBE", json.dumps({
        "chin": chin_z,
        "rim": report["front_rim"],
        "hair_components": len(hair_component_rows),
        "small_hair": report["hair_components_under_40_vertices"],
        "body_holes": len(holes),
        "hole_regions": report["body_boundary_region_counts"],
    }), flush=True)


if __name__ == "__main__":
    main()
