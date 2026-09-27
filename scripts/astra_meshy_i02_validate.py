"""Numeric-only validation for Meshy graft iteration 02.

No render operator is called.  Stages: native, export, roundtrip, rising, notes,
or all (default).  The stress poses are evaluated numerically and reset.
"""
import bpy
import hashlib
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
CANDIDATE = ROOT / "models/astra_character_v2_meshy_i02.blend"
GLB = ROOT / "models/astra_character_v2_meshy_i02.glb"
BASELINE = OUT / "mpfb_baseline.json"
VALIDATION = OUT / "meshy_i02_validation.json"
ROUNDTRIP = OUT / "meshy_i02_roundtrip.json"
RISING = OUT / "meshy_i02_rising_spin.json"
NOTES = OUT / "MESHY_GRAFT_I02_NOTES.md"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPEC_SKIN = np.array((0.95, 0.90, 0.82), dtype=np.float32)
SKIN_HUE = 0.485
SKIN_SATURATION = 1.15
SKIN_VALUE = 0.92


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reset(arm):
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def rotate(arm, name, axis, angle_deg):
    bone = arm.pose.bones[name]
    local_axis = (arm.matrix_world.to_3x3() @ bone.bone.matrix_local.to_3x3()).inverted() @ Vector(axis)
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = Quaternion(local_axis.normalized(), math.radians(angle_deg))


def apply_pose(arm, label):
    reset(arm)
    if label == "arms_raised":
        rotate(arm, "LeftArm", (0, 1, 0), -105)
        rotate(arm, "RightArm", (0, 1, 0), 105)
        rotate(arm, "Head", (0, 0, 1), 10)
    elif label == "combat_stress":
        rotate(arm, "Spine", (0, 0, 1), 24)
        rotate(arm, "Head", (0, 0, 1), -18)
        rotate(arm, "LeftArm", (1, 0, 0), -78)
        rotate(arm, "RightArm", (0, 1, 0), 65)
        rotate(arm, "LeftForeArm", (0, 0, 1), 55)
        rotate(arm, "RightForeArm", (1, 0, 0), -60)
        rotate(arm, "LeftUpLeg", (1, 0, 0), -18)
        rotate(arm, "RightUpLeg", (1, 0, 0), 15)
    else:
        raise ValueError(label)
    bpy.context.view_layer.update()


