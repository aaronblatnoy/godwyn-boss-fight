"""Read-only structural probe for the Godwyn move rehost inputs."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
paths = [Path(p).resolve() for p in args]
out = {}


def mesh_digest(obj):
    h = hashlib.sha256()
    for v in obj.data.vertices:
        h.update(bytes(str(tuple(round(x, 9) for x in v.co)), "utf8"))
        h.update(bytes(str([(g.group, round(g.weight, 9)) for g in v.groups]), "utf8"))
    for p in obj.data.polygons:
        h.update(bytes(str(tuple(p.vertices)), "utf8"))
        h.update(bytes(str(p.material_index), "utf8"))
    return h.hexdigest()


for path in paths:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rigs = [o for o in scene.objects if o.type == "ARMATURE"]
    rig = rigs[0] if rigs else None
    action = rig.animation_data.action if rig and rig.animation_data else None
    actions = []
    for act in bpy.data.actions:
        fcurves = [fc for layer in act.layers for strip in layer.strips
                   for bag in strip.channelbags for fc in bag.fcurves]
        actions.append({
            "name": act.name,
            "frame_range": list(act.frame_range),
            "fcurves": len(fcurves),
            "keys": sum(len(fc.keyframe_points) for fc in fcurves),
            "cyclic_fcurves": sum(any(m.type == "CYCLES" for m in fc.modifiers) for fc in fcurves),
        })
    meshes = {}
    for name in ["char1", "Godwyn_Sword"]:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == "MESH":
            meshes[name] = {
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "digest": mesh_digest(obj),
                "custom": {k: obj[k] for k in obj.keys() if k != "_RNA_UI"},
                "groups": list(obj.vertex_groups.keys()),
                "modifiers": [(m.name, m.type, getattr(m, "object", None).name if getattr(m, "object", None) else None)
                              for m in obj.modifiers],
            }
    out[str(path.relative_to(ROOT))] = {
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "fps": scene.render.fps,
        "scene_custom": {k: scene[k] for k in scene.keys() if k != "_RNA_UI"},
        "scene_camera": scene.camera.name if scene.camera else None,
        "objects": len(scene.objects),
        "object_names": sorted(o.name for o in scene.objects),
        "bone_count": len(rig.data.bones) if rig else 0,
        "active_action": action.name if action else None,
        "actions": actions,
        "meshes": meshes,
    }

dest = ROOT / "renders/astra/rehost/input_probe.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2, default=str) + "\n")
print(json.dumps(out, indent=2, default=str), flush=True)
