"""
PHASE 3 FIXER r7 — upright posture bias + cloth de-shatter (round-3 fixer).

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r7.py

DIAGNOSIS (p3_r7_diag.py): the retarget is FAITHFUL — source mocap and
retargeted rig have identical head-hips dZ / horizontal lean at f1/20/40/68
(rigs share the same Mixamo skeleton; only the grounding Z-offset differs).
The "hunched" read comes from the source clip itself (torso rise 0.73-0.97m
vs 1.04m rest, up to 0.66m forward lean) plus the down-looking camera and the
cape mummification. So NO conversion-matrix change; instead:

  1. UPRIGHT BIAS (flaw 2): per-frame adaptive lean reduction on the spine
     chain. lean(f) = angle(neck-hips, Z). theta = 0.35*lean, capped 12deg,
     gaussian-smoothed — proportional, so upright frames barely move and the
     dive keeps its lunge drama. theta is distributed Spine02 .35 /
     Spine01 .35 / Spine .30 (+ neck 0.30*theta extra to lift the head out
     of the shoulders). Applied by rotating each
     pose matrix about the character's per-frame left-right axis at the
     bone head, then re-deriving the local basis (loc+quat keys rewritten
     in place). Hips/feet/arms curves untouched -> grounding survives.
  2. CLOTH SHATTER (flaw 1): CapeWind peak 250 -> 100 and pulse shortened
     (f8..f26, plateau f11-22); sim quality 15 -> 22, collision_quality
     6 -> 10 for both grids; self_distance_min 0.008 -> 0.010 (distance_min
     stays 0.022); cape time_scale 0.85 -> 0.70 (robe stays 0.85).
  3. Rebake -45..68, save.

char1 materials/UVs/weights, face, sword parenting, phys_ chains: untouched.
Idempotent: upright pass is flag-guarded (act["p3_r7_upright"]); wind is
rebuilt by name; cloth settings are absolute.
"""
import bpy
import math
import time
from mathutils import Matrix, Vector

PREROLL = -45
# chain order on THIS rig: Hips -> Spine02 -> Spine01 -> Spine -> neck
CHAIN = ("Spine02", "Spine01", "Spine", "neck")
DIST = {"Spine02": 0.35, "Spine01": 0.35, "Spine": 0.30, "neck": 0.30}
GAIN = 0.35          # proportional: every leaning frame straightens a bit
CAP = math.radians(12.0)

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
cape = bpy.data.objects["CapeGrid"]
robe = bpy.data.objects["RobeGrid"]
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))
act = arm.animation_data.action
slot = arm.animation_data.action_slot
cb = None
for layer in act.layers:
    for strip in layer.strips:
        c = strip.channelbag(slot)
        if c:
            cb = c
assert cb is not None
print(f"clip {frames[0]}..{frames[-1]} action={act.name!r}")

# ════════════════════════════════════════════════════════════════
# 1) UPRIGHT BIAS
# ════════════════════════════════════════════════════════════════
if act.get("p3_r7_upright"):
    print("upright bias: already applied, skipping")
