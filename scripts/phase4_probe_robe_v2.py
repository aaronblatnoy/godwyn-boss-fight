"""
phase4_probe_robe_v2.py — probe godwyn_p2_robe.blend and godwyn_face.blend structure.
"""
import bpy, os
from mathutils import Vector

HOME    = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
ROBE_B  = f"{REPO}/models/godwyn_p2_robe.blend"
FACE_B  = f"{REPO}/models/godwyn_face.blend"

# ---- Probe robe blend ----
print("\n[probe] === godwyn_p2_robe.blend ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=ROBE_B)
bpy.context.view_layer.update()

for o in bpy.context.scene.objects:
    print(f"[probe] robe obj: {o.name}  type={o.type}  loc={tuple(round(v,4) for v in o.location)}")
    if o.type == "ARMATURE":
        bones = o.data.bones
        phys  = [b.name for b in bones if b.name.startswith("phys_")]
        mix   = [b.name for b in bones if not b.name.startswith("phys_")]
        print(f"[probe]   armature: {len(bones)} bones  mixamo={len(mix)}  phys={len(phys)}")
        print(f"[probe]   first 5 mixamo: {mix[:5]}")
        print(f"[probe]   LeftHand in mixamo: {'LeftHand' in mix}")
        # Show LeftHand location in rest pose
        if "LeftHand" in [b.name for b in bones]:
            lh = bones["LeftHand"]
            print(f"[probe]   LeftHand head={tuple(round(v,4) for v in lh.head_local)}  tail={tuple(round(v,4) for v in lh.tail_local)}")
    if o.type == "MESH":
        vgs = [vg.name for vg in o.vertex_groups]
        print(f"[probe]   mesh: verts={len(o.data.vertices)}  vgroups={len(vgs)}")
        mats = [m.name for m in o.data.materials if m]
        print(f"[probe]   mats: {mats}")
        for mod in o.modifiers:
            if mod.type == "ARMATURE":
                print(f"[probe]   arm mod -> {mod.object.name if mod.object else None}")

# ---- Probe face blend ----
print("\n[probe] === godwyn_face.blend ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=FACE_B)
bpy.context.view_layer.update()

for o in bpy.context.scene.objects:
    print(f"[probe] face obj: {o.name}  type={o.type}  loc={tuple(round(v,4) for v in o.location)}")
    if o.type == "ARMATURE":
        bones = o.data.bones
        phys  = [b.name for b in bones if b.name.startswith("phys_")]
        mix   = [b.name for b in bones if not b.name.startswith("phys_")]
        print(f"[probe]   armature: {len(bones)} bones  mixamo={len(mix)}  phys={len(phys)}")
        if "LeftHand" in [b.name for b in bones]:
            lh = bones["LeftHand"]
            print(f"[probe]   LeftHand head={tuple(round(v,4) for v in lh.head_local)}  tail={tuple(round(v,4) for v in lh.tail_local)}")
    if o.type == "MESH":
        vgs = [vg.name for vg in o.vertex_groups]
        mats = [m.name for m in o.data.materials if m]
        print(f"[probe]   mesh: {o.name}  verts={len(o.data.vertices)}  vgroups={len(vgs)}  mats={mats}")
        bbox_pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        zmin = min(p.z for p in bbox_pts); zmax = max(p.z for p in bbox_pts)
        print(f"[probe]   world Z: {zmin:.3f}..{zmax:.3f}")
        if o.name in ("Godwyn_Sword", "Godwyn_Gauntlet"):
            print(f"[probe]   parent={o.parent.name if o.parent else None}  parent_bone={o.parent_bone}")
            for mod in o.modifiers:
                print(f"[probe]   mod={mod.type}  -> {mod.object.name if hasattr(mod,'object') and mod.object else None}")
