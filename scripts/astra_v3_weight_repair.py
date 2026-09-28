"""Repair only pathological auto-rig seam edges while preserving v3 topology."""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
WIP = ROOT / "models/astra_character_v3_wip.blend"
EXTENDED = {"idle_guard": 48, "walk_stalk": 36, "lunge_thrust": 40, "rising_spin": 40, "xslash": 55}
PROTECTED = [ROOT / "models/astra_character_v2.blend", ROOT / "models/astra_character_v2.glb"]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default=str(WIP.relative_to(ROOT)))
    parser.add_argument("--threshold", type=float, default=2.80)
    parser.add_argument("--iterations", type=int, default=6)
    parser.add_argument("--finalize", action="store_true")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def assign_action(rig, name, frame):
    action = bpy.data.actions[f"Godwyn_V3_{name}"]
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def evaluated_coordinates(ob):
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", values)
    values = values.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    values = values @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return values


def rest_edges(body):
    rest = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", rest)
    rest = rest.reshape(-1, 3)
    matrix = np.asarray(body.matrix_world)
    rest = rest @ matrix[:3, :3].T + matrix[:3, 3]
    edges = np.empty(len(body.data.edges) * 2, dtype=np.int32)
    body.data.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    return edges, lengths


def scan(rig, body, edges, lengths, threshold):
    valid = lengths > 1e-6
    bad = set()
    rows = {}
    for name, frame in EXTENDED.items():
        assign_action(rig, name, frame)
        posed = evaluated_coordinates(body)
        posed_lengths = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
        ratios = np.zeros_like(lengths)
        ratios[valid] = posed_lengths[valid] / lengths[valid]
        slots = np.flatnonzero(ratios > threshold)
        bad.update(int(index) for index in slots)
        maximum = int(np.argmax(ratios))
        rows[name] = {
            "frame": frame,
            "p99": float(np.percentile(ratios[valid], 99)),
            "max": float(ratios[maximum]),
            "edges_above_threshold": int(len(slots)),
            "maximum_edge": maximum,
            "maximum_edge_vertices": [int(value) for value in edges[maximum]],
            "maximum_rest_length_m": float(lengths[maximum]),
            "maximum_posed_length_m": float(posed_lengths[maximum]),
        }
    return bad, rows


def components_from_edges(edges, bad_indices):
    parent = {}

    def find(value):
        parent.setdefault(value, value)
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a, b):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra

    for index in bad_indices:
        union(*edges[index])
    result = defaultdict(list)
    for vertex in parent:
        result[find(vertex)].append(vertex)
    return list(result.values())


def vertex_weights(body, index, names):
    return {names[item.group]: float(item.weight) for item in body.data.vertices[index].groups if item.weight > 1e-8}


def weights_snapshot(body):
    names = {group.index: group.name for group in body.vertex_groups}
    return [vertex_weights(body, index, names) for index in range(len(body.data.vertices))]


def assign_weights(body, index, weights):
    strongest = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4]
    total = sum(value for _name, value in strongest)
    final = {name: value / total for name, value in strongest if value > 1e-8}
    for group in body.vertex_groups:
        try:
            group.remove([index])
        except RuntimeError:
            pass
    for name, value in final.items():
        body.vertex_groups[name].add([index], value, "REPLACE")


def adjacency_from_edges(edges, vertex_count):
    adjacency = [set() for _ in range(vertex_count)]
    for a, b in edges:
        adjacency[int(a)].add(int(b))
        adjacency[int(b)].add(int(a))
    return adjacency


