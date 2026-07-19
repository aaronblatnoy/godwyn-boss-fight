"""
p4_probe_materials.py — probe materials and textures in both blend files
to understand what needs to be merged.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/p4_probe_materials.py 2>&1
"""
import bpy, os

REPO = os.path.expanduser("~/godwyn-boss-fight")

def probe_blend(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
    print(f"\n[probe] === {os.path.basename(path)} ===")
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        tex_nodes = [n for n in mat.node_tree.nodes
                     if n.type == "TEX_IMAGE" and n.image]
        if tex_nodes:
            print(f"[probe]  mat={mat.name}  textures:")
            for n in tex_nodes:
                img = n.image
                src = img.filepath if img.filepath else "(packed/generated)"
                px  = f"{img.size[0]}x{img.size[1]}" if img.size[0] else "?"
                print(f"[probe]    {n.label or n.name}  img={img.name}  {px}  src={src}")
        else:
            print(f"[probe]  mat={mat.name}  (no texture images)")

probe_blend(os.path.join(REPO, "models", "godwyn_p2_robe.blend"))
probe_blend(os.path.join(REPO, "models", "godwyn_face.blend"))
print("\n[probe] DONE")
