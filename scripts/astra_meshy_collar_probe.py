"""Inventory meshes intersecting the Meshy/collar seam band."""
import bpy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "models/astra_character_v2_meshy_i01.blend"
OUT = ROOT / "renders/astra/char2/meshy_collar_objects.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    rows = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.data.vertices:
            continue
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        if lo[2] > 2.75 or hi[2] < 2.50:
            continue
        rows.append({
            "name": ob.name,
            "bounds": [lo, hi],
            "vertices": len(ob.data.vertices),
            "triangles": sum(len(p.vertices) - 2 for p in ob.data.polygons),
            "materials": [m.name if m else None for m in ob.data.materials],
            "hide_render": ob.hide_render,
        })
    OUT.write_text(json.dumps(sorted(rows, key=lambda r: r["name"]), indent=2) + "\n")
    print("MESHY_COLLAR_PROBE_PASS", len(rows), flush=True)


if __name__ == "__main__":
    main()
