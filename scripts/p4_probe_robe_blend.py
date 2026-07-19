"""
p4_probe_robe_blend.py — probe godwyn_p2_robe.blend to understand
what bones and meshes are present (the robe/cape/hair physics chains).

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/p4_probe_robe_blend.py 2>&1
"""
import bpy, os

REPO  = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_p2_robe.blend")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

print("\n[probe] === OBJECTS IN godwyn_p2_robe.blend ===")
for o in scn.objects:
    parent_str = f"parent={o.parent.name}({o.parent_type})" if o.parent else "no-parent"
    print(f"[probe]  {o.name:40s} type={o.type:12s} {parent_str}")

arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
if arm:
    print(f"\n[probe] ARMATURE: {arm.name}  bones={len(arm.data.bones)}")
    # Print all bones grouped by prefix
    for b in arm.data.bones:
        print(f"[probe]   bone: {b.name}")

meshes = [o for o in scn.objects if o.type == "MESH"]
print(f"\n[probe] MESHES ({len(meshes)}):")
for m in meshes:
    vg_names = [vg.name for vg in m.vertex_groups]
    mats     = [mat.name for mat in m.data.materials if mat]
    arm_mods = [md.name for md in m.modifiers if md.type == "ARMATURE"]
    print(f"[probe]  {m.name}")
    print(f"[probe]    verts={len(m.data.vertices)}  vgroups={len(vg_names)}  mats={mats}")
    print(f"[probe]    arm_modifiers={arm_mods}")
    if vg_names:
        print(f"[probe]    first 10 vgroups: {vg_names[:10]}")

print("\n[probe] DONE")
