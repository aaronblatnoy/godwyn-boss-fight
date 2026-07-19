"""
Phase 1 — mocap retarget (Blender 5.2, slotted actions).

PASS 1: import godwyn_game.glb + mocap_combo.glb, copy per-bone keyframes for
ONLY the base Mixamo bones into a NEW action on our armature (97 phys_ chains
never touched), save models/godwyn_mocap.blend.

PASS 2 lives in mocap_ground_render.py and MUST run as a separate blender
invocation on the saved blend: pose evaluation inside the process that did the
glTF imports is corrupt (hips translation off ~10x, even after open_mainfile).
A fresh process evaluates the same file correctly.
"""

import bpy
import os
import re
import math
from mathutils import Vector

MODELS_DIR = os.path.expanduser("~/godwyn-boss-fight/models")
BLEND_PATH = os.path.join(MODELS_DIR, "godwyn_mocap.blend")
OUT_DIR = "/tmp/godwyn_retarget"
os.makedirs(OUT_DIR, exist_ok=True)

BASE_BONES = {
    "Hips", "Spine", "Spine01", "Spine02", "neck", "Head",
    "headfront", "head_end",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
}
ACTION_NAME = "Godwyn_DoubleCombo"
BONE_RE = re.compile(r'pose\.bones\["([^"]+)"\]\.(.+)')

print("=" * 60)
print("PHASE 1 RETARGET — PASS 1 (copy curves)")
print("=" * 60)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS_DIR, "godwyn_game.glb"))
bpy.context.view_layer.update()
godwyn_objs = list(bpy.context.scene.objects)

stray = bpy.context.scene.objects.get("Icosphere")
if stray:
    print("removing stray Icosphere from blend")
    godwyn_objs = [o for o in godwyn_objs if o is not stray]
    bpy.data.objects.remove(stray, do_unlink=True)

our_arm = next(o for o in godwyn_objs if o.type == "ARMATURE")
print(f"our armature: {our_arm.name}, bones={len(our_arm.data.bones)}")
our_bones = {b.name for b in our_arm.data.bones}
matched = BASE_BONES & our_bones
print(f"base bones on our rig: {len(matched)}/{len(BASE_BONES)}")

sword = next((o for o in godwyn_objs if "sword" in o.name.lower()), None)
if sword:
    print(f"sword: {sword.name} parent_type={sword.parent_type} "
          f"parent_bone={sword.parent_bone!r}")
    # glTF import bone-parents to the bone TAIL frame without compensating for
    # the importer's (bogus, huge) bone length — sword sits exactly one bone
    # length from the hand even at rest. Pull it back along bone -Y.
    from mathutils import Matrix
    blen = our_arm.data.bones[sword.parent_bone].length
    sword.matrix_parent_inverse = (
        Matrix.Translation((0.0, -blen, 0.0)) @ sword.matrix_parent_inverse)
    print(f"sword parent-inverse corrected by -{blen:.1f} along parent bone Y")

# ── import mocap, snapshot curves ────────────────────────────────
pre = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS_DIR, "mocap_combo.glb"))
bpy.context.view_layer.update()
mocap_objs = [o for o in bpy.context.scene.objects if o not in pre]
mocap_arm = next(o for o in mocap_objs if o.type == "ARMATURE")
src_act = mocap_arm.animation_data.action
print(f"mocap action: {src_act.name!r} range={tuple(src_act.frame_range)}")

src_slot = mocap_arm.animation_data.action_slot or src_act.slots[0]
src_cb = None
for layer in src_act.layers:
    for strip in layer.strips:
        cb = strip.channelbag(src_slot)
        if cb:
            src_cb = cb
print(f"mocap fcurves: {len(src_cb.fcurves)}")