def evaluated(ob):
    evaluated_ob = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated_ob.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.array(evaluated_ob.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    faces = [tuple(poly.vertices) for poly in mesh.polygons]
    evaluated_ob.to_mesh_clear()
    return coords, faces


def weight_check(objects, arm):
    total = 0
    bad = 0
    maximum = 0.0
    examples = []
    for ob in objects:
        if ob.type != "MESH" or not any(mod.type == "ARMATURE" for mod in ob.modifiers):
            continue
        deform = {group.index: group.name for group in ob.vertex_groups if group.name in arm.data.bones}
        referenced = {int(index) for poly in ob.data.polygons for index in poly.vertices}
        for index in referenced:
            groups = [group for group in ob.data.vertices[index].groups if group.group in deform and group.weight > 0]
            error = abs(sum(group.weight for group in groups) - 1.0)
            total += 1
            maximum = max(maximum, error)
            if not groups or error > 0.003:
                bad += 1
                if len(examples) < 12:
                    examples.append([ob.name, index, error])
    return {"referenced_skinned_vertices": total, "unweighted_or_bad_sum_vertices": bad,
            "weight_sum_max_error": maximum, "bad_examples": examples}


def stress_metrics(arm):
    names = ("AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend")
    objects = [bpy.data.objects[name] for name in names]
    reset(arm)
    rest = {ob.name: evaluated(ob)[0] for ob in objects}
    edges = {ob.name: np.array([edge.vertices[:] for edge in ob.data.edges], dtype=int) for ob in objects}
    result = {"rendering": "disabled; numeric evaluated-mesh checks only"}
    for label in ("arms_raised", "combat_stress"):
        apply_pose(arm, label)
        result[label] = {}
        for ob in objects:
            after = evaluated(ob)[0]
            before = rest[ob.name]
            edge_ids = edges[ob.name]
            assert len(after) == len(before)
            assert np.isfinite(after).all() and float(np.max(np.abs(after))) < 10.0
            before_lengths = np.linalg.norm(before[edge_ids[:, 0]] - before[edge_ids[:, 1]], axis=1)
            after_lengths = np.linalg.norm(after[edge_ids[:, 0]] - after[edge_ids[:, 1]], axis=1)
            usable = before_lengths > 0.0003
            ratios = after_lengths[usable] / before_lengths[usable]
            result[label][ob.name] = {
                "edge_count_tested": int(usable.sum()),
                "edge_stretch_max": float(ratios.max()),
                "edge_stretch_p99": float(np.quantile(ratios, 0.99)),
            }
            assert float(ratios.max()) < 2.0
            print("MESHY_I02_STRESS", label, ob.name, float(ratios.max()), flush=True)
    reset(arm)
    result["neutral_restored"] = all(np.allclose(np.array(bone.matrix_basis), np.eye(4), atol=1.0e-6) for bone in arm.pose.bones)
    assert result["neutral_restored"]
    return result


def native_validation():
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    baseline = json.loads(BASELINE.read_text())["bones"]
    rest_error = max(float(np.max(np.abs(np.array(bone.matrix_local) - np.array(baseline[bone.name]["rest"])))) for bone in arm.data.bones)
    report = {
        "source": str(CANDIDATE.relative_to(ROOT)),
        "source_bytes": CANDIDATE.stat().st_size,
        "source_sha256": sha256(CANDIDATE),
        "bones": len(arm.data.bones),
        "actions": len(bpy.data.actions),
        "rest_matrix_error": rest_error,
        "meshy_head_present": "AstraChar2_Meshy_HeadHair" in bpy.data.objects,
        "legacy_head_absent": "AstraChar2_Mpfb_Head" not in bpy.data.objects,
        "numeric_only": True,
        "render_calls": 0,
    }
    assert report["bones"] == 121 and report["actions"] == 0 and report["rest_matrix_error"] == 0.0
    assert report["meshy_head_present"] and report["legacy_head_absent"]
    report["weights"] = weight_check([ob for ob in bpy.context.scene.objects if not ob.hide_render], arm)
    assert report["weights"]["unweighted_or_bad_sum_vertices"] == 0
    report["poses"] = stress_metrics(arm)
    cut = json.loads((OUT / "meshy_i02_cut_audit.json").read_text())
    report["cut_gate"] = {
        "cut_plane_margin_below_visible_rim_m": cut["cut_plane_margin_below_visible_rim_m"],
        "minimum_required_margin_m": cut["minimum_required_margin_m"],
        "planar_cut_pass": cut["planar_cut_pass"],
        "cap_or_bridge_pass": cut["cap"]["cap_or_bridge_pass"],
        "skin_cut_boundary_vertices_above_rim_minus_25mm": cut["skin_cut_boundary_vertices_above_rim_minus_25mm"],
        "skin_cut_boundary_outside_inner_radius_above_rim_violations": cut["skin_cut_boundary_outside_inner_radius_above_rim_violations"],
        "hair_full_length_preserved_except_explicit_sub15mm_floating_rule": cut["classification"]["hair_full_length_preserved_except_explicit_sub15mm_floating_rule"],
    }
    assert report["cut_gate"]["planar_cut_pass"]
    assert report["cut_gate"]["cap_or_bridge_pass"]
    assert report["cut_gate"]["skin_cut_boundary_vertices_above_rim_minus_25mm"] == 0
    assert report["cut_gate"]["skin_cut_boundary_outside_inner_radius_above_rim_violations"] == 0
    assert report["cut_gate"]["hair_full_length_preserved_except_explicit_sub15mm_floating_rule"]
    VALIDATION.write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_I02_NATIVE_PASS", json.dumps({"bones": report["bones"], "rest": rest_error,
          "unweighted": report["weights"]["unweighted_or_bad_sum_vertices"]}), flush=True)


