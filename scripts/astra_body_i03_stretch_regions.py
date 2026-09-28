"""Partition failed i03 stretch by plate-island topology category."""
import bpy
import json
import numpy as np
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/rehost_body_i03/meshy_body_i03_stretch_regions.json"
MODELS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_body_i03.blend", 48),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_body_i03.blend", 36),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_body_i03.blend", 40),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_body_i03.blend", 40),
    "xslash": (ROOT / "models/astra_xslash_body_i03.blend", 55),
}


def evaluated_world(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coords


def summarize(values):
    return {"edges": len(values), "maximum_ratio": float(values.max()),
            "p99_ratio": float(np.percentile(values, 99)),
            "p999_ratio": float(np.percentile(values, 99.9))} if len(values) else {"edges": 0}


def inspect(model, frame):
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    body = bpy.data.objects["char1"]
    rest = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", rest)
    rest = rest.reshape(-1, 3)
    matrix = np.asarray(body.matrix_world)
    rest = rest @ matrix[:3, :3].T + matrix[:3, 3]
    edges = np.empty(len(body.data.edges) * 2, dtype=np.int32)
    body.data.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    posed = evaluated_world(body)
    posed_lengths = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
    valid = rest_lengths > 1e-6
    ratios = np.zeros(len(edges), dtype=np.float32)
    ratios[valid] = posed_lengths[valid] / rest_lengths[valid]
    component = np.asarray([item.value for item in body.data.attributes["astra_body_plate_component"].data])
    a = component[edges[:, 0]]
    b = component[edges[:, 1]]
    masks = {
        "nonplate_both": valid & (a < 0) & (b < 0),
        "plate_internal_same_island": valid & (a >= 0) & (a == b),
        "plate_cross_island": valid & (a >= 0) & (b >= 0) & (a != b),
        "plate_to_nonplate_boundary": valid & ((a >= 0) != (b >= 0)),
    }
    return {name: summarize(ratios[mask]) for name, mask in masks.items()}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {name: inspect(model, frame) for name, (model, frame) in MODELS.items()}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_I03_STRETCH_REGIONS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
