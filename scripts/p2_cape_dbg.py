"""p2_cape_dbg.py — debug spaces for the cape bake."""
import bpy, os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_xslash.blend"))
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print("[dbg] arm.matrix_world:")
for r in arm.matrix_world:
    print("[dbg]  ", tuple(round(v, 4) for v in r))
sc.frame_set(1)
bpy.context.view_layer.update()
sp = arm.pose.bones["Spine"]
print("[dbg] Spine pose matrix translation:", tuple(round(v, 3) for v in sp.matrix.translation))
ch = []
pb = arm.pose.bones["phys_cape_C_00"]
while pb:
    ch.append(pb)
    kids = [c for c in pb.children if c.name.startswith("phys_")]
    pb = kids[0] if kids else None
for pb in ch:
    h = arm.matrix_world @ pb.matrix.translation
    t = arm.matrix_world @ (pb.matrix @ Vector((0, pb.bone.length, 0)))
    print(f"[dbg] {pb.name} len={pb.bone.length:.3f} headW=({h.x:+.2f},{h.y:+.2f},{h.z:+.2f}) tailW=({t.x:+.2f},{t.y:+.2f},{t.z:+.2f}) quat={tuple(round(v,2) for v in pb.rotation_quaternion)}")
# offsets check
OFF = ch[0].parent.bone.matrix_local.inverted() @ ch[0].bone.matrix_local
M = sp.matrix @ OFF
W = arm.matrix_world @ M
print("[dbg] rigid root head via OFF:", tuple(round(v, 2) for v in W.translation))
print("[dbg] rigid root tail via OFF:", tuple(round(v, 2) for v in (W @ Vector((0, ch[0].bone.length, 0)))))
print("[dbg] DONE")
