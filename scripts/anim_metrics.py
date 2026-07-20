"""
anim_metrics.py — Phase 0 objective animation backbone (sec 4).

CLI:
  blender --background --python anim_metrics.py -- \
      --glb /path/to/file.glb \
      --action ActionName \
      --out /tmp/metrics.json \
      [--thresholds '{"M1_vertex_delta_frac":0.06,...}'] \
      [--calibrate /path/good.glb /path/bad.glb]

Reads bone world matrices per-frame via scene.frame_set (Blender 5.2 safe --
  NO action.fcurves). Computes M1-M4 per the plan, writes JSON to --out, prints path.

Idempotent -- safe to re-run.

phys_ prefix params (from rigMap):
  PHYS_CAPE_PREFIX  = "phys_cape"
  PHYS_ROBE_PREFIX  = "phys_robe"
  SWORD_OBJECT      = "Godwyn_Sword"
  RIGHTHAND_BONE    = "RightHand"
  FOOT_BONES        = ["LeftToeBase","RightToeBase","LeftFoot","RightFoot"]
  BODY_BONES        = Mixamo set (non-phys_)
  ELBOW_BONES       = ["LeftForeArm","RightForeArm"]
  KNEE_BONES        = ["LeftLeg","RightLeg"]
  SPINE_BONES       = ["Spine","Spine01","Spine02"]
"""

import bpy
import sys
import os
import json
import math
import argparse
from mathutils import Vector, Matrix, Quaternion

# ──────────────────────────────────────────────
#  THRESHOLD DEFAULTS (tunable via --thresholds)
# ──────────────────────────────────────────────
DEFAULT_THRESHOLDS = {
    "M1_vertex_delta_frac":  0.06,    # max per-frame vert delta as fraction of char height
    "M1_bbox_growth_ratio":  1.8,     # max cloth bbox growth vs rest
    "M2_ang_vel_deg":        45.0,    # max body bone angular velocity deg/frame
    "M2_jerk_deg":           30.0,    # max body bone jerk deg/frame^2 (>1 frame)
    "M2_elbow_knee_limit":   175.0,   # max bend angle for elbow/knee (hyperextension)
    "M2_spine_twist_limit":  90.0,    # max twist between adjacent spine bones (deg)
    "M3_foot_slide_frac":    0.02,    # max foot XY slide per frame (fraction of char height)
    "M3_ground_eps":         0.05,    # world-Z below which a foot is "in contact" (m)
    "M4_grip_dist_ratio":    1.15,    # max sword-hand dist ratio vs rest
}

# ──────────────────────────────────────────────
#  RIG CONSTANTS (from P0 rigMap -- phys_ prefixes are params)
# ──────────────────────────────────────────────
PHYS_CAPE_PREFIX  = "phys_cape"
PHYS_ROBE_PREFIX  = "phys_robe"
PHYS_HAIR_PREFIX  = "phys_hair"
SWORD_OBJECT      = "Godwyn_Sword"
RIGHTHAND_BONE    = "RightHand"
FOOT_BONES        = ["LeftToeBase", "RightToeBase", "LeftFoot", "RightFoot"]
TOE_BONES         = ["LeftToeBase", "RightToeBase"]
ELBOW_BONES       = ["LeftForeArm", "RightForeArm"]
KNEE_BONES        = ["LeftLeg", "RightLeg"]
SPINE_BONES       = ["Spine", "Spine01", "Spine02"]


def parse_args():
    """Parse args after '--' separator in Blender headless invocation."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Godwyn animation metrics (P0 backbone)")
    parser.add_argument("--glb", required=False, help="Input animated .glb file")
    parser.add_argument("--blend", required=False, help="Input animated .blend file (alt to --glb)")
    parser.add_argument("--action", required=False, default=None, help="Action name (default: first action)")
    parser.add_argument("--out", required=False, default="/tmp/anim_metrics.json", help="Output JSON path")
    parser.add_argument("--thresholds", required=False, default=None, help="JSON override for thresholds dict")
    parser.add_argument("--calibrate", required=False, nargs=2, metavar=("GOOD_GLB", "BAD_GLB"),
                        help="Run calibration: print suggested thresholds from good+bad clips")
    return parser.parse_args(argv)


def quat_angle_between(q1: Quaternion, q2: Quaternion) -> float:
    """Shortest-arc angle (degrees) between two ORIENTATIONS.

    Folds the quaternion double cover: q and -q represent the SAME orientation, so
    a sign flip between frames must read as ~0 deg, not 360. rotation_difference().angle
    can return up to 2*pi and does not fold the sign flip, which produced a spurious
    360 deg/frame M2 artifact (identical on good and bad clips). Using abs(dot) folds
    q/-q, and 2*acos(|dot|) yields the true shortest arc in [0, 180] deg.
    """
    d = abs(q1.normalized().dot(q2.normalized()))
    d = max(-1.0, min(1.0, d))
    return math.degrees(2.0 * math.acos(d))


def bone_world_matrix(arm_obj, pose_bone) -> Matrix:
    """Return bone's world-space matrix (head transform)."""
    return arm_obj.matrix_world @ pose_bone.matrix


