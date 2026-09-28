"""Replace the failed broad liners with boundary-conforming gap patches."""

import json
from collections import defaultdict, deque
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_round2_wip.blend"
REPORT = ROOT / "renders/astra/char2/astra_v3m_round2_build.json"


def boundary_components(body):
    representative = {}
    canonical = {}
    members = defaultdict(set)
    for vertex in body.data.vertices:
        key = tuple(round(float(value), 4) for value in vertex.co)
        rep = representative.setdefault(key, vertex.index)
        canonical[vertex.index] = rep
        members[rep].add(vertex.index)

    edge_count = defaultdict(int)
    for polygon in body.data.polygons:
        vertices = list(polygon.vertices)
        for index, first in enumerate(vertices):
            a = canonical[first]
            b = canonical[vertices[(index + 1) % len(vertices)]]
            if a != b:
                edge_count[tuple(sorted((a, b)))] += 1

    adjacency = defaultdict(set)
    for (a, b), count in edge_count.items():
        if count == 1:
            adjacency[a].add(b)
            adjacency[b].add(a)

    unseen = set(adjacency)
    components = []
    while unseen:
        seed = unseen.pop()
        unseen_component = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    unseen_component.add(other)
                    queue.append(other)
        components.append(unseen_component)
    return components, adjacency, members


