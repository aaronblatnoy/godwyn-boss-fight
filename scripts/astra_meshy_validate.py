"""Native, stress, hero, GLB round-trip, and Rising Spin F40 gates for Meshy graft."""
import bpy
import json
import math
import struct
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
CANDIDATE = "models/astra_character_v2_meshy_i01.blend"
GLB = "models/astra_character_v2_meshy_i01.glb"
sys.path.insert(0, str(ROOT / "scripts"))
import astra_likeness_render as renderlib
import astra_cine_hero_render as hero

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
METRICS_ONLY = "metrics" in ARGS


def reset(arm):
    for b in arm.pose.bones:
        b.matrix_basis.identity()
    bpy.context.view_layer.update()


def rotate(arm, name, axis, angle):
    b = arm.pose.bones[name]
    v = (arm.matrix_world.to_3x3() @ b.bone.matrix_local.to_3x3()).inverted() @ Vector(axis)
    b.rotation_mode = "QUATERNION"
    b.rotation_quaternion = Quaternion(v.normalized(), math.radians(angle))


def pose(arm, label):
    reset(arm)
    if label == "arms_raised":
        rotate(arm, "LeftArm", (0, 1, 0), -105)
        rotate(arm, "RightArm", (0, 1, 0), 105)
        rotate(arm, "Head", (0, 0, 1), 10)
    else:
        rotate(arm, "Spine", (0, 0, 1), 24)
        rotate(arm, "Head", (0, 0, 1), -18)
        rotate(arm, "LeftArm", (1, 0, 0), -78)
        rotate(arm, "RightArm", (0, 1, 0), 65)
        rotate(arm, "LeftForeArm", (0, 0, 1), 55)
        rotate(arm, "RightForeArm", (1, 0, 0), -60)
        rotate(arm, "LeftUpLeg", (1, 0, 0), -18)
        rotate(arm, "RightUpLeg", (1, 0, 0), 15)
    bpy.context.view_layer.update()