else:
    parent_name = {}
    L = {}
    for bn in CHAIN:
        b = arm.data.bones[bn]
        parent_name[bn] = b.parent.name
        L[bn] = b.matrix_local.copy()
        L[b.parent.name] = b.parent.matrix_local.copy()
    print("chain parents:", {b: parent_name[b] for b in CHAIN})

    # pass 1: sample pose matrices, lean, left-right axis
    M = {}          # frame -> {bone: matrix}
    axis = {}
    lean = {}
    for f in frames:
        scene.frame_set(f)
        ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        M[f] = {bn: ae.pose.bones[bn].matrix.copy()
                for bn in CHAIN + ("Hips",)}
        v = ae.pose.bones["neck"].head - ae.pose.bones["Hips"].head
        lean[f] = v.angle(Vector((0, 0, 1))) if v.length > 1e-6 else 0.0
        a = ae.pose.bones["LeftUpLeg"].head - ae.pose.bones["RightUpLeg"].head
        a.z = 0.0
        axis[f] = a.normalized() if a.length > 1e-6 else axis[frames[0]]

    theta = {f: min(GAIN * lean[f], CAP) for f in frames}
    K = (1.0, 4.0, 6.0, 4.0, 1.0)
    for _ in range(2):
        nx = {}
        for f in frames:
            acc = wacc = 0.0
            for k, w in zip(range(-2, 3), K):
                fk = min(max(f + k, frames[0]), frames[-1])
                acc += w * theta[fk]
                wacc += w
            nx[f] = acc / wacc
        theta = nx
    print("lean(deg):", " ".join(f"{f}:{math.degrees(lean[f]):.0f}"
                                 for f in frames[::8] + [frames[-1]]))
    print("theta(deg):", " ".join(f"{f}:{math.degrees(theta[f]):.1f}"
                                  for f in frames[::8] + [frames[-1]]))

    def apply_chain(f, sign):
        """rotate each chain bone about the L-R axis at its head; return
        (new pose mats, new local bases)."""
        Mn = {"Hips": M[f]["Hips"]}
        bases = {}
        for bn in CHAIN:
            pn = parent_name[bn]
            carried = Mn[pn] @ M[f][pn].inverted() @ M[f][bn]
            T = Matrix.Translation(carried.translation)
            R = Matrix.Rotation(sign * theta[f] * DIST[bn], 4, axis[f])
            Mn[bn] = T @ R @ T.inverted() @ carried
            bases[bn] = ((L[pn].inverted() @ L[bn]).inverted()
                         @ Mn[pn].inverted() @ Mn[bn])
        return Mn, bases

    # pick the sign that raises the neck at the max-theta frame
    fmax = max(frames, key=lambda f: theta[f])
    zp = apply_chain(fmax, +1.0)[0]["neck"].translation.z
    zn = apply_chain(fmax, -1.0)[0]["neck"].translation.z
    sign = 1.0 if zp >= zn else -1.0
    print(f"sign={sign:+.0f} (f{fmax}: neckZ +{zp*s:.3f} / -{zn*s:.3f}, "
          f"orig {M[fmax]['neck'].translation.z*s:.3f})")

    new_vals = {}   # (bone, prop, idx) -> {frame: value}
    prev_q = {}
    for f in frames:
        _, bases = apply_chain(f, sign)
        for bn in CHAIN:
            loc, q, _ = bases[bn].decompose()
            if bn in prev_q and prev_q[bn].dot(q) < 0:
                q.negate()
            prev_q[bn] = q
            for i in range(3):
                new_vals.setdefault((bn, "location", i), {})[f] = loc[i]
            for i in range(4):
                new_vals.setdefault((bn, "rotation_quaternion", i), {})[f] = q[i]

    touched = 0
    for fc in cb.fcurves:
        for bn in CHAIN:
            for prop in ("location", "rotation_quaternion"):
                if fc.data_path == f'pose.bones["{bn}"].{prop}':
                    vals = new_vals[(bn, prop, fc.array_index)]
                    for kp in fc.keyframe_points:
                        f = int(round(kp.co.x))
                        if f in vals:
                            kp.co.y = vals[f]
                            kp.handle_left.y = vals[f]
                            kp.handle_right.y = vals[f]
                    fc.update()
                    touched += 1
    act["p3_r7_upright"] = True
    print(f"upright bias: rewrote {touched} fcurves")

    # verify
    for f in (1, 20, 24, 40, 68):
        scene.frame_set(f)
        ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        hp = ae.pose.bones["Hips"].head * s
        hd = ae.pose.bones["Head"].head * s
        print(f"  f{f:03d} now: hipsZ={hp.z:.3f} headZ={hd.z:.3f} "
              f"dZ={hd.z-hp.z:.3f} (lean was {math.degrees(lean[f]):.0f}deg)")

# ════════════════════════════════════════════════════════════════
# 2) WIND: peak 250 -> 100, pulse f8..f26
# ════════════════════════════════════════════════════════════════
if "CapeWind" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["CapeWind"], do_unlink=True)
hp = {}
for f in (10, 30):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    hp[f] = (arm.evaluated_get(dg).pose.bones["Hips"].head * s).copy()
vel = hp[30] - hp[10]
vel.z = 0.0
back = (-vel).normalized() if vel.length > 1e-3 else Vector((0, 1, 0))
bpy.ops.object.effector_add(type='WIND',
                            location=hp[10] - back * 3.0 + Vector((0, 0, 1.3)))
wind = bpy.context.active_object
wind.name = "CapeWind"
wind.rotation_euler = back.to_track_quat('Z', 'Y').to_euler()
fs = wind.field
fs.strength = 0.0
fs.flow = 0.0
fs.noise = 0.0
for f, v in ((PREROLL, 0.0), (8, 0.0), (11, 100.0), (22, 100.0), (26, 0.0)):
    fs.strength = v
    fs.keyframe_insert("strength", frame=f)
print("CapeWind keyed: 0 @f8 -> 100 @f11-22 -> 0 @f26 "
      f"dir={tuple(round(c, 2) for c in back)}")

# ════════════════════════════════════════════════════════════════
# 3) CLOTH QUALITY + SELF-COLLISION + CAPE TIME_SCALE
# ════════════════════════════════════════════════════════════════
for obj, tsc in ((cape, 0.70), (robe, 0.85)):
    cl = obj.modifiers["Cloth"]
    cset = cl.settings
    cset.time_scale = tsc
    cset.quality = 22
    ccol = cl.collision_settings
    ccol.collision_quality = 10
    ccol.distance_min = 0.022
    ccol.use_self_collision = True
    ccol.self_distance_min = 0.010
    cl.point_cache.frame_start = PREROLL
    cl.point_cache.frame_end = scene.frame_end
    print(f"{obj.name}: ts={tsc} q=22 colq=10 dmin=0.022 self=0.010")

# ════════════════════════════════════════════════════════════════
# 4) REBAKE + SAVE
# ════════════════════════════════════════════════════════════════
old_start = scene.frame_start
scene.frame_start = PREROLL
bpy.ops.ptcache.free_bake_all()
t0 = time.time()
bpy.ops.ptcache.bake_all(bake=True)
print(f"baked {PREROLL}..{scene.frame_end} in {time.time()-t0:.1f}s")
scene.frame_start = old_start
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("SAVED; P3 FIXER R7 DONE")
