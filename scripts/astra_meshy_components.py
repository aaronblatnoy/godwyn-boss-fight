"""Topology-component inventory for the single Meshy mesh."""
import bpy
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "models/meshy_head_approved.glb"))
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
n = len(ob.data.vertices)
parent = np.arange(n, dtype=np.int32)


def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = int(parent[a])
    return a


def union(a, b):
    a, b = find(a), find(b)
    if a != b:
        parent[b] = a


for edge in ob.data.edges:
    union(*edge.vertices)
roots = np.array([find(i) for i in range(n)], dtype=np.int32)
p = np.array([v.co[:] for v in ob.data.vertices], float)
uv = ob.data.uv_layers.active
components = []
for root in np.unique(roots):
    ids = np.where(roots == root)[0]
    q = p[ids]
    components.append({"root": int(root), "vertices": len(ids), "min": q.min(0).tolist(),
                       "max": q.max(0).tolist(), "size": np.ptp(q, axis=0).tolist(),
                       "centroid": q.mean(0).tolist()})
components.sort(key=lambda d: -d["vertices"])
report = {"object": ob.name, "vertices": n, "component_count": len(components),
          "components": components[:100]}
(OUT / "meshy_components.json").write_text(json.dumps(report, indent=2) + "\n")
print("MESHY_COMPONENTS_DONE", len(components), json.dumps(components[:20]), flush=True)