def evaluated(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    a = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", a)
    a = a.reshape(-1, 3)
    matrix = np.array(ev.matrix_world)
    co = a @ matrix[:3, :3].T + matrix[:3, 3]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return co, faces


def weights_check(objects, arm):
    total = bad = 0
    maximum = 0.0
    examples = []
    for ob in objects:
        if ob.type != "MESH" or not any(m.type == "ARMATURE" for m in ob.modifiers):
            continue
        deform = {g.index: g.name for g in ob.vertex_groups if g.name in arm.data.bones}
        referenced = {i for p in ob.data.polygons for i in p.vertices}
        for i in referenced:
            gs = [g for g in ob.data.vertices[i].groups if g.group in deform and g.weight > 0]
            err = abs(sum(g.weight for g in gs) - 1)
            total += 1
            maximum = max(maximum, err)
            if not gs or err > .003:
                bad += 1
                if len(examples) < 12:
                    examples.append([ob.name, i, err])
    return {"referenced_skinned_vertices": total, "unweighted_or_bad_sum_vertices": bad,
            "weight_sum_max_error": maximum, "bad_examples": examples}


def draw(scene, label):
    scene.camera.location = (3, -8, 3.5)
    renderlib.aim(scene.camera, (0, -.05, 1.75))
    scene.camera.data.ortho_scale = 4.1
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.filepath = str(OUT / f"{label}.png")
    bpy.ops.render.render(write_still=True)


def stress(arm, label):
    names = ["AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend"]
    obs = [bpy.data.objects[n] for n in names if n in bpy.data.objects]
    reset(arm)
    rest = {o.name: evaluated(o)[0] for o in obs}
    edges = {o.name: np.array([e.vertices[:] for e in o.data.edges], int) for o in obs}
    scene = None
    devices = []
    if not METRICS_ONLY:
        scene, devices = renderlib.studio()
        scene.cycles.samples = 32
    result = {"optix_devices": devices}
    for label_pose in ("arms_raised", "combat_stress"):
        pose(arm, label_pose)
        result[label_pose] = {}
        for ob in obs:
            after = evaluated(ob)[0]
            before = rest[ob.name]
            e = edges[ob.name]
            assert np.isfinite(after).all() and np.max(np.abs(after)) < 10
            a = np.linalg.norm(before[e[:, 0]] - before[e[:, 1]], axis=1)
            b = np.linalg.norm(after[e[:, 0]] - after[e[:, 1]], axis=1)
            ratio = b[a > .0003] / a[a > .0003]
            result[label_pose][ob.name] = {"edge_stretch_max": float(ratio.max()),
                "edge_stretch_p99": float(np.quantile(ratio, .99))}
            print("MESHY_STRESS_METRIC", label_pose, ob.name, float(ratio.max()), flush=True)
            assert ratio.max() < 100
        if not METRICS_ONLY:
            draw(scene, f"meshy_{label}_{label_pose}")
    reset(arm)
    return result


def validate_native():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / CANDIDATE))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    baseline = json.loads((OUT / "mpfb_baseline.json").read_text())["bones"]
    rest_error = max(float(np.max(np.abs(np.array(b.matrix_local) - np.array(baseline[b.name]["rest"])))) for b in arm.data.bones)
    report = {"source": CANDIDATE, "bones": len(arm.data.bones), "actions": len(bpy.data.actions),
              "rest_matrix_error": rest_error, "meshy_head_present": "AstraChar2_Meshy_HeadHair" in bpy.data.objects,
              "legacy_head_absent": "AstraChar2_Mpfb_Head" not in bpy.data.objects}
    assert report["bones"] == 121 and report["actions"] == 0 and rest_error == 0
    assert report["meshy_head_present"] and report["legacy_head_absent"]
    visible = [o for o in bpy.context.scene.objects if not o.hide_render]
    report["weights"] = weights_check(visible, arm)
    assert report["weights"]["unweighted_or_bad_sum_vertices"] == 0
    report["poses"] = stress(arm, "native")
    report["neutral_restored"] = all(np.allclose(np.array(b.matrix_basis), np.eye(4), atol=1e-6) for b in arm.pose.bones)
    (OUT / "meshy_native_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_NATIVE_PASS", flush=True)


def export_glb():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / CANDIDATE))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for ob in bpy.context.scene.objects:
        asset = ob.name.startswith("AstraChar2_") or ob.name in {"char1", "Astra_Undersleeves", "Godwyn_Sword"}
        include = ob == arm or (asset and ob.type == "MESH" and len(ob.data.polygons) and not ob.hide_render)
        if include:
            ob.hide_set(False)
            ob.hide_render = False
            ob.select_set(True)
            selected.append(ob.name)
    bpy.context.view_layer.objects.active = arm
    options = dict(filepath=str(ROOT / GLB), export_format="GLB", use_selection=True,
        export_animations=False, export_skins=True, export_def_bones=False, export_leaf_bone=False,
        export_apply=True, export_texcoords=True, export_normals=True, export_materials="EXPORT",
        export_all_influences=False, export_cameras=False, export_lights=False)
    valid = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    options = {k: v for k, v in options.items() if k in valid}
    bpy.ops.export_scene.gltf(**options)
    (OUT / "meshy_export.json").write_text(json.dumps({"source": CANDIDATE, "output": GLB,
        "selected_objects": selected, "options": options}, indent=2) + "\n")
    print("MESHY_EXPORT_PASS", flush=True)