def get_bone_quat(arm_obj, pose_bone) -> Quaternion:
    """Return bone's world-space rotation as quaternion."""
    mat = bone_world_matrix(arm_obj, pose_bone)
    return mat.to_quaternion()


def get_bone_head_world(arm_obj, pose_bone) -> Vector:
    """Return bone head in world space."""
    mat = bone_world_matrix(arm_obj, pose_bone)
    return mat.translation


def compute_character_height(arm_obj) -> float:
    """Estimate character height from the bound armature (world-space Z extent of mesh)."""
    max_z = -1e9
    min_z = 1e9
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == arm_obj:
            for v in obj.data.vertices:
                wv = obj.matrix_world @ v.co
                max_z = max(max_z, wv.z)
                min_z = min(min_z, wv.z)
    if max_z == -1e9:
        # Fallback: use armature pose bbox
        for pose_bone in arm_obj.pose.bones:
            hw = get_bone_head_world(arm_obj, pose_bone)
            max_z = max(max_z, hw.z)
            min_z = min(min_z, hw.z)
    h = max_z - min_z
    return h if h > 0 else 1.8  # fallback


def get_phys_verts(arm_obj, prefix: str):
    """Get list of (obj, vert_local_idx) for vertices weighted to bones with given prefix."""
    phys_bones = {b.name for b in arm_obj.data.bones if b.name.startswith(prefix)}
    result = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if obj.parent != arm_obj:
            continue
        # find vertex groups that match phys bones
        relevant_groups = {vg.index for vg in obj.vertex_groups if vg.name in phys_bones}
        if not relevant_groups:
            continue
        for v in obj.data.vertices:
            for vge in v.groups:
                if vge.group in relevant_groups and vge.weight > 0.1:
                    result.append((obj, v.index))
                    break
    return result


def get_vert_world(obj, vert_idx: int) -> Vector:
    """Get world position of a vertex."""
    v = obj.data.vertices[vert_idx]
    return obj.matrix_world @ v.co


def compute_cloth_bbox(obj_vert_list):
    """Return (min_vec, max_vec) of cloth vert world positions."""
    if not obj_vert_list:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    xs, ys, zs = [], [], []
    for (obj, vi) in obj_vert_list:
        wv = get_vert_world(obj, vi)
        xs.append(wv.x); ys.append(wv.y); zs.append(wv.z)
    return (Vector((min(xs), min(ys), min(zs))),
            Vector((max(xs), max(ys), max(zs))))


def bbox_size(mn, mx) -> float:
    d = mx - mn
    return d.x * d.y * d.z if (d.x * d.y * d.z > 0) else (d.length + 1e-6)


def load_file(glb=None, blend=None):
    """Load a .glb or .blend into current Blender session."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if glb:
        bpy.ops.import_scene.gltf(filepath=glb)
    elif blend:
        bpy.ops.wm.open_mainfile(filepath=blend)
    else:
        raise ValueError("Must provide --glb or --blend")


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def find_action(action_name=None):
    if not bpy.data.actions:
        return None
    if action_name:
        return bpy.data.actions.get(action_name)
    return bpy.data.actions[0]


def assign_action(arm_obj, action):
    """Assign action to armature's animation data."""
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = action


