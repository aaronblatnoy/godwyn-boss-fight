"""
PHASE 3 r7 DIAG — is the retarget crushing the rig onto the mocap skeleton?

  blender --background --python scripts/p3_r7_diag.py

Part A: open models/godwyn_mocap.blend (fresh process => depsgraph valid),
        print rest proportions of OUR rig (world) + animated Hips/Head world Z
        and head-forward offset at frames 1/20/40/68.
Part B: factory reset, import models/mocap_combo.glb, print SOURCE rest
        proportions + pure-fcurve-math FK Hips/Head positions at the same
        frames (no depsgraph — in-process pose eval after glTF import is
        known-corrupt).
"""
import bpy
import os
import re
import collections
from mathutils import Matrix, Quaternion, Vector

MODELS = os.path.expanduser("~/godwyn-boss-fight/models")
FRAMES = (1, 20, 40, 68)
BONE_RE = re.compile(r'pose\.bones\["([^"]+)"\]\.(.+)')

print("=" * 60)
print("PART A — retargeted rig (godwyn_mocap.blend)")
print("=" * 60)
bpy.ops.wm.open_mainfile(filepath=os.path.join(MODELS, "godwyn_mocap.blend"))
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
s = arm.scale.x
print(f"arm={arm.name} scale={s:.5f} rot={tuple(arm.rotation_euler)}")
for bn in ("Hips", "Spine", "Spine02", "neck", "Head", "head_end",
           "LeftFoot", "LeftHand"):
    b = arm.data.bones.get(bn)
    if b:
        p = b.matrix_local.translation * s
        print(f"  REST {bn:10s} world=({p.x:7.3f},{p.y:7.3f},{p.z:7.3f})")

for f in FRAMES:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    hp = ae.pose.bones["Hips"].head * s
    hd = ae.pose.bones["Head"].head * s
    ft = min(ae.pose.bones[b].head.z for b in
             ("LeftFoot", "RightFoot")) * s
    horiz = (Vector((hd.x, hd.y)) - Vector((hp.x, hp.y))).length
    print(f"  f{f:03d} hipsZ={hp.z:6.3f} headZ={hd.z:6.3f} "
          f"head-hips dZ={hd.z-hp.z:6.3f} horiz={horiz:6.3f} footZ={ft:6.3f}")

print("=" * 60)
print("PART B — source mocap (mocap_combo.glb, pure fcurve math)")
print("=" * 60)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, "mocap_combo.glb"))
marm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
MW = marm.matrix_world.copy()
print(f"mocap arm={marm.name} matrix_world=\n{MW}")
L = {b.name: b.matrix_local.copy() for b in marm.data.bones}
parent = {b.name: (b.parent.name if b.parent else None)
          for b in marm.data.bones}
for bn in ("Hips", "Spine", "Spine02", "neck", "Head", "head_end",
           "LeftFoot", "LeftHand"):
    if bn in L:
        p = MW @ L[bn].translation
        print(f"  REST {bn:10s} world=({p.x:7.3f},{p.y:7.3f},{p.z:7.3f})")

act = marm.animation_data.action
slot = marm.animation_data.action_slot or act.slots[0]
cb = None
for layer in act.layers:
    for strip in layer.strips:
        c = strip.channelbag(slot)
        if c:
            cb = c
chan = collections.defaultdict(dict)
for fc in cb.fcurves:
    m = BONE_RE.match(fc.data_path)
    if m:
        chan[(m.group(1), m.group(2))][fc.array_index] = fc


def basis(bn, t):
    lc = chan.get((bn, "location"), {})
    loc = tuple(lc[i].evaluate(t) if i in lc else 0.0 for i in range(3))
    qc = chan.get((bn, "rotation_quaternion"), {})
    q = Quaternion(tuple(qc[i].evaluate(t) if i in qc else
                         (1.0 if i == 0 else 0.0) for i in range(4)))
    return Matrix.LocRotScale(loc, q, None)


def pose_mat(bn, t, cache):
    if bn in cache:
        return cache[bn]
    p = parent[bn]
    local = (L[p].inverted() @ L[bn]) if p else L[bn]
    M = (pose_mat(p, t, cache) if p else Matrix.Identity(4)) \
        @ local @ basis(bn, t)
    cache[bn] = M
    return M


for f in FRAMES:
    cache = {}
    hp = MW @ pose_mat("Hips", f, cache).translation
    hd = MW @ pose_mat("Head", f, cache).translation
    ft = min((MW @ pose_mat(b, f, cache).translation).z
             for b in ("LeftFoot", "RightFoot") if b in L)
    horiz = (Vector((hd.x, hd.y)) - Vector((hp.x, hp.y))).length
    print(f"  f{f:03d} hipsZ={hp.z:6.3f} headZ={hd.z:6.3f} "
          f"head-hips dZ={hd.z-hp.z:6.3f} horiz={horiz:6.3f} footZ={ft:6.3f}")
print("DIAG DONE")