def validate_roundtrip():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / GLB))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    reset(arm)
    baseline = json.loads((OUT / "mpfb_baseline.json").read_text())["bones"]
    errors = {b.name: float(np.max(np.abs(np.array(arm.matrix_world @ b.head_local) - np.array(baseline[b.name]["head"])))) for b in arm.data.bones}
    data = (ROOT / GLB).read_bytes()
    n = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20+n])
    report = {"source": GLB, "bones": len(arm.data.bones), "actions": len(bpy.data.actions),
        "world_joint_position_max_error_m": max(errors.values()), "world_joint_position_tolerance_m": .00005,
        "bone_names_and_hierarchy_preserved": all((b.parent.name if b.parent else None) == baseline[b.name]["parent"] for b in arm.data.bones),
        "glb_skin_joint_counts": [len(s["joints"]) for s in gltf["skins"]], "glb_animations": len(gltf.get("animations", []))}
    assert report["bones"] == 121 and report["actions"] == 0
    assert report["world_joint_position_max_error_m"] < .00005 and report["bone_names_and_hierarchy_preserved"]
    assert all(x == 121 for x in report["glb_skin_joint_counts"]) and not report["glb_animations"]
    report["weights"] = weights_check([o for o in bpy.context.scene.objects if not o.hide_render], arm)
    assert report["weights"]["unweighted_or_bad_sum_vertices"] == 0
    report["poses"] = stress(arm, "roundtrip")
    report["neutral_restored"] = all(np.allclose(np.array(b.matrix_basis), np.eye(4), atol=1e-6) for b in arm.pose.bones)
    (OUT / "meshy_roundtrip_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_ROUNDTRIP_PASS", flush=True)