def corrected_skin_pixels(source):
    pixels = np.asarray(source.pixels[:], dtype=np.float32).reshape(-1, 4).copy()
    rgb = np.clip(pixels[:, :3] * SPEC_SKIN[None, :], 0.0, None)
    maximum = rgb.max(axis=1)
    minimum = rgb.min(axis=1)
    delta = maximum - minimum
    hue = np.zeros(len(rgb), dtype=np.float32)
    nonzero = delta > 1.0e-12
    red = nonzero & (maximum == rgb[:, 0])
    green = nonzero & (maximum == rgb[:, 1])
    blue = nonzero & (maximum == rgb[:, 2])
    hue[red] = np.mod((rgb[red, 1] - rgb[red, 2]) / delta[red], 6.0)
    hue[green] = (rgb[green, 2] - rgb[green, 0]) / delta[green] + 2.0
    hue[blue] = (rgb[blue, 0] - rgb[blue, 1]) / delta[blue] + 4.0
    hue = np.mod(hue / 6.0 + (SKIN_HUE - 0.5), 1.0)
    saturation = np.zeros(len(rgb), dtype=np.float32)
    positive = maximum > 1.0e-12
    saturation[positive] = delta[positive] / maximum[positive]
    saturation = np.clip(saturation * SKIN_SATURATION, 0.0, 1.0)
    value = np.clip(maximum * SKIN_VALUE, 0.0, 1.0)
    sector = np.floor(hue * 6.0).astype(np.int32)
    fraction = hue * 6.0 - sector
    p = value * (1.0 - saturation)
    q = value * (1.0 - fraction * saturation)
    t = value * (1.0 - (1.0 - fraction) * saturation)
    converted = np.empty_like(rgb)
    choices = sector % 6
    converted[choices == 0] = np.stack((value, t, p), axis=1)[choices == 0]
    converted[choices == 1] = np.stack((q, value, p), axis=1)[choices == 1]
    converted[choices == 2] = np.stack((p, value, t), axis=1)[choices == 2]
    converted[choices == 3] = np.stack((p, q, value), axis=1)[choices == 3]
    converted[choices == 4] = np.stack((t, p, value), axis=1)[choices == 4]
    converted[choices == 5] = np.stack((value, p, q), axis=1)[choices == 5]
    pixels[:, :3] = converted
    return pixels.reshape(-1)


def direct_base_color(mat, image):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    source = next(node for node in nodes if node.type == "TEX_IMAGE" and node.image and node.image.name.startswith("Image_0"))
    source.image = image
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)
    links.new(source.outputs["Color"], bsdf.inputs["Base Color"])
    for name in ("Meshy i02 SPEC multiply", "Meshy i02 warm HSV", "Meshy i02 skin mask", "Meshy i02 skin mix"):
        node = nodes.get(name)
        if node:
            nodes.remove(node)


