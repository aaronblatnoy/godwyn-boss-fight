"""Sample Meshy base-color values by geometric zone for mask feasibility."""
import bpy
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT / "models/meshy_head_approved.glb"))
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
mat = ob.data.materials[0]
node = next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and
            any(link.to_socket.name == "Base Color" for link in n.outputs["Color"].links))
im = node.image
w, h = im.size
pix = np.asarray(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
uv = ob.data.uv_layers.active.data
rgb = np.zeros((len(ob.data.vertices), 3), np.float32)
count = np.zeros(len(ob.data.vertices), np.float32)
for poly in ob.data.polygons:
    for li in poly.loop_indices:
        vi = ob.data.loops[li].vertex_index
        u, v = uv[li].uv
        x = min(w - 1, max(0, int(u * (w - 1))))
        y = min(h - 1, max(0, int(v * (h - 1))))
        rgb[vi] += pix[y, x, :3]
        count[vi] += 1
rgb /= np.maximum(count[:, None], 1)
p = np.array([v.co[:] for v in ob.data.vertices], float)
zones = {
    "face": (np.abs(p[:, 0]) < .30) & (p[:, 1] < -.34) & (p[:, 2] > -.10) & (p[:, 2] < .65),
    "side_hair": (np.abs(p[:, 0]) > .36) & (p[:, 2] > -.45) & (p[:, 2] < .70),
    "top_hair": (p[:, 2] > .72),
    "lower_center": (np.abs(p[:, 0]) < .35) & (p[:, 2] < -.45),
    "shoulders": (np.abs(p[:, 0]) > .50) & (p[:, 2] < -.45),
}
report = {}
for name, mask in zones.items():
    q = rgb[mask]
    report[name] = {"vertices": len(q), "rgb_p05": np.quantile(q, .05, axis=0).tolist(),
                    "rgb_median": np.median(q, axis=0).tolist(),
                    "rgb_p95": np.quantile(q, .95, axis=0).tolist(),
                    "luma_median": float(np.median(q @ [.2126, .7152, .0722]))}
(OUT / "meshy_colorprobe.json").write_text(json.dumps(report, indent=2) + "\n")
print("MESHY_COLORPROBE_DONE", json.dumps(report), flush=True)
