"""p2_cape_probe.py — Phase 2 probe: inspect phys_ chains + cape/robe meshes
in models/godwyn_xslash.blend. Headless, no render."""
import bpy, os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_xslash.blend"))

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print(f"[probe] armature={arm.name} bones={len(arm.pose.bones)}")
print(f"[probe] scene frames {bpy.context.scene.frame_start}-{bpy.context.scene.frame_end}")

# phys / chain bones
phys = [b for b in arm.pose.bones if any(k in b.name.lower() for k in ("phys", "cape", "robe", "hair", "cloth", "skirt", "tabard"))]
for b in sorted(phys, key=lambda x: x.name):
    par = b.parent.name if b.parent else None
    print(f"[probe] bone {b.name:32s} parent={par:28s} head_z={round((arm.matrix_world @ b.head).z,2)} nkids={len(b.children)} mode={b.rotation_mode}")

# meshes and their vertex groups touching those bones
physnames = {b.name for b in phys}
for o in bpy.data.objects:
    if o.type == 'MESH':
        vgs = [g.name for g in o.vertex_groups if g.name in physnames]
        mods = [m.type for m in o.modifiers]
        print(f"[probe] mesh {o.name:24s} verts={len(o.data.vertices):6d} mods={mods} physVGs={len(vgs)} {vgs[:6]}")

# action info
ad = arm.animation_data
print(f"[probe] action={ad.action.name if ad and ad.action else None}")
if ad and ad.action:
    act = ad.action
    # Blender 5.x slotted actions
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags(act.slots[0]) if hasattr(strip, 'channelbags') else []:
                    pass
    except Exception as e:
        print("[probe] layer walk err:", e)
    # count fcurves via channelbag API
    try:
        for slot in act.slots:
            cb = act.layers[0].strips[0].channelbag(slot)
            if cb:
                bones_keyed = sorted({fc.data_path.split('"')[1] for fc in cb.fcurves if '"' in fc.data_path})
                print(f"[probe] slot {slot.identifier}: {len(cb.fcurves)} fcurves, bones keyed: {bones_keyed}")
    except Exception as e:
        print("[probe] channelbag err:", e)
print("[probe] DONE")