def run_metrics(glb=None, blend=None, action_name=None, thresholds=None, label=""):
    """
    Core metrics computation. Returns the full metrics dict.
    """
    T = {**DEFAULT_THRESHOLDS}
    if thresholds:
        T.update(thresholds)

    load_file(glb=glb, blend=blend)
    arm_obj = find_armature()
    if arm_obj is None:
        return {"error": "No armature found"}

    action = find_action(action_name)
    if action is None:
        return {"error": f"No action found (requested: {action_name})"}

    assign_action(arm_obj, action)

    frame_start = int(action.frame_range[0])
    frame_end   = int(action.frame_range[1])
    frames = list(range(frame_start, frame_end + 1))

    scene = bpy.context.scene
    scene.frame_start = frame_start
    scene.frame_end   = frame_end

    # Step to rest pose (frame 0 or frame_start) to get rest measurements
    scene.frame_set(frame_start)
    bpy.context.view_layer.update()

    char_height = compute_character_height(arm_obj)

    # --- Identify body bones ---
    all_bone_names = [b.name for b in arm_obj.data.bones]
    body_bone_names = [n for n in all_bone_names if not n.startswith("phys_")]
    phys_cape_verts = get_phys_verts(arm_obj, PHYS_CAPE_PREFIX)
    phys_robe_verts = get_phys_verts(arm_obj, PHYS_ROBE_PREFIX)
    cloth_verts = phys_cape_verts + phys_robe_verts

    # Rest-state cloth bbox
    scene.frame_set(frame_start)
    bpy.context.view_layer.update()
    rest_bbox_mn, rest_bbox_mx = compute_cloth_bbox(cloth_verts)
    rest_bbox_sz = bbox_size(rest_bbox_mn, rest_bbox_mx)

    # Rest sword grip distance
    sword_obj = bpy.data.objects.get(SWORD_OBJECT)
    rh_bone = arm_obj.pose.bones.get(RIGHTHAND_BONE)
    rest_grip_dist = None
    if sword_obj and rh_bone:
        sword_world = sword_obj.matrix_world.translation
        rh_world = get_bone_head_world(arm_obj, rh_bone)
        rest_grip_dist = (sword_world - rh_world).length

    # ── PER-FRAME PASS ──────────────────────────────────────────────────────
    # Collect per-frame data: cloth vert positions, body bone quats, foot world pos, sword dist

    prev_cloth_verts_world = None
    prev_body_quats = {}
    prev_body_ang_vel = {}  # frame-1 angular velocities

    # M1 accumulators
    m1_worst_frame = frame_start
    m1_worst_delta = 0.0
    m1_worst_bbox  = 1.0

    # M2 accumulators
    m2_worst_frame    = frame_start
    m2_worst_ang_vel  = 0.0
    m2_worst_jerk     = 0.0
    m2_limit_violations = []
    m2_jerk_spike_frames = []

    # M3 accumulators
    prev_foot_world = {}
    m3_worst_frame = frame_start
    m3_worst_slide = 0.0
    m3_worst_foot  = ""

    # M4 accumulators
    m4_worst_frame = frame_start
    m4_worst_ratio = 0.0

    for f in frames:
        scene.frame_set(f)
        bpy.context.view_layer.update()

        # ── M1: Cloth displacement ──────────────────────────────────────────
        if cloth_verts:
            curr_cloth_world = [get_vert_world(obj, vi) for (obj, vi) in cloth_verts]
            if prev_cloth_verts_world is not None:
                for i, (pw, cw) in enumerate(zip(prev_cloth_verts_world, curr_cloth_world)):
                    delta = (cw - pw).length / char_height
                    if delta > m1_worst_delta:
                        m1_worst_delta = delta
                        m1_worst_frame = f

            # Cloth bbox growth
            curr_bbox_mn, curr_bbox_mx = compute_cloth_bbox(cloth_verts)
            curr_bbox_sz = bbox_size(curr_bbox_mn, curr_bbox_mx)
            if rest_bbox_sz > 1e-6:
                ratio = curr_bbox_sz / rest_bbox_sz
            else:
                ratio = 1.0
            if ratio > m1_worst_bbox:
                m1_worst_bbox = ratio
                m1_worst_frame = f

            prev_cloth_verts_world = curr_cloth_world

        # ── M2: Body bone angular velocity + jerk ──────────────────────────
        curr_body_quats = {}
        for bname in body_bone_names:
            pb = arm_obj.pose.bones.get(bname)
            if pb:
                curr_body_quats[bname] = get_bone_quat(arm_obj, pb)

        if prev_body_quats:
            curr_ang_vel = {}
            for bname, cq in curr_body_quats.items():
                pq = prev_body_quats.get(bname)
                if pq:
                    ang_vel = quat_angle_between(pq, cq)
                    curr_ang_vel[bname] = ang_vel
                    if ang_vel > m2_worst_ang_vel:
                        m2_worst_ang_vel = ang_vel
                        m2_worst_frame = f

            # Jerk = change in angular velocity
            if prev_body_ang_vel:
                for bname, av in curr_ang_vel.items():
                    pav = prev_body_ang_vel.get(bname, 0.0)
                    jerk = abs(av - pav)
                    if jerk > m2_worst_jerk:
                        m2_worst_jerk = jerk
                        m2_worst_frame = f
                    if jerk > T["M2_jerk_deg"]:
                        m2_jerk_spike_frames.append(f)

            prev_body_ang_vel = curr_ang_vel

        # Anatomical limits: elbow/knee hyperextension
        for bname in ELBOW_BONES + KNEE_BONES:
            pb = arm_obj.pose.bones.get(bname)
            if pb and pb.parent:
                parent_q = get_bone_quat(arm_obj, pb.parent)
                child_q  = get_bone_quat(arm_obj, pb)
                bend_ang = quat_angle_between(parent_q, child_q)
                if bend_ang > T["M2_elbow_knee_limit"]:
                    m2_limit_violations.append({
                        "bone": bname, "frame": f,
                        "angle_deg": round(bend_ang, 2),
                        "limit_deg": T["M2_elbow_knee_limit"]
                    })

        # Spine twist between adjacent spine bones
        spine_quats = []
        for bname in SPINE_BONES:
            pb = arm_obj.pose.bones.get(bname)
            if pb:
                spine_quats.append((bname, get_bone_quat(arm_obj, pb)))
        for i in range(len(spine_quats) - 1):
            n1, q1 = spine_quats[i]
            n2, q2 = spine_quats[i + 1]
            twist = quat_angle_between(q1, q2)
            if twist > T["M2_spine_twist_limit"]:
                m2_limit_violations.append({
                    "bone": f"{n1}->{n2}", "frame": f,
                    "angle_deg": round(twist, 2),
                    "limit_deg": T["M2_spine_twist_limit"]
                })

        prev_body_quats = curr_body_quats

        # ── M3: Foot slide ──────────────────────────────────────────────────
        for bname in FOOT_BONES:
            pb = arm_obj.pose.bones.get(bname)
            if pb:
                hw = get_bone_head_world(arm_obj, pb)
                is_contact = hw.z < T["M3_ground_eps"]
                if is_contact and bname in prev_foot_world:
                    prev_hw = prev_foot_world[bname]
                    slide_xy = Vector((hw.x - prev_hw.x, hw.y - prev_hw.y, 0)).length
                    slide_frac = slide_xy / char_height
                    if slide_frac > m3_worst_slide:
                        m3_worst_slide = slide_frac
                        m3_worst_frame = f
                        m3_worst_foot  = bname
                if is_contact:
                    prev_foot_world[bname] = hw
                else:
                    prev_foot_world.pop(bname, None)

        # ── M4: Sword detach ────────────────────────────────────────────────
        if sword_obj and rh_bone and rest_grip_dist is not None and rest_grip_dist > 1e-6:
            sw_world = sword_obj.matrix_world.translation
            rh_world = get_bone_head_world(arm_obj, rh_bone)
            curr_dist = (sw_world - rh_world).length
            ratio = curr_dist / rest_grip_dist
            if ratio > m4_worst_ratio:
                m4_worst_ratio = ratio
                m4_worst_frame = f

    # ── EVALUATE FAMILIES ───────────────────────────────────────────────────
    m1_pass = (m1_worst_delta <= T["M1_vertex_delta_frac"]) and (m1_worst_bbox <= T["M1_bbox_growth_ratio"])
    # Jerk: only fail if >1 isolated frame (plan says ">1 isolated frame")
    m2_jerk_pass = (m2_worst_jerk <= T["M2_jerk_deg"]) or (len(m2_jerk_spike_frames) <= 1)
    m2_pass = (m2_worst_ang_vel <= T["M2_ang_vel_deg"]) and m2_jerk_pass and (len(m2_limit_violations) == 0)
    m3_pass = (m3_worst_slide <= T["M3_foot_slide_frac"])
    m4_pass = (rest_grip_dist is None) or (m4_worst_ratio <= T["M4_grip_dist_ratio"])

    overall_pass = m1_pass and m2_pass and m3_pass and m4_pass

    # ── M5: Smoothness advisory ─────────────────────────────────────────────
    # 10 - normalized jerk integral (capped at 0)
    # Normalize: if worst jerk is at threshold, score = 5; if 0, score = 10
    jerk_norm = min(m2_worst_jerk / max(T["M2_jerk_deg"], 1.0), 2.0)
    smoothness_m5 = max(0.0, round(10.0 - 5.0 * jerk_norm, 2))

    # ── METRIC FLAWS (prioritized, fixer-consumable) ─────────────────────────
    metric_flaws = []
    if not m1_pass:
        if m1_worst_delta > T["M1_vertex_delta_frac"]:
            metric_flaws.append({
                "issue": f"M1 cape/robe explodes at f{m1_worst_frame:03d} (delta={m1_worst_delta:.3f} > {T['M1_vertex_delta_frac']:.3f}*h)",
                "fix": "Increase phys_cape/phys_robe damping, lower stiffness, tighten per-frame delta clamp",
                "severity": "CRITICAL"
            })
        if m1_worst_bbox > T["M1_bbox_growth_ratio"]:
            metric_flaws.append({
                "issue": f"M1 cloth bounding-box growth {m1_worst_bbox:.2f}x > {T['M1_bbox_growth_ratio']}x rest",
                "fix": "Reduce cloth chain stiffness; add per-frame delta clamp on phys_ chains",
                "severity": "CRITICAL"
            })
    if not m2_pass:
        if m2_worst_ang_vel > T["M2_ang_vel_deg"]:
            metric_flaws.append({
                "issue": f"M2 body teleport/pop at f{m2_worst_frame:03d}: ang-vel {m2_worst_ang_vel:.1f}°/frame > {T['M2_ang_vel_deg']}°",
                "fix": "Add intermediate keyframes to smooth the jump; reduce Euler discontinuities",
                "severity": "HIGH"
            })
        if not m2_jerk_pass:
            metric_flaws.append({
                "issue": f"M2 jerk {m2_worst_jerk:.1f}°/frame² at f{m2_worst_frame:03d} on {len(m2_jerk_spike_frames)} frames",
                "fix": "Smooth out snap transitions with bezier handles or additional easing keys",
                "severity": "HIGH"
            })
        for v in m2_limit_violations[:3]:  # top 3
            metric_flaws.append({
                "issue": f"M2 anatomical limit: {v['bone']} bent {v['angle_deg']}° > {v['limit_deg']}° at f{v['frame']:03d}",
                "fix": f"Constrain {v['bone']} rotation; check IK rest",
                "severity": "MEDIUM"
            })
    if not m3_pass:
        metric_flaws.append({
            "issue": f"M3 foot slide: {m3_worst_foot} slides {m3_worst_slide*char_height*100:.1f}cm/frame at f{m3_worst_frame:03d}",
            "fix": "Add foot IK or locking keyframes during contact phase",
            "severity": "HIGH"
        })
    if not m4_pass:
        metric_flaws.append({
            "issue": f"M4 sword detach at f{m4_worst_frame:03d}: grip dist ratio {m4_worst_ratio:.3f} > {T['M4_grip_dist_ratio']}",
            "fix": "Keep Godwyn_Sword parented to RightHand; do not re-parent; check constraint",
            "severity": "CRITICAL"
        })

    result = {
        "label": label,
        "animName": action.name if action else "unknown",
        "action": action.name if action else None,
        "frameRange": [frame_start, frame_end],
        "characterHeight": round(char_height, 4),
        "families": {
            "M1_cape": {
                "pass": m1_pass,
                "worstFrame": m1_worst_frame,
                "worstDelta": round(m1_worst_delta, 5),
                "bboxGrowth": round(m1_worst_bbox, 4),
                "threshold_delta_frac": T["M1_vertex_delta_frac"],
                "threshold_bbox_ratio": T["M1_bbox_growth_ratio"],
                "cloth_vert_count": len(cloth_verts),
            },
            "M2_body": {
                "pass": m2_pass,
                "worstFrame": m2_worst_frame,
                "worstAngVel": round(m2_worst_ang_vel, 2),
                "worstJerk": round(m2_worst_jerk, 2),
                "jerkSpikeFrames": m2_jerk_spike_frames,
                "limitViolations": m2_limit_violations[:10],
                "threshold_ang_vel": T["M2_ang_vel_deg"],
                "threshold_jerk": T["M2_jerk_deg"],
            },
            "M3_foot": {
                "pass": m3_pass,
                "worstFrame": m3_worst_frame,
                "worstSlide": round(m3_worst_slide, 5),
                "foot": m3_worst_foot,
                "threshold_slide_frac": T["M3_foot_slide_frac"],
                "ground_eps": T["M3_ground_eps"],
            },
            "M4_sword": {
                "pass": m4_pass,
                "worstFrame": m4_worst_frame,
                "worstDistRatio": round(m4_worst_ratio, 4),
                "restGripDist": round(rest_grip_dist, 4) if rest_grip_dist else None,
                "threshold_ratio": T["M4_grip_dist_ratio"],
                "sword_found": sword_obj is not None,
            },
        },
        "overallMetricsPass": overall_pass,
        "smoothnessM5": smoothness_m5,
        "metricFlaws": metric_flaws,
    }
    return result