def prepare_glb_safe_meshy_materials():
    ob = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    skin_attr = ob.data.color_attributes["meshy_skin_mask"]
    source_mat = ob.data.materials[0]
    image_node = next(node for node in source_mat.node_tree.nodes if node.type == "TEX_IMAGE" and node.image and node.image.name.startswith("Image_0"))
    source_image = image_node.image
    hair_mat = source_mat.copy()
    hair_mat.name = "AstraChar2 Meshy i02 original hair and non-skin PBR"
    direct_base_color(hair_mat, source_image)
    skin_image = bpy.data.images.new("Image_0_Meshy_i02_skin_corrected", width=source_image.size[0], height=source_image.size[1], alpha=True)
    skin_image.colorspace_settings.name = source_image.colorspace_settings.name
    skin_image.pixels.foreach_set(corrected_skin_pixels(source_image))
    skin_image.pack()
    skin_mat = source_mat.copy()
    skin_mat.name = "AstraChar2 Meshy i02 corrected skin PBR"
    direct_base_color(skin_mat, skin_image)
    ob.data.materials.clear()
    ob.data.materials.append(hair_mat)
    ob.data.materials.append(skin_mat)
    skin_faces = 0
    for poly in ob.data.polygons:
        is_skin = np.mean([skin_attr.data[index].color[0] for index in poly.loop_indices]) >= 0.5
        poly.material_index = 1 if is_skin else 0
        skin_faces += int(is_skin)
    assert skin_faces > 0 and skin_faces < len(ob.data.polygons)
    return {"skin_faces": skin_faces, "other_faces": len(ob.data.polygons) - skin_faces,
            "skin_image": skin_image.name, "hair_image": source_image.name,
            "hair_material": hair_mat.name, "skin_material": skin_mat.name}


def export_glb():
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    material_export = prepare_glb_safe_meshy_materials()
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
    options = dict(filepath=str(GLB), export_format="GLB", use_selection=True,
                   export_animations=False, export_skins=True, export_def_bones=False,
                   export_leaf_bone=False, export_apply=True, export_texcoords=True,
                   export_normals=True, export_materials="EXPORT", export_all_influences=False,
                   export_cameras=False, export_lights=False)
    valid = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    options = {key: value for key, value in options.items() if key in valid}
    bpy.ops.export_scene.gltf(**options)
    assert GLB.exists() and GLB.stat().st_size > 0
    print("MESHY_I02_EXPORT_PASS", GLB.stat().st_size, sha256(GLB), json.dumps(material_export), flush=True)


def glb_json(path):
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    json_length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + json_length])


def roundtrip_validation():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    arm = next(ob for ob in bpy.data.objects if ob.type == "ARMATURE")
    reset(arm)
    baseline = json.loads(BASELINE.read_text())["bones"]
    errors = {
        bone.name: float(np.max(np.abs(np.array(arm.matrix_world @ bone.head_local) - np.array(baseline[bone.name]["head"]))))
        for bone in arm.data.bones
    }
    gltf = glb_json(GLB)
    report = {
        "source": str(GLB.relative_to(ROOT)),
        "source_bytes": GLB.stat().st_size,
        "source_sha256": sha256(GLB),
        "bones": len(arm.data.bones),
        "actions": len(bpy.data.actions),
        "world_joint_position_max_error_m": max(errors.values()),
        "world_joint_position_tolerance_m": 0.00005,
        "bone_names_and_hierarchy_preserved": all(
            (bone.parent.name if bone.parent else None) == baseline[bone.name]["parent"] for bone in arm.data.bones
        ),
        "glb_skin_joint_counts": [len(skin["joints"]) for skin in gltf.get("skins", [])],
        "glb_animations": len(gltf.get("animations", [])),
        "numeric_only": True,
        "render_calls": 0,
        "materials": [material.get("name") for material in gltf.get("materials", [])],
        "images": [image.get("name") for image in gltf.get("images", [])],
    }
    assert report["bones"] == 121 and report["actions"] == 0
    assert report["world_joint_position_max_error_m"] < report["world_joint_position_tolerance_m"]
    assert report["bone_names_and_hierarchy_preserved"]
    assert report["glb_skin_joint_counts"] and all(count == 121 for count in report["glb_skin_joint_counts"])
    assert report["glb_animations"] == 0
    assert "AstraChar2 Meshy i02 original hair and non-skin PBR" in report["materials"]
    assert "AstraChar2 Meshy i02 corrected skin PBR" in report["materials"]
    meshy_materials = {
        material["name"]: {
            "base_color_texture": "baseColorTexture" in material.get("pbrMetallicRoughness", {}),
            "metallic_roughness_texture": "metallicRoughnessTexture" in material.get("pbrMetallicRoughness", {}),
            "normal_texture": "normalTexture" in material,
            "emissive_texture": "emissiveTexture" in material,
        }
        for material in gltf.get("materials", []) if "Meshy i02" in material.get("name", "")
        and "skin blend" not in material.get("name", "")
    }
    assert len(meshy_materials) == 2
    assert all(all(slots.values()) for slots in meshy_materials.values())
    report["meshy_material_export"] = {
        "mask_source": "meshy_skin_mask face-corner attribute from the build classification",
        "hair_base_color_unchanged": True,
        "skin_texture_correction": {"multiply_rgb": SPEC_SKIN.tolist(), "hue": SKIN_HUE,
                                    "saturation": SKIN_SATURATION, "value": SKIN_VALUE},
        "glb_safe_face_material_split": True,
        "roundtrip_texture_slots": meshy_materials,
    }
    report["weights"] = weight_check([ob for ob in bpy.context.scene.objects if not ob.hide_render], arm)
    assert report["weights"]["unweighted_or_bad_sum_vertices"] == 0
    report["poses"] = stress_metrics(arm)
    ROUNDTRIP.write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_I02_ROUNDTRIP_PASS", json.dumps({"bones": report["bones"],
          "joint_error_m": report["world_joint_position_max_error_m"], "unweighted": report["weights"]["unweighted_or_bad_sum_vertices"]}), flush=True)