def hero_gate():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "models/astra_character_v2_collar_banked.blend"))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    for ob in list(bpy.data.objects):
        if ob != arm:
            bpy.data.objects.remove(ob, do_unlink=True)
    bone = arm.pose.bones["Head"]
    bone.rotation_mode = "XYZ"
    bone.keyframe_insert("rotation_euler", frame=1)
    bone.rotation_euler.z = .10
    bone.keyframe_insert("rotation_euler", frame=2)
    fixture = Path("/tmp/astra_meshy_hero_fixture.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(fixture))
    scene, result = hero.assemble_inputs(fixture, ROOT / CANDIDATE)
    result["meshy_head_present"] = "AstraChar2_Meshy_HeadHair" in scene.objects
    result["bones"] = len(scene.objects["Armature"].data.bones)
    result["armature_modifier_targets_valid"] = all(m.object == scene.objects["Armature"] for ob in scene.objects for m in ob.modifiers if m.type == "ARMATURE")
    assert result["meshy_head_present"] and result["bones"] == 121
    assert result["rest_transform_max_error"] == 0 and result["armature_modifier_targets_valid"]
    (OUT / "meshy_hero_assembly.json").write_text(json.dumps(result, indent=2) + "\n")
    print("MESHY_HERO_PASS", flush=True)


def original_name(name):
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def rising_spin():
    animation = ROOT / "models/astra_move_rising_spin_v2_wip.blend"
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / CANDIDATE))
    character_scene = bpy.context.scene
    objects = [o for o in character_scene.objects if o.type not in {"LIGHT", "CAMERA"} and o.name != "Astra evaluation ground"]
    rig = bpy.data.objects["Armature"]
    with bpy.data.libraries.load(str(animation), link=False) as (src, dst):
        dst.scenes = src.scenes[:]
    scene = dst.scenes[0]
    bpy.context.window.scene = scene
    old_rig = next(o for o in scene.objects if o.type == "ARMATURE")
    old_body = next(o for o in scene.objects if original_name(o.name) == "char1")
    old_sword = next(o for o in scene.objects if original_name(o.name) == "Godwyn_Sword")
    old_under = next((o for o in scene.objects if original_name(o.name) == "Astra_Undersleeves"), None)
    old_assets = [o for o in list(scene.objects) if o.type not in {"CAMERA", "LIGHT"} and o.name != "Astra evaluation ground"]
    action = old_rig.animation_data.action
    rest_error = max(abs(old_rig.data.bones[n].matrix_local[i][j] - rig.data.bones[n].matrix_local[i][j]) for n in old_rig.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0
    for ob in objects:
        scene.collection.objects.link(ob)
    rig.animation_data_create()
    transferred = action.copy()
    transferred.name = action.name + "_MeshyProof"
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    for ob in old_assets:
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    scene.frame_set(40)
    bpy.context.view_layer.update()
    head = scene.objects["AstraChar2_Meshy_HeadHair"]
    sword = scene.objects["Godwyn_Sword"]
    co, faces = evaluated(head)
    local = np.array([v.co[:] for v in head.data.vertices], float)
    raw = (local - np.array((.00043, -.2519, 2.8552))) / .31
    head_faces, hair_faces = [], []
    for face in faces:
        c = raw[list(face)].mean(0)
        skin = abs(c[0]) < .37 and c[1] < -.16 and -.48 < c[2] < .73
        (head_faces if skin else hair_faces).append(face)
    neck = scene.objects["AstraChar2_Meshy_NeckBlend"]
    nco, nfaces = evaluated(neck)
    offset = len(co)
    head_co = np.vstack((co, nco))
    head_faces += [tuple(offset + i for i in f) for f in nfaces]
    hb = BVHTree.FromPolygons(head_co.tolist(), head_faces)
    hairb = BVHTree.FromPolygons(co.tolist(), hair_faces)
    source = np.array([p.vector[:] for p in sword.data.attributes["astra_sword_source"].data])
    sco, sfaces = evaluated(sword)
    blade_ids = set(int(i) for i in np.where(source[:, 2] < 150)[0])
    blade_faces = [f for f in sfaces if all(i in blade_ids for i in f)]
    bb = BVHTree.FromPolygons(sco.tolist(), blade_faces)
    head_overlap = hb.overlap(bb)
    hair_overlap = hairb.overlap(bb)
    def clearance(tree, points):
        return min((tree.find_nearest(Vector(p))[3] for p in points), default=float("inf"))
    blade_samples = sco[sorted(blade_ids)[::3]]
    head_distance = min(clearance(hb, blade_samples), clearance(bb, head_co[::12]))
    hair_distance = min(clearance(hairb, blade_samples), clearance(bb, co[::12]))
    if head_overlap: head_distance = 0.0
    if hair_overlap: hair_distance = 0.0
    print("MESHY_RISING_RAW", len(head_overlap), len(hair_overlap), head_distance, hair_distance, flush=True)
    if hair_overlap:
        samples = []
        for hi, bi in hair_overlap[:12]:
            samples.append({"hair_world": co[list(hair_faces[hi])].mean(0).tolist(), "blade_world": sco[list(blade_faces[bi])].mean(0).tolist()})
        print("MESHY_RISING_OVERLAP_SAMPLES", json.dumps(samples), flush=True)
    assert not head_overlap and not hair_overlap and head_distance > 0 and hair_distance > 0
    devices = []
    if not METRICS_ONLY:
        for ob in list(scene.objects):
            if ob.type in {"CAMERA", "LIGHT"}:
                bpy.data.objects.remove(ob, do_unlink=True)
        scene, devices = renderlib.studio()
        target = co.mean(0)
        scene.camera.data.type = "ORTHO"
        scene.camera.data.ortho_scale = 1.42
        scene.camera.location = Vector(target) + Vector((3.15, -5.6, 1.20))
        renderlib.aim(scene.camera, target + np.array((0, 0, -.10)))
        scene.render.resolution_x = scene.render.resolution_y = 1000
        scene.render.filepath = str(OUT / "meshy_rising_spin_f040.png")
        bpy.ops.render.render(write_still=True)
    report = {"animation": str(animation.relative_to(ROOT)), "candidate": CANDIDATE, "frame": 40,
        "blade_head_exact_triangle_overlaps": len(head_overlap), "blade_hair_exact_triangle_overlaps": len(hair_overlap),
        "blade_head_exact_sampled_surface_distance_m": float(head_distance),
        "blade_hair_exact_sampled_surface_distance_m": float(hair_distance),
        "fused_mesh_partition": "Geometric triangle partition: central anterior skin envelope plus neck band=head; remainder=hair. No fiber allowance.",
        "head_triangles": len(head_faces), "hair_triangles": len(hair_faces),
        "assembly_rest_transform_max_error": rest_error, "bones": len(rig.data.bones), "optix_devices": devices}
    (OUT / "meshy_rising_spin_clearance.json").write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_RISING_SPIN_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    stage = ARGS[0]
    {"native": validate_native, "export": export_glb, "roundtrip": validate_roundtrip,
     "hero": hero_gate, "rising": rising_spin}[stage]()
