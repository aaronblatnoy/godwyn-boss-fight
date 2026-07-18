"""
phase4_probe_blend.py — probe godwyn_face.blend to understand what objects
are present, their types, parents, and relationships before Phase 4 export.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_probe_blend.py 2>&1
"""
import bpy, os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_face.blend")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

print("\n[probe] === OBJECTS IN godwyn_face.blend ===")
for o in scn.objects:
    parent_str = f"parent={o.parent.name}({o.parent_type})" if o.parent else "no-parent"
    print(f"[probe]  {o.name:40s} type={o.type:12s} {parent_str}")

arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
if arm:
    print(f"\n[probe] ARMATURE: {arm.name}  bones={len(arm.data.bones)}")
    for b in arm.data.bones:
        print(f"[probe]   bone: {b.name}")

meshes = [o for o in scn.objects if o.type == "MESH"]
print(f"\n[probe] MESHES ({len(meshes)}):")
for m in meshes:
    vg_names = [vg.name for vg in m.vertex_groups]
    mats = [mat.name for mat in m.data.materials if mat]
    parent_bone = m.parent_bone if m.parent_type == "BONE" else None
    print(f"[probe]  {m.name}")
    print(f"[probe]    verts={len(m.data.vertices)} vgroups={len(vg_names)} mats={mats}")
    print(f"[probe]    parent_type={m.parent_type} parent_bone={parent_bone}")
    if vg_names:
        print(f"[probe]    first 5 vgroups: {vg_names[:5]}")

print("\n[probe] DONE")