def original_name(name):
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def face_hair_flags(ob):
    attr = ob.data.color_attributes.get("meshy_hair_mask")
    if not attr:
        raise RuntimeError("Native candidate lacks meshy_hair_mask")
    flags = []
    for poly in ob.data.polygons:
        mean = np.mean([attr.data[li].color[0] for li in poly.loop_indices])
        flags.append(bool(mean >= 0.5))
    return flags


def nearest_distance(tree, points):
    return min((tree.find_nearest(Vector(point))[3] for point in points), default=float("inf"))


def rising_spin_validation():
    animation = ROOT / "models/astra_move_rising_spin_v2_wip.blend"
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    character_scene = bpy.context.scene
    objects = [ob for ob in character_scene.objects if ob.type not in {"LIGHT", "CAMERA"} and ob.name != "Astra evaluation ground"]
    rig = bpy.data.objects["Armature"]
    hair_flags = face_hair_flags(bpy.data.objects["AstraChar2_Meshy_HeadHair"])
    with bpy.data.libraries.load(str(animation), link=False) as (source, target):
        target.scenes = source.scenes[:]
    scene = target.scenes[0]
    bpy.context.window.scene = scene
    old_rig = next(ob for ob in scene.objects if ob.type == "ARMATURE")
    old_assets = [ob for ob in list(scene.objects) if ob.type not in {"CAMERA", "LIGHT"} and ob.name != "Astra evaluation ground"]
    action = old_rig.animation_data.action
    rest_error = max(abs(old_rig.data.bones[name].matrix_local[i][j] - rig.data.bones[name].matrix_local[i][j])
                     for name in old_rig.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0.0
    for ob in objects:
        scene.collection.objects.link(ob)
    rig.animation_data_create()
    transferred = action.copy()
    transferred.name = action.name + "_MeshyI02Proof"
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    for ob in old_assets:
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    scene.frame_set(40)
    bpy.context.view_layer.update()

    head = scene.objects["AstraChar2_Meshy_HeadHair"]
    sword = scene.objects["Godwyn_Sword"]
    coords, faces = evaluated(head)
    assert len(faces) == len(hair_flags)
    head_faces = [face for face, is_hair in zip(faces, hair_flags) if not is_hair]
    hair_faces = [face for face, is_hair in zip(faces, hair_flags) if is_hair]
    neck = scene.objects["AstraChar2_Meshy_NeckBlend"]
    neck_coords, neck_faces = evaluated(neck)
    offset = len(coords)
    head_coords = np.vstack((coords, neck_coords))
    head_faces.extend(tuple(offset + index for index in face) for face in neck_faces)
    head_bvh = BVHTree.FromPolygons(head_coords.tolist(), head_faces)
    hair_bvh = BVHTree.FromPolygons(coords.tolist(), hair_faces)

    source_attr = np.array([entry.vector[:] for entry in sword.data.attributes["astra_sword_source"].data])
    sword_coords, sword_faces = evaluated(sword)
    blade_ids = set(int(index) for index in np.where(source_attr[:, 2] < 150)[0])
    blade_faces = [face for face in sword_faces if all(index in blade_ids for index in face)]
    blade_bvh = BVHTree.FromPolygons(sword_coords.tolist(), blade_faces)
    head_overlap = head_bvh.overlap(blade_bvh)
    hair_overlap = hair_bvh.overlap(blade_bvh)
    blade_samples = sword_coords[sorted(blade_ids)[::3]]
    head_distance = min(nearest_distance(head_bvh, blade_samples), nearest_distance(blade_bvh, head_coords[::12]))
    hair_distance = min(nearest_distance(hair_bvh, blade_samples), nearest_distance(blade_bvh, coords[::12]))
    if head_overlap:
        head_distance = 0.0
    if hair_overlap:
        hair_distance = 0.0
    report = {
        "animation": str(animation.relative_to(ROOT)),
        "candidate": str(CANDIDATE.relative_to(ROOT)),
        "frame": 40,
        "blade_head_exact_triangle_overlaps": len(head_overlap),
        "blade_hair_exact_triangle_overlaps": len(hair_overlap),
        "blade_head_sampled_surface_distance_m": float(head_distance),
        "blade_hair_sampled_surface_distance_m": float(hair_distance),
        "mesh_partition": "meshy_hair_mask face-corner attribute; complement plus neck band is head/skin/other",
        "head_triangles_or_polygons": len(head_faces),
        "hair_triangles_or_polygons": len(hair_faces),
        "blade_triangles_or_polygons": len(blade_faces),
        "assembly_rest_transform_max_error": rest_error,
        "bones": len(rig.data.bones),
        "numeric_only": True,
        "render_calls": 0,
    }
    assert report["bones"] == 121 and not head_overlap and not hair_overlap
    assert head_distance > 0.0 and hair_distance > 0.0
    RISING.write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_I02_RISING_PASS", json.dumps(report), flush=True)


def fmt(value, digits=9):
    return f"{float(value):.{digits}f}"


def write_notes():
    cut = json.loads((OUT / "meshy_i02_cut_audit.json").read_text())
    validation = json.loads(VALIDATION.read_text())
    roundtrip = json.loads(ROUNDTRIP.read_text())
    rising = json.loads(RISING.read_text())
    poses = validation["poses"]
    rtposes = roundtrip["poses"]
    material = cut["material_correction"]
    shards = cut["gorget_shards"]
    text = f"""# Meshy graft iteration 02 — geometry/material notes

## Outcome

Iteration 02 was built as new, unpublished candidate files. The published `models/astra_character_v2.blend/.glb`, iteration-01 files, and `models/astra_character_v2_pre_likeness.blend` were treated as read-only. No render engine was invoked; every check in this pass is numeric.

- Blend: `models/astra_character_v2_meshy_i02.blend` — {validation['source_bytes']:,} bytes, SHA-256 `{validation['source_sha256']}`.
- GLB: `models/astra_character_v2_meshy_i02.glb` — {roundtrip['source_bytes']:,} bytes, SHA-256 `{roundtrip['source_sha256']}`.
- Publication status: **NOT PUBLISHED**.

## Geometry changes

- Rebuilt from the untouched Meshy GLB and the protected pre-likeness body instead of editing the defective i01 result.
- Measured the visible gorget upper rim from `{cut['rim_measurement']['object']}` at z={fmt(cut['rim_measurement']['visible_upper_rim_z_m'])} m.
- Applied one planar non-hair bisect at z={fmt(cut['cut_plane_z_m'])} m, {fmt(cut['cut_plane_margin_below_visible_rim_m'] * 1000, 3)} mm below the rim (minimum required: 25 mm).
- The source's disconnected cut segments yielded {cut['cap']['cap_faces_created']} direct `holes_fill` faces across {cut['cap']['cut_plane_vertices']} cut-plane vertices. The overlapping 9×64 Spine/neck/Head blend band starts on the same plane and supplies a closed {cut['cap']['neck_blend_planar_cap_faces']}-triangle planar bottom cap, satisfying the cap/bridge gate.
- Classified {cut['classification']['hair_faces']:,} hair faces and did not pass them through the bust bisect. Hair z-min changed by {cut['classification']['hair_z_min_change_m']} m and z-max by {cut['classification']['hair_z_max_change_m']} m; any nonzero lower-bound change is limited to the {cut['floating_hair_components_removed']} disconnected components removed under the explicit rule: entire bounding box below the cut plane and maximum dimension <15 mm.
- Hair classification thresholds: luma ≤{cut['classification']['hair_thresholds']['ordinary_luma_max']} (strong capture ≤{cut['classification']['hair_thresholds']['strong_luma_max']}), R−B ≥{cut['classification']['hair_thresholds']['r_minus_b_min']}, G−B ≥{cut['classification']['hair_thresholds']['g_minus_b_min']}, plus the documented outside-head-core geometry envelope in `meshy_i02_cut_audit.json`.
- Angular cut audit: {len(cut['skin_cut_boundary_by_angular_sector'])} sectors; cut-boundary vertices above rim−25 mm: {cut['skin_cut_boundary_vertices_above_rim_minus_25mm']}.

## Material change

Hair uses the original base color unchanged. The skin-classification mask `meshy_skin_mask` applies this exact node chain only to skin:

1. `Meshy i02 SPEC multiply`: MULTIPLY factor 1.0 by RGBA {material['nodes']['multiply']['color2_rgba']}.
2. `Meshy i02 warm HSV`: hue {material['nodes']['hue_saturation_value']['hue']}, saturation {material['nodes']['hue_saturation_value']['saturation']}, value {material['nodes']['hue_saturation_value']['value']}, factor 1.0.
3. `Meshy i02 skin mix`: MIX factor from `meshy_skin_mask`, original base color on input 1 and corrected skin on input 2.

The imported normal, ORM/roughness/metallic, and emission maps remain connected and packed.

For glTF portability, export converts the same mask to two standard PBR face-material slots in memory: `AstraChar2 Meshy i02 original hair and non-skin PBR` retains `Image_0`, while `AstraChar2 Meshy i02 corrected skin PBR` uses `Image_0_Meshy_i02_skin_corrected` with the identical multiply/HSV math above. The native `.blend` is not modified by this export-only conversion. Round-trip inspection confirms both materials and both images are present, and both materials retain base-color, metallic/roughness, normal, and emission texture slots.

## Gorget shards (reported, not rebuilt)

Using the audit definition “current disconnected component with ≤12 triangles and maximum bounding-box dimension <30 mm,” the existing gorget/gorget-rim contains **{shards['count']}** detached shard components. Each current object is one connected component; exact object bounds, centroids, boundary/nonmanifold edge counts, and any qualifying shard locations are in `meshy_i02_cut_audit.json`. The banked repair record reports {shards['banked_repair_record']['removed_fractured_neck_faces']:,} fractured neck/collar faces removed in total, including {shards['banked_repair_record']['last_collar_strays_removed']} final strays. Those historical removals are not counted as present i02 shard locations. No armor geometry was rebuilt or repaired.

## Numeric validation

- Native: {validation['bones']} bones; {validation['actions']} actions; rest-matrix error {validation['rest_matrix_error']}; {validation['weights']['unweighted_or_bad_sum_vertices']} unweighted/bad-sum vertices; maximum weight-sum error {validation['weights']['weight_sum_max_error']}.
- Native arms-raised stretch: head/hair {poses['arms_raised']['AstraChar2_Meshy_HeadHair']['edge_stretch_max']}×; neck band {poses['arms_raised']['AstraChar2_Meshy_NeckBlend']['edge_stretch_max']}×.
- Native combat-stress stretch: head/hair {poses['combat_stress']['AstraChar2_Meshy_HeadHair']['edge_stretch_max']}×; neck band {poses['combat_stress']['AstraChar2_Meshy_NeckBlend']['edge_stretch_max']}×.
- GLB round trip: {roundtrip['bones']} bones; {roundtrip['actions']} actions; maximum joint-position error {roundtrip['world_joint_position_max_error_m']} m (gate {roundtrip['world_joint_position_tolerance_m']} m); joint counts {roundtrip['glb_skin_joint_counts']}; animations {roundtrip['glb_animations']}; {roundtrip['weights']['unweighted_or_bad_sum_vertices']} unweighted/bad-sum vertices.
- Round-trip arms-raised stretch: head/hair {rtposes['arms_raised']['AstraChar2_Meshy_HeadHair']['edge_stretch_max']}×; neck band {rtposes['arms_raised']['AstraChar2_Meshy_NeckBlend']['edge_stretch_max']}×.
- Round-trip combat-stress stretch: head/hair {rtposes['combat_stress']['AstraChar2_Meshy_HeadHair']['edge_stretch_max']}×; neck band {rtposes['combat_stress']['AstraChar2_Meshy_NeckBlend']['edge_stretch_max']}×.
- Rising Spin F40 exact overlaps: head {rising['blade_head_exact_triangle_overlaps']}; hair {rising['blade_hair_exact_triangle_overlaps']}.
- Rising Spin F40 sampled surface distance: head {fmt(rising['blade_head_sampled_surface_distance_m'] * 1000, 3)} mm; hair {fmt(rising['blade_hair_sampled_surface_distance_m'] * 1000, 3)} mm. Assembly rest error {rising['assembly_rest_transform_max_error']}.

## Pending GPU render, comparison, and publication

PID 3937364 / `train_marika_v2.py` was active at task start, was never signaled or otherwise touched, and ended naturally before final handoff. No render was started because this task explicitly prohibits rendering. Before running these later commands, independently confirm both approved GPUs remain available. The render script asserts OptiX and never permits CPU fallback.

```bash
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=front"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=side"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=three_quarter"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=collar"
ssh black-sky "cd ~/godwyn-boss-fight && python scripts/astra_meshy_comparison.py -- final=renders/astra/char2/meshy_i02_front.png output=renders/astra/char2/meshy_i02_approved_comparison.png"
```

Review all four i02 views and `meshy_i02_approved_comparison.png` against the approved face reference and the i01 defect renders. Only after explicit owner approval, publish without changing the banked i01 files:

```bash
ssh black-sky "cd ~/godwyn-boss-fight && cp -p models/astra_character_v2_meshy_i02.blend models/astra_character_v2.blend && cp -p models/astra_character_v2_meshy_i02.glb models/astra_character_v2.glb"
```

No git commit or push was made.
"""
    NOTES.write_text(text)
    print("MESHY_I02_NOTES_PASS", NOTES, flush=True)


def main():
    stage = ARGS[0] if ARGS else "all"
    stages = {
        "native": native_validation,
        "export": export_glb,
        "roundtrip": roundtrip_validation,
        "rising": rising_spin_validation,
        "notes": write_notes,
    }
    if stage == "all":
        for name in ("native", "export", "roundtrip", "rising", "notes"):
            stages[name]()
    else:
        stages[stage]()


if __name__ == "__main__":
    main()
