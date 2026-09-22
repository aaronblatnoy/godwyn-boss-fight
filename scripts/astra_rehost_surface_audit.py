"""Fresh v2 sole and cloth-floor measurements on evaluated char2 geometry."""
import bpy
import json
import numpy as np
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:]
name, model, out_dir = args[0], Path(args[1]), Path(args[2])
out_dir.mkdir(parents=True, exist_ok=True)
manifest = json.loads((out_dir / f"{name}_manifest.json").read_text())
bpy.ops.wm.open_mainfile(filepath=str(model))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
stage = next(o for o in scene.objects if o.name in {"Astra_Move_Stage", "Astra_Stage"})
floor = max((stage.matrix_world @ v.co).z for v in stage.data.vertices)

groups = {g.index: g.name for g in body.vertex_groups}
soles = {}
for side in ["Left", "Right"]:
    soles[side] = [v.index for v in body.data.vertices
                   if (body.matrix_world @ v.co).z < .13
                   and sum(g.weight for g in v.groups
                           if groups[g.group] in [side + "Foot", side + "ToeBase"]) > .6]
families = {}
for bone in rig.pose.bones:
    if bone.name.startswith(("phys_robe", "phys_cape")):
        families.setdefault(bone.name.rsplit("_", 1)[0], [])
for v in body.data.vertices:
    if (body.matrix_world @ v.co).z > .4:
        continue
    weights = {}
    for g in v.groups:
        family = groups[g.group].rsplit("_", 1)[0]
        if family in families:
            weights[family] = weights.get(family, 0.0) + g.weight
    for family, weight in weights.items():
        if weight > .55:
            families[family].append(v.index)
families = {k: v for k, v in families.items() if len(v) > 10}

rows = []
for frame in range(1, manifest["samples_end"] + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.to_mesh()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    matrix = np.array(obj.matrix_world)
    co = co @ matrix[:3, :3].T + matrix[:3, 3]
    rows.append({
        "frame": frame,
        "sole": {side: float(co[ids, 2].min() - floor) for side, ids in soles.items()},
        "hem": {family: float(co[ids, 2].min() - floor) for family, ids in families.items()},
    })
    obj.to_mesh_clear()
    if frame % 20 == 0:
        print("SURFACE", name, frame, flush=True)

if name != "xslash":
    old_contacts = json.loads((ROOT / f"renders/astra/moves/{name}_contacts.json").read_text())
    before = old_contacts["after"]
    old_floor = {
        "sole_min_m": min(v for row in before for v in row["sole"].values()),
        "cloth_min_m": min(v for row in before for v in row["hem"].values()),
    }
else:
    old = json.loads((ROOT / "renders/astra/naturalness_surface_after.json").read_text())
    before = rows
    old_floor = {
        "sole_min_m": min(v["min_clearance_m"] for row in old["rows"] for v in row["feet"].values()),
        "cloth_min_m": min(row["cloth_min_z"] - old["floor_z"] for row in old["rows"]),
    }

contacts = {"before": before, "after": rows,
            "before_semantics": "delivered old-body post-correction" if name != "xslash" else "not used; xslash baseline is summarized separately",
            "after_semantics": "published-char2 rehost evaluated geometry"}
(out_dir / f"{name}_contacts.json").write_text(json.dumps(contacts, indent=2) + "\n")
summary = {
    "name": name,
    "floor_z": floor,
    "sole_vertex_counts": {k: len(v) for k, v in soles.items()},
    "cloth_vertex_counts": {k: len(v) for k, v in families.items()},
    "old_body": old_floor,
    "v2_body": {
        "sole_min_m": min(v for row in rows for v in row["sole"].values()),
        "cloth_min_m": min(v for row in rows for v in row["hem"].values()),
        "sole_worst_frame": min(rows, key=lambda r: min(r["sole"].values()))["frame"],
        "cloth_worst_frame": min(rows, key=lambda r: min(r["hem"].values()))["frame"],
    },
    "planted_penetration_frames": {
        side: [row["frame"] for row in rows
               if manifest["planted"][side][row["frame"] - 1] and row["sole"][side] < 0]
        for side in ["Left", "Right"]
    },
    "cloth_threshold_m": old_floor["cloth_min_m"],
    "cloth_same_or_better_with_tolerance": min(v for row in rows for v in row["hem"].values()) >= old_floor["cloth_min_m"] - 1e-5,
}
(out_dir / "surface_verification.json").write_text(json.dumps(summary, indent=2) + "\n")
assert not any(summary["planted_penetration_frames"].values())
print("SURFACE COMPLETE", json.dumps(summary), flush=True)