def smooth_bad_edges(body, edges, bad_indices, adjacency, rings=2, passes=2):
    region = {int(vertex) for index in bad_indices for vertex in edges[index]}
    for _ring in range(rings):
        region.update(neighbor for vertex in list(region) for neighbor in adjacency[vertex])
    for _pass in range(passes):
        snapshot = weights_snapshot(body)
        updates = {}
        for vertex in region:
            neighbors = adjacency[vertex]
            if not neighbors:
                continue
            totals = defaultdict(float)
            # Retain one quarter of the current value and diffuse three
            # quarters from the one-ring neighborhood.
            for name, value in snapshot[vertex].items():
                totals[name] += 0.25 * value
            scale = 0.75 / len(neighbors)
            for neighbor in neighbors:
                for name, value in snapshot[neighbor].items():
                    totals[name] += scale * value
            updates[vertex] = totals
        for vertex, weights in updates.items():
            assign_weights(body, vertex, weights)
    return region


def equalize_components(body, components):
    snapshot = weights_snapshot(body)
    changed = set()
    for component in components:
        totals = defaultdict(float)
        for vertex in component:
            for name, value in snapshot[vertex].items():
                totals[name] += value / len(component)
        for vertex in component:
            assign_weights(body, vertex, totals)
            changed.add(vertex)
    return changed


def main():
    args = cli()
    blend = root_path(args.blend)
    protected_before = {str(path.relative_to(ROOT)): sha256(path) for path in PROTECTED}
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    edges, lengths = rest_edges(body)
    adjacency = adjacency_from_edges(edges, len(body.data.vertices))
    iterations = []
    all_changed = set()
    for iteration in range(1, args.iterations + 1):
        bad, before = scan(rig, body, edges, lengths, args.threshold)
        if not bad:
            iterations.append({"iteration": iteration, "before": before, "bad_edges": 0, "components": []})
            break
        components = components_from_edges(edges, bad)
        maximum_component = max(len(component) for component in components)
        assert maximum_component <= 2048, f"repair component unexpectedly broad: {maximum_component} vertices"
        changed = (equalize_components(body, components) if args.finalize
                   else smooth_bad_edges(body, edges, bad, adjacency, rings=2, passes=2))
        all_changed.update(changed)
        iterations.append({
            "iteration": iteration,
            "before": before,
            "bad_edges": len(bad),
            "components": [{"vertices": len(component), "vertex_examples": component[:20]} for component in components],
            "changed_vertices": len(changed),
            "maximum_component_vertices": maximum_component,
        })
        print("V3_WEIGHT_REPAIR", iteration, "edges", len(bad), "components", len(components), "vertices", len(changed), flush=True)
    remaining, final = scan(rig, body, edges, lengths, 3.0)
    report = {
        "schema": "astra-v3-pathological-edge-weight-repair",
        "method": (
            "final exact equalization of connected remaining over-gate edge endpoints"
            if args.finalize else
            "two simultaneous 25/75 self/neighbor Laplacian passes across affected vertices plus two edge rings"
        ) + "; retain top-four normalized weights; topology and vertex positions unchanged",
        "blend": str(blend.relative_to(ROOT)),
        "threshold_used": args.threshold,
        "iterations": iterations,
        "unique_vertices_changed": len(all_changed),
        "body_vertices": len(body.data.vertices),
        "fraction_vertices_changed": len(all_changed) / len(body.data.vertices),
        "final": final,
        "remaining_edges_above_3": len(remaining),
        "gate_pass": not remaining and all(row["p99"] <= 1.6 and row["max"] <= 3.0 for row in final.values()),
    }
    (OUT / "meshy_v3_weight_repair.json").write_text(json.dumps(report, indent=2) + "\n")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    protected_after = {str(path.relative_to(ROOT)): sha256(path) for path in PROTECTED}
    assert protected_before == protected_after
    print("V3_WEIGHT_REPAIR_COMPLETE", json.dumps({
        "changed": report["unique_vertices_changed"],
        "fraction": report["fraction_vertices_changed"],
        "remaining": report["remaining_edges_above_3"],
        "gate": report["gate_pass"],
    }), flush=True)
    if not report["gate_pass"]:
        raise RuntimeError("edge-stretch repair did not converge")


if __name__ == "__main__":
    main()
