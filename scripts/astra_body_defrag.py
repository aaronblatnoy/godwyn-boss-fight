"""Remove tiny disconnected fragments from the body mesh (char1); save candidate i03."""
import bpy, bmesh, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MIN_VERTS = 50
bpy.ops.wm.open_mainfile(filepath=str(ROOT/"models/astra_character_v2.blend"))
report = {}
for name in ["char1", "AstraChar2_R6_NeckGraft"]:
    o = bpy.data.objects.get(name)
    if not o: continue
    me = o.data; bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    seen = set(); kill = []; sizes = []
    for v in bm.verts:
        if v.index in seen: continue
        comp = [v]; seen.add(v.index); stack = [v]
        while stack:
            x = stack.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); stack.append(y); comp.append(y)
        sizes.append(len(comp))
        if len(comp) < MIN_VERTS: kill.extend(comp)
    before = (len(bm.verts), len(bm.faces))
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(me); bm.free(); me.update()
    report[name] = {"verts_before": before[0], "faces_before": before[1], "verts_after": len(me.vertices), "faces_after": len(me.polygons),
                    "components_before": len(sizes), "components_removed": sum(1 for s in sizes if s < MIN_VERTS), "min_verts": MIN_VERTS}
    print("DEFRAG", name, report[name], flush=True)
arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
report["bones"] = len(arm.data.bones); report["actions"] = len(bpy.data.actions)
out = ROOT/"models/astra_character_v2_meshy_i03_defrag.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(out), copy=True)
(ROOT/"renders/astra/char2/body_defrag_i03.json").write_text(json.dumps(report, indent=2))
print("DEFRAG_SAVED", out.name, report["bones"], report["actions"], flush=True)