# The two glTF imports assign DIFFERENT bone-local frames (Hips differs by
# 124 deg — our phys_ children skew the importer's bone-direction heuristic),
# so raw fcurve copying mangles the pose. Convert each pose basis instead:
#   B_our(b) = L_our(b)^-1 @ L_our(p) @ L_moc(p)^-1 @ L_moc(b) @ B_moc(b)
# where L = rest matrix_local (armature space). Pure data math, no depsgraph
# (in-process pose evaluation after glTF import is unreliable).
from mathutils import Matrix, Quaternion
import collections

L_M = {b.name: b.matrix_local.copy() for b in mocap_arm.data.bones}
L_O = {b.name: b.matrix_local.copy() for b in our_arm.data.bones}
parent_of = {b.name: (b.parent.name if b.parent else None)
             for b in mocap_arm.data.bones}

chan = collections.defaultdict(dict)
anim_bones = set()
for fc in src_cb.fcurves:
    m = BONE_RE.match(fc.data_path)
    if not m:
        print(f"  skip non-bone path: {fc.data_path}")
        continue
    bname, prop = m.group(1), m.group(2)
    if bname not in BASE_BONES or bname not in our_bones:
        continue
    chan[(bname, prop)][fc.array_index] = fc
    anim_bones.add(bname)
print(f"animated base bones: {len(anim_bones)}")

frame_lo, frame_hi = src_act.frame_range
bake_frames = list(range(int(math.ceil(frame_lo)), int(math.floor(frame_hi)) + 1))

baked = {}   # bone -> [(frame, loc3, quat4), ...]
for bname in sorted(anim_bones):
    pn = parent_of[bname]
    K = L_O[bname].inverted()
    if pn:
        K = K @ L_O[pn] @ L_M[pn].inverted()
    K = K @ L_M[bname]
    rows = []
    prev_q = None
    for t in bake_frames:
        lc = chan.get((bname, "location"), {})
        loc = tuple(lc[i].evaluate(t) if i in lc else 0.0 for i in range(3))
        qc = chan.get((bname, "rotation_quaternion"), {})
        quat = Quaternion(tuple(
            qc[i].evaluate(t) if i in qc else (1.0 if i == 0 else 0.0)
            for i in range(4)))
        B_M = Matrix.LocRotScale(loc, quat, None)
        l2, q2, _ = (K @ B_M).decompose()
        if prev_q is not None and prev_q.dot(q2) < 0:
            q2.negate()
        prev_q = q2
        rows.append((t, tuple(l2), tuple(q2)))
    baked[bname] = rows
print(f"baked {len(baked)} bones x {len(bake_frames)} frames (converted bases)")

for o in mocap_objs:
    bpy.data.objects.remove(o, do_unlink=True)

# ── build new slotted action on our armature ─────────────────────
dst_act = bpy.data.actions.new(ACTION_NAME)
dst_act.use_fake_user = True
slot = dst_act.slots.new(id_type='OBJECT', name="Godwyn")
layer = dst_act.layers.new("Layer")
strip = layer.strips.new(type='KEYFRAME')
cb = strip.channelbag(slot, ensure=True)

for bname, rows in baked.items():
    for prop, dim, get in (("location", 3, lambda r: r[1]),
                           ("rotation_quaternion", 4, lambda r: r[2])):
        dp = f'pose.bones["{bname}"].{prop}'
        for i in range(dim):
            nfc = cb.fcurves.new(dp, index=i)
            nfc.keyframe_points.add(len(rows))
            for kp, r in zip(nfc.keyframe_points, rows):
                kp.co = (r[0], get(r)[i])
                kp.interpolation = 'LINEAR'
            nfc.update()
print(f"dst action fcurves: {len(cb.fcurves)}")

ad = our_arm.animation_data_create()
ad.action = dst_act
ad.action_slot = slot

scene = bpy.context.scene
scene.frame_start = int(math.ceil(frame_lo))
scene.frame_end = int(math.floor(frame_hi))
scene.render.fps = 24
print(f"scene frames {scene.frame_start}-{scene.frame_end} @24fps")

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"PASS 1 saved {BLEND_PATH}")

print("PASS 1 DONE — run mocap_ground_render.py on the saved blend")