def run_calibrate(good_glb, bad_glb):
    """Run metrics on good + bad and print suggested thresholds."""
    print("\n=== CALIBRATION MODE ===")
    good = run_metrics(glb=good_glb, label="good")
    bad  = run_metrics(glb=bad_glb,  label="bad")

    print("\n--- GOOD clip metrics ---")
    print(f"  M1 worstDelta: {good['families']['M1_cape']['worstDelta']}")
    print(f"  M1 bboxGrowth: {good['families']['M1_cape']['bboxGrowth']}")
    print(f"  M2 worstAngVel: {good['families']['M2_body']['worstAngVel']}")
    print(f"  M2 worstJerk: {good['families']['M2_body']['worstJerk']}")
    print(f"  M3 worstSlide: {good['families']['M3_foot']['worstSlide']}")
    print(f"  M4 worstDistRatio: {good['families']['M4_sword']['worstDistRatio']}")

    print("\n--- BAD clip metrics ---")
    print(f"  M1 worstDelta: {bad['families']['M1_cape']['worstDelta']}")
    print(f"  M1 bboxGrowth: {bad['families']['M1_cape']['bboxGrowth']}")
    print(f"  M2 worstAngVel: {bad['families']['M2_body']['worstAngVel']}")
    print(f"  M2 worstJerk: {bad['families']['M2_body']['worstJerk']}")
    print(f"  M3 worstSlide: {bad['families']['M3_foot']['worstSlide']}")
    print(f"  M4 worstDistRatio: {bad['families']['M4_sword']['worstDistRatio']}")

    # Suggest: midpoint between good and bad, or good * 1.5 if bad is similar
    def suggest(good_val, bad_val, default):
        if bad_val > good_val * 2:
            return round((good_val + bad_val) / 2, 4)
        return default

    suggested = {
        "M1_vertex_delta_frac": suggest(
            good['families']['M1_cape']['worstDelta'],
            bad['families']['M1_cape']['worstDelta'],
            DEFAULT_THRESHOLDS["M1_vertex_delta_frac"]),
        "M1_bbox_growth_ratio": suggest(
            good['families']['M1_cape']['bboxGrowth'],
            bad['families']['M1_cape']['bboxGrowth'],
            DEFAULT_THRESHOLDS["M1_bbox_growth_ratio"]),
        "M2_ang_vel_deg": suggest(
            good['families']['M2_body']['worstAngVel'],
            bad['families']['M2_body']['worstAngVel'],
            DEFAULT_THRESHOLDS["M2_ang_vel_deg"]),
        "M2_jerk_deg": suggest(
            good['families']['M2_body']['worstJerk'],
            bad['families']['M2_body']['worstJerk'],
            DEFAULT_THRESHOLDS["M2_jerk_deg"]),
        "M3_foot_slide_frac": suggest(
            good['families']['M3_foot']['worstSlide'],
            bad['families']['M3_foot']['worstSlide'],
            DEFAULT_THRESHOLDS["M3_foot_slide_frac"]),
    }
    print("\n--- SUGGESTED THRESHOLDS (defaults if bad ~= good) ---")
    print(json.dumps(suggested, indent=2))
    print("Disagreement with defaults >2x: check OQ-2 and confirm before trusting.")
    return good, bad


def main():
    args = parse_args()

    # Parse optional threshold override
    thresholds = None
    if args.thresholds:
        thresholds = json.loads(args.thresholds)

    if args.calibrate:
        good_glb, bad_glb = args.calibrate
        run_calibrate(good_glb, bad_glb)
        return

    if not args.glb and not args.blend:
        print("ERROR: must provide --glb or --blend")
        sys.exit(1)

    result = run_metrics(
        glb=args.glb,
        blend=args.blend,
        action_name=args.action,
        thresholds=thresholds,
    )

    out_path = os.path.expanduser(args.out)
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"METRICS_JSON:{out_path}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