def cycle_loops(component, adjacency):
    """Partition an even-degree welded boundary graph into simple cycles."""
    local = {index: set(adjacency[index]) for index in component}
    start = next(iter(component))
    stack = [start]
    circuit = []
    while stack:
        current = stack[-1]
        if local[current]:
            other = next(iter(local[current]))
            local[current].remove(other)
            local[other].remove(current)
            stack.append(other)
        else:
            circuit.append(stack.pop())
    circuit.reverse()
    if len(circuit) < 4 or circuit[0] != circuit[-1]:
        return []

    def split(walk):
        positions = {}
        for index, vertex in enumerate(walk[:-1]):
            if vertex in positions:
                prior = positions[vertex]
                cycle = walk[prior:index + 1]
                remainder = walk[:prior + 1] + walk[index + 1:]
                return split(cycle) + split(remainder)
            positions[vertex] = index
        return [walk[:-1]] if len(walk) >= 4 else []

    loops = split(circuit)
    edge_total = sum(len(loop) for loop in loops)
    expected_edges = sum(len(adjacency[index]) for index in component) // 2
    assert edge_total == expected_edges, (edge_total, expected_edges)
    return loops


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    for name in (
        "AstraChar2_R2_TorsoOccluder",
        "AstraChar2_R2_HemLiner",
        "AstraChar2_R2_LargeTorsoPatches",
    ):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    body = bpy.data.objects["char1"]
    rig = bpy.data.objects["Astra_V3_Rig"]
    components, adjacency, members = boundary_components(body)

    chosen = []
    diagnostics = []
    for component in components:
        if len(component) <= 100:
            continue
        world_points = [body.matrix_world @ body.data.vertices[index].co for index in component]
        center = sum(world_points, Vector()) / len(world_points)
        degree_counts = defaultdict(int)
        for index in component:
            degree_counts[len(adjacency[index])] += 1
        diagnostics.append({
            "vertices": len(component),
            "center_m": list(center),
            "degree_counts": dict(degree_counts),
        })
        loops = cycle_loops(component, adjacency)
        # The two large rear-upper-torso openings are the visible tears.  Keep
        # this deliberately narrow so the intended neckline/gorget remains open.
        if center.z > 2.55 and center.y < -0.08:
            for loop in loops:
                loop_world = [body.matrix_world @ body.data.vertices[index].co for index in loop]
                loop_center = sum(loop_world, Vector()) / len(loop_world)
                chosen.append((loop, loop_center))

    vertices = []
    faces = []
    source_reps = []
    center_sources = []
    for loop, world_center in chosen:
        start = len(vertices)
        vertices.extend(tuple(body.data.vertices[index].co) for index in loop)
        source_reps.extend(loop)
        # Recess the fan center toward the body's longitudinal center.  The
        # boundary itself remains exact, so the patch cannot change silhouette.
        local_center = body.matrix_world.inverted() @ (world_center + Vector((0.0, 0.018, 0.0)))
        center_index = len(vertices)
        vertices.append(tuple(local_center))
        source_reps.append(None)
        center_sources.append((center_index, loop))
        for index in range(len(loop)):
            faces.append((start + index, start + (index + 1) % len(loop), center_index))

    mesh = bpy.data.meshes.new("AstraChar2_R2_LargeTorsoPatches_Mesh")
    mesh.from_pydata(vertices, [], faces)
    patch = bpy.data.objects.new("AstraChar2_R2_LargeTorsoPatches", mesh)
    bpy.context.scene.collection.objects.link(patch)

    underlayer = bpy.data.materials.get("V3M R2 visible blue underlayer")
    if underlayer is None:
        underlayer = bpy.data.materials.new("V3M R2 visible blue underlayer")
        underlayer.diffuse_color = (0.012, 0.045, 0.20, 1.0)
        underlayer.metallic = 0.18
        underlayer.roughness = 0.46
    mesh.materials.append(underlayer)

    group_names = {group.index: group.name for group in body.vertex_groups}
    group_cache = {}

    def weights_for(representative_index):
        weights = defaultdict(float)
        for old_index in members[representative_index]:
            for assignment in body.data.vertices[old_index].groups:
                name = group_names[assignment.group]
                weights[name] = max(weights[name], assignment.weight)
        total = sum(weights.values()) or 1.0
        return {name: value / total for name, value in weights.items()}

    vertex_weights = {}
    for new_index, representative_index in enumerate(source_reps):
        if representative_index is not None:
            vertex_weights[new_index] = weights_for(representative_index)
    for center_index, loop in center_sources:
        average = defaultdict(float)
        for representative_index in loop:
            for name, value in weights_for(representative_index).items():
                average[name] += value / len(loop)
        total = sum(average.values()) or 1.0
        vertex_weights[center_index] = {name: value / total for name, value in average.items()}
    for vertex_index, weights in vertex_weights.items():
        for name, value in weights.items():
            group = group_cache.get(name)
            if group is None:
                group = patch.vertex_groups.new(name=name)
                group_cache[name] = group
            group.add([vertex_index], value, "REPLACE")

    modifier = patch.modifiers.new("V3M R2 large patch binding", "ARMATURE")
    modifier.object = rig
    patch.parent = rig
    patch.matrix_world = body.matrix_world.copy()
    small_patch = bpy.data.objects.get("AstraChar2_R2_BoundaryPatches")
    if small_patch:
        small_patch.matrix_world = body.matrix_world.copy()

    result = {
        "diagnosis": "two large closed rear-upper-torso boundaries are genuine source-mesh openings",
        "removed_failed_liners": ["AstraChar2_R2_TorsoOccluder", "AstraChar2_R2_HemLiner"],
        "object": patch.name,
        "loops": len(chosen),
        "loop_vertex_counts": [len(loop) for loop, _ in chosen],
        "triangles": len(faces),
        "center_recess_m": 0.018,
        "silhouette_change": "none; all perimeter vertices exactly copy the source boundary",
        "large_component_diagnostics": diagnostics,
        "body_world_scale": list(body.matrix_world.to_scale()),
    }
    report = json.loads(REPORT.read_text())
    report["gap_and_hem_fix"]["large_open_shell_liners"] = {
        "status": "rejected and removed",
        "reason": "broad liners visibly protruded through the costume in hero renders",
    }
    report["gap_and_hem_fix"]["large_boundary_patches"] = result
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("V3M_R2_LARGE_GAP_REPAIR", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
