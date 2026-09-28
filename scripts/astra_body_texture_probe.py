"""Sample Meshy UV textures by geometric zone to document segmentation thresholds."""
import bpy
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/meshy_body_godA.glb"
OUT = ROOT / "renders/astra/char2/meshy_body_texture_probe.json"


def image_array(image):
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape(image.size[1], image.size[0], image.channels)


def sample(array, uv):
    height, width = array.shape[:2]
    x = int(np.floor((uv[0] % 1.0) * width)) % width
    y = int(np.floor((uv[1] % 1.0) * height)) % height
    return array[y, x, :3]


def stats(values):
    if not values:
        return {"count": 0}
    array = np.asarray(values)
    return {"count": len(array), "mean": array.mean(axis=0).tolist(),
            "p10": np.percentile(array, 10, axis=0).tolist(),
            "p50": np.percentile(array, 50, axis=0).tolist(),
            "p90": np.percentile(array, 90, axis=0).tolist()}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    obj = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
    mesh = obj.data
    uv_data = mesh.uv_layers.active.data
    arrays = {image.name: image_array(image) for image in bpy.data.images}
    zones = {
        "head": lambda p: p.z > 0.55,
        "upper_core": lambda p: 0.18 < p.z <= 0.55 and abs(p.x) < 0.28,
        "upper_outer": lambda p: 0.18 < p.z <= 0.55 and abs(p.x) >= 0.28,
        "arms_hands": lambda p: -0.15 < p.z <= 0.45 and abs(p.x) >= 0.35,
        "waist_sash": lambda p: -0.05 < p.z <= 0.20 and abs(p.x) < 0.38,
        "robe": lambda p: p.z <= 0.05 and abs(p.x) < 0.42,
        "legs": lambda p: p.z < -0.15 and 0.08 < abs(p.x) < 0.38,
        "outer_cape": lambda p: p.z < 0.2 and abs(p.x) >= 0.38,
    }
    values = {zone: {name: [] for name in arrays} for zone in zones}
    coord_stats = {zone: [] for zone in zones}
    # Deterministic every-fifth-face sample is ample and keeps the JSON compact.
    for polygon_index, polygon in enumerate(mesh.polygons):
        if polygon_index % 5:
            continue
        center = obj.matrix_world @ polygon.center
        matched = [name for name, predicate in zones.items() if predicate(center)]
        if not matched:
            continue
        uv = np.mean([uv_data[index].uv[:] for index in polygon.loop_indices], axis=0)
        for zone in matched:
            coord_stats[zone].append(center[:])
            for name, array in arrays.items():
                values[zone][name].append(sample(array, uv))
    material = mesh.materials[0]
    links = []
    for link in material.node_tree.links:
        links.append({"from_node": link.from_node.name, "from_socket": link.from_socket.name,
                      "to_node": link.to_node.name, "to_socket": link.to_socket.name})
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "material_links": links,
        "zones_source_coordinates": {
            name: {"coordinates": stats(coord_stats[name]),
                   "images": {image: stats(rows) for image, rows in values[name].items()}}
            for name in zones
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("TEXTURE_PROBE", json.dumps({name: {image: data["p50"] for image, data in row["images"].items()}
                                         for name, row in report["zones_source_coordinates"].items()}), flush=True)


if __name__ == "__main__":
    main()
