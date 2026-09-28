"""Build the Godwyn v3 WIP from Meshy's auto-rig and the approved v2 parts.

All geometry operations, retarget sampling, image edits, and blend writes happen
inside Blender on black-sky.  Inputs are treated as immutable and verified by
hash before and after the build.
"""

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
DEFAULT_RIGGED = ROOT / "models/meshy_body_godA_hairback_rigged.glb"
SOURCE_PBR = ROOT / "models/meshy_body_godA_hairback.glb"
PARTS_BLEND = ROOT / "models/astra_character_v2_skin_i01.blend"
PROTECTED = [
    ROOT / "models/astra_character_v2.blend",
    ROOT / "models/astra_character_v2.glb",
]
WIP = ROOT / "models/astra_character_v3_wip.blend"

SEAM_Z = 2.605
GORGET_MAX_Z = 2.77
PLATE_METALLIC_MIN = 0.65
GOLD = (0.82, 0.65, 0.15, 1.0)
DEEP_BLUE = (0.00, 0.03, 0.23, 1.0)
TARGET_HEIGHT = 3.16
APPROVED_HEAD_EYE_Z = 2.97655010

MOVES = {
    "idle_guard": {
        "source": ROOT / "models/astra_move_idle_guard_v2_wip.blend",
        "frames": 96,
        "loop": True,
    },
    "walk_stalk": {
        "source": ROOT / "models/astra_move_walk_stalk_v2_wip.blend",
        "frames": 72,
        "loop": True,
    },
    "lunge_thrust": {
        "source": ROOT / "models/astra_move_lunge_thrust_v2_wip.blend",
        "frames": 64,
        "loop": False,
    },
    "rising_spin": {
        "source": ROOT / "models/astra_move_rising_spin_v2_wip.blend",
        "frames": 116,
        "loop": False,
    },
    "xslash": {
        "source": ROOT / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
        "frames": 90,
        "loop": False,
    },
}

BONES = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
ORDER = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
CHILD = {
    "Hips": "Spine02", "Spine02": "Spine01", "Spine01": "Spine", "Spine": "neck",
    "neck": "Head", "Head": "head_end",
    "LeftShoulder": "LeftArm", "LeftArm": "LeftForeArm", "LeftForeArm": "LeftHand",
    "RightShoulder": "RightArm", "RightArm": "RightForeArm", "RightForeArm": "RightHand",
    "LeftUpLeg": "LeftLeg", "LeftLeg": "LeftFoot", "LeftFoot": "LeftToeBase",
    "RightUpLeg": "RightLeg", "RightLeg": "RightFoot", "RightFoot": "RightToeBase",
}
AIM = set(CHILD) - {"Hips"}
LEAF_COPY_BASIS = {"LeftHand", "RightHand"}

HAIR = {
    "min_world_z": 1.55,
    "base_r_min": 0.34,
    "base_g_min": 0.22,
    "r_minus_b_min": 0.20,
    "g_minus_b_min": 0.08,
}


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_RIGGED.relative_to(ROOT)))
    parser.add_argument("--out", default=str(WIP.relative_to(ROOT)))
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_matrix(matrix):
    return [list(row) for row in matrix]


def image_array(image):
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape(image.size[1], image.size[0], image.channels)


def texture_sample(array, uv):
    height, width = array.shape[:2]
    x = int(math.floor((float(uv[0]) % 1.0) * width)) % width
    y = int(math.floor((float(uv[1]) % 1.0) * height)) % height
    return array[y, x, :3]


def linked_image_from_socket(socket):
    if not socket.links:
        return None
    node = socket.links[0].from_node
    if node.type == "TEX_IMAGE":
        return node.image
    for candidate in node.inputs:
        found = linked_image_from_socket(candidate)
        if found is not None:
            return found
    return None


def pbr_images(material):
    bsdf = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    return {
        "base": linked_image_from_socket(bsdf.inputs["Base Color"]),
        "metallic": linked_image_from_socket(bsdf.inputs["Metallic"]),
        "roughness": linked_image_from_socket(bsdf.inputs["Roughness"]),
        "normal": linked_image_from_socket(bsdf.inputs["Normal"]),
        "emission": linked_image_from_socket(bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")),
    }


def import_rigged(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [ob for ob in bpy.data.objects if ob not in before]
    arms = [ob for ob in imported if ob.type == "ARMATURE"]
    bodies = [ob for ob in imported if ob.type == "MESH" and len(ob.vertex_groups)]
    assert len(arms) == 1 and len(bodies) == 1, ([ob.name for ob in arms], [ob.name for ob in bodies])
    arm, body = arms[0], bodies[0]
    arm.name = "Astra_V3_Rig"
    arm.data.name = "Astra V3 Meshy 24-bone skeleton"
    body.name = "char1"
    for ob in imported:
        if ob not in {arm, body}:
            bpy.data.objects.remove(ob, do_unlink=True)
    assert sorted(b.name for b in arm.data.bones) == sorted(BONES)
    return arm, body


def import_source_pbr(target_material):
    before_objects = set(bpy.data.objects)
    before_materials = set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE_PBR))
    imported = [ob for ob in bpy.data.objects if ob not in before_objects and ob.type == "MESH"]
    assert len(imported) == 1
    source_object = imported[0]
    source_material = source_object.data.materials[0]
    source_images = pbr_images(source_material)
    assert source_images["base"] and source_images["metallic"] and source_images["normal"]
    orm = source_images["metallic"]
    normal = source_images["normal"]
    emission = source_images["emission"]
    orm.name = "Astra_V3_Source_ORM"
    normal.name = "Astra_V3_Source_Normal"
    if emission:
        emission.name = "Astra_V3_Source_Emission"
    for image in {value for value in source_images.values() if value is not None}:
        image.pack()
    target_images = pbr_images(target_material)
    base = target_images["base"]
    assert base is not None
    base.name = "Astra_V3_Meshy_AutoRig_BaseColor"
    base.pack()
    bpy.data.objects.remove(source_object, do_unlink=True)
    if source_material.name in bpy.data.materials and source_material not in before_materials:
        bpy.data.materials.remove(source_material)
    return {
        "base": base,
        "orm": orm,
        "normal": normal,
        "emission": emission,
        "source_images": {key: value.name if value else None for key, value in source_images.items()},
    }


def point_segment_distance(point, start, end):
    axis = end - start
    if axis.length_squared <= 1e-12:
        return (point - start).length
    amount = max(0.0, min(1.0, (point - start).dot(axis) / axis.length_squared))
    return (point - (start + axis * amount)).length


def classify_plate(center, metallic, roughness):
    if metallic < PLATE_METALLIC_MIN:
        return False
    x, y, z = center
    torso = z >= 1.62 and abs(x) <= 0.46 and y <= 0.22 and roughness <= 0.52
    limbs = {
        "Left": [Vector((0.315, -0.188, 2.613)), Vector((0.469, -0.161, 2.185)), Vector((0.569, -0.504, 1.959))],
        "Right": [Vector((-0.308, -0.181, 2.615)), Vector((-0.449, -0.138, 2.130)), Vector((-0.468, -0.225, 1.661))],
    }
    arm = roughness <= 0.42 and any(
        min(
            point_segment_distance(center, points[0], points[1]),
            point_segment_distance(center, points[1], points[2]),
            (center - points[0]).length,
            (center - points[2]).length,
        ) <= 0.34
        for points in limbs.values()
    )
    leg_plate = roughness <= 0.52 and 0.34 <= z < 1.62 and 0.10 <= abs(x) <= 0.39 and y <= 0.20
    boot = roughness <= 0.52 and z < 0.38 and 0.11 <= abs(x) <= 0.40 and y <= 0.20
    gauntlet = roughness <= 0.42 and 1.25 <= z < 1.90 and abs(x) >= 0.36
    return bool(torso or arm or leg_plate or boot or gauntlet)


def face_samples(body, base_array, orm_array):
    uv_data = body.data.uv_layers.active.data
    rows = []
    for poly in body.data.polygons:
        uv = np.mean([uv_data[index].uv[:] for index in poly.loop_indices], axis=0)
        base = texture_sample(base_array, uv)
        orm = texture_sample(orm_array, uv)
        coords = [body.matrix_world @ body.data.vertices[index].co for index in poly.vertices]
        center = sum(coords, Vector()) / len(coords)
        plate = classify_plate(center, float(orm[2]), float(orm[1]))
        blue = bool(base[2] > base[0] * 1.12 and base[2] > base[1] * 1.12 and orm[2] < 0.35)
        rows.append({
            "poly": poly.index,
            "base": base,
            "orm": orm,
            "center": center,
            "coords": coords,
            "plate": plate,
            "blue": blue,
        })
    return rows


def segment_body(body, base_image, orm_image):
    base_array = image_array(base_image)
    orm_array = image_array(orm_image)
    rows = face_samples(body, base_array, orm_array)
    keep = []
    removed = defaultdict(int)
    removed_head_vertices = set()
    for row in rows:
        above = max(point.z for point in row["coords"]) > SEAM_Z
        keep_gorget = row["plate"] and row["center"].z <= GORGET_MAX_Z and abs(row["center"].x) <= 0.40
        if above and not keep_gorget:
            removed["non_plate_head_neck_faces"] += 1
            removed_head_vertices.update(body.data.polygons[row["poly"]].vertices)
        else:
            keep.append(row)

    kept_face_indices = {row["poly"] for row in keep}
    head_face_indices = {row["poly"] for row in rows if row["poly"] not in kept_face_indices}

    kept_vertices = {index for row in keep for index in body.data.polygons[row["poly"]].vertices}
    parent = {index: index for index in kept_vertices}

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for row in keep:
        ids = list(body.data.polygons[row["poly"]].vertices)
        for other in ids[1:]:
            union(ids[0], other)
    components = defaultdict(list)
    component_vertices = defaultdict(set)
    for row in keep:
        poly = body.data.polygons[row["poly"]]
        root = find(poly.vertices[0])
        components[root].append(row)
        component_vertices[root].update(poly.vertices)
    rejected_faces = {row["poly"] for row in rows if row["poly"] not in kept_face_indices}
    component_report = []
    for root, members in components.items():
        vertices = component_vertices[root]
        mean_base = np.mean([row["base"] for row in members], axis=0)
        mean_orm = np.mean([row["orm"] for row in members], axis=0)
        mean_center = sum((row["center"] for row in members), Vector()) / len(members)
        r, g, b = mean_base
        hair_colored = bool(
            mean_center.z >= HAIR["min_world_z"]
            and mean_orm[2] < PLATE_METALLIC_MIN
            and r >= HAIR["base_r_min"]
            and g >= HAIR["base_g_min"]
            and r - b >= HAIR["r_minus_b_min"]
            and g - b >= HAIR["g_minus_b_min"]
        )
        small = len(vertices) < 200
        # Meshy's auto-rigged output is intentionally split into many small
        # weighted islands.  Removing components merely because they are small
        # would destroy the body.  Only the color-classified source-hair
        # islands are removed below the neck plane.
        if hair_colored:
            rejected_faces.update(row["poly"] for row in members)
            removed["hair_component_faces"] += len(members)
        component_report.append({
            "vertices": len(vertices),
            "faces": len(members),
            "mean_base": [float(x) for x in mean_base],
            "mean_orm": [float(x) for x in mean_orm],
            "mean_center_world_m": list(mean_center),
            "small": small,
            "hair_colored": hair_colored,
        })

    before = {"vertices": len(body.data.vertices), "edges": len(body.data.edges), "faces": len(body.data.polygons)}
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed_faces = [face for face in bm.faces if face.index in rejected_faces]
    bmesh.ops.delete(bm, geom=doomed_faces, context="FACES")
    orphan_vertices = [vert for vert in bm.verts if not vert.link_faces]
    if orphan_vertices:
        bmesh.ops.delete(bm, geom=orphan_vertices, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    after = {"vertices": len(body.data.vertices), "edges": len(body.data.edges), "faces": len(body.data.polygons)}

    for name in ("astra_v3_plate_mask", "astra_v3_cloth_mask"):
        old = body.data.color_attributes.get(name)
        if old:
            body.data.color_attributes.remove(old)
    plate_attr = body.data.color_attributes.new(name="astra_v3_plate_mask", type="FLOAT_COLOR", domain="CORNER")
    cloth_attr = body.data.color_attributes.new(name="astra_v3_cloth_mask", type="FLOAT_COLOR", domain="CORNER")
    final_rows = face_samples(body, base_array, orm_array)
    for poly, row in zip(body.data.polygons, final_rows):
        plate = 1.0 if row["plate"] else 0.0
        cloth = 1.0 if row["blue"] and not row["plate"] else 0.0
        for loop_index in poly.loop_indices:
            plate_attr.data[loop_index].color = (plate, plate, plate, 1.0)
            cloth_attr.data[loop_index].color = (cloth, cloth, cloth, 1.0)

    group_names = {group.index: group.name for group in body.vertex_groups}
    unweighted = 0
    bad_sums = 0
    maximum_sum_error = 0.0
    for vertex in body.data.vertices:
        weights = [(group_names[item.group], item.weight) for item in vertex.groups if item.weight > 1e-8]
        total = sum(value for _, value in weights)
        unweighted += int(not weights)
        bad_sums += int(weights and abs(total - 1.0) > 1e-4)
        maximum_sum_error = max(maximum_sum_error, abs(total - 1.0) if weights else 1.0)
    # Head measurements must use the pre-delete mesh coordinates.  Capture them
    # from the rows because bmesh compacts vertex indices.
    head_points = np.array([point[:] for row in rows if row["poly"] in head_face_indices for point in row["coords"]], dtype=float)
    head_measure = {
        "point_samples": int(len(head_points)),
        "bounds_min_m": head_points.min(axis=0).tolist(),
        "bounds_max_m": head_points.max(axis=0).tolist(),
        "crown_z_m": float(head_points[:, 2].max()),
        "upper_center_xy_m": np.median(head_points[head_points[:, 2] > 2.82, :2], axis=0).tolist(),
        "seam_center_xy_m": np.median(head_points[np.abs(head_points[:, 2] - SEAM_Z) < 0.035, :2], axis=0).tolist()
        if np.any(np.abs(head_points[:, 2] - SEAM_Z) < 0.035)
        else [0.0, -0.235],
    }
    return {
        "before": before,
        "after": after,
        "removed": dict(removed),
        "rejected_faces": len(rejected_faces),
        "components": sorted(component_report, key=lambda row: row["vertices"], reverse=True),
        "plate_faces": sum(row["plate"] for row in final_rows),
        "cloth_faces": sum(row["blue"] and not row["plate"] for row in final_rows),
        "weights": {
            "unweighted_vertices": unweighted,
            "bad_weight_sum_vertices": bad_sums,
            "maximum_weight_sum_error": maximum_sum_error,
        },
        "removed_head_measurements": head_measure,
        "method": {
            "head": f"remove non-plate faces crossing z={SEAM_Z} m",
            "gorget_exception": f"retain classified plate faces through z={GORGET_MAX_Z} m inside |x|<=0.40 m",
            "small_components": "retained because the auto-rigged mesh is delivered as many weighted islands",
            "hair_color_rule": HAIR,
            "topology": "bmesh face/unused-vertex deletion; no merge-by-distance and no decimation",
        },
    }


def install_body_material(material, images):
    material.name = "Astra V3 Meshy full-resolution PBR LOOK"
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.name = "Astra V3 Output"
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Astra V3 Principled"
    base = nodes.new("ShaderNodeTexImage")
    base.name = "Astra V3 Base Color"
    base.image = images["base"]
    orm = nodes.new("ShaderNodeTexImage")
    orm.name = "Astra V3 ORM"
    orm.image = images["orm"]
    orm.image.colorspace_settings.name = "Non-Color"
    separate = nodes.new("ShaderNodeSeparateColor")
    separate.name = "Astra V3 ORM Separate"
    normal_tex = nodes.new("ShaderNodeTexImage")
    normal_tex.name = "Astra V3 Normal"
    normal_tex.image = images["normal"]
    normal_tex.image.colorspace_settings.name = "Non-Color"
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.name = "Astra V3 Normal Map"
    plate_attr = nodes.new("ShaderNodeAttribute")
    plate_attr.name = "Astra V3 Plate Mask"
    plate_attr.attribute_name = "astra_v3_plate_mask"
    cloth_attr = nodes.new("ShaderNodeAttribute")
    cloth_attr.name = "Astra V3 Cloth Mask"
    cloth_attr.attribute_name = "astra_v3_cloth_mask"
    plate_factor = nodes.new("ShaderNodeMath")
    plate_factor.operation = "MULTIPLY"
    plate_factor.inputs[1].default_value = 0.25
    plate_factor.name = "Astra V3 Plate Tint 25pct"
    plate_mix = nodes.new("ShaderNodeMixRGB")
    plate_mix.blend_type = "MIX"
    plate_mix.inputs[2].default_value = GOLD
    plate_mix.name = "Astra V3 Warm Gold Tint"
    cloth_factor = nodes.new("ShaderNodeMath")
    cloth_factor.operation = "MULTIPLY"
    cloth_factor.inputs[1].default_value = 0.30
    cloth_factor.name = "Astra V3 Cloth Tint 30pct"
    cloth_mix = nodes.new("ShaderNodeMixRGB")
    cloth_mix.blend_type = "MIX"
    cloth_mix.inputs[2].default_value = DEEP_BLUE
    cloth_mix.name = "Astra V3 Deep Blue Tint"
    inv_plate = nodes.new("ShaderNodeMath")
    inv_plate.operation = "SUBTRACT"
    inv_plate.inputs[0].default_value = 1.0
    inv_plate.name = "Astra V3 One Minus Plate"
    rough_base = nodes.new("ShaderNodeMath")
    rough_base.operation = "MULTIPLY"
    rough_base.name = "Astra V3 Nonplate Roughness"
    rough_plate = nodes.new("ShaderNodeMath")
    rough_plate.operation = "MULTIPLY"
    rough_plate.inputs[1].default_value = 0.35
    rough_plate.name = "Astra V3 Plate Roughness 0.35"
    rough_add = nodes.new("ShaderNodeMath")
    rough_add.operation = "ADD"
    rough_add.name = "Astra V3 Final Roughness"
    links.new(output.inputs["Surface"], output.inputs["Surface"]) if False else None
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    links.new(base.outputs["Color"], plate_mix.inputs[1])
    links.new(plate_attr.outputs["Fac"], plate_factor.inputs[0])
    links.new(plate_factor.outputs[0], plate_mix.inputs[0])
    links.new(plate_mix.outputs[0], cloth_mix.inputs[1])
    links.new(cloth_attr.outputs["Fac"], cloth_factor.inputs[0])
    links.new(cloth_factor.outputs[0], cloth_mix.inputs[0])
    links.new(cloth_mix.outputs[0], bsdf.inputs["Base Color"])
    links.new(orm.outputs["Color"], separate.inputs["Color"])
    links.new(separate.outputs["Blue"], bsdf.inputs["Metallic"])
    links.new(plate_attr.outputs["Fac"], inv_plate.inputs[1])
    links.new(separate.outputs["Green"], rough_base.inputs[0])
    links.new(inv_plate.outputs[0], rough_base.inputs[1])
    links.new(plate_attr.outputs["Fac"], rough_plate.inputs[0])
    links.new(rough_base.outputs[0], rough_add.inputs[0])
    links.new(rough_plate.outputs[0], rough_add.inputs[1])
    links.new(rough_add.outputs[0], bsdf.inputs["Roughness"])
    links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    if images["emission"] is not None:
        emission = nodes.new("ShaderNodeTexImage")
        emission.name = "Astra V3 Emission"
        emission.image = images["emission"]
        links.new(emission.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    return {
        "material": material.name,
        "plate_roughness": 0.35,
        "plate_tint": {"color": list(GOLD), "mix": 0.25},
        "cloth_tint": {"color": list(DEEP_BLUE), "mix": 0.30},
        "base_image": images["base"].name,
        "orm_image": images["orm"].name,
        "normal_image": images["normal"].name,
        "emission_image": images["emission"].name if images["emission"] else None,
    }


def append_parts():
    names = ["Armature", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Godwyn_Sword"]
    with bpy.data.libraries.load(str(PARTS_BLEND), link=False) as (available, requested):
        missing = [name for name in names if name not in available.objects]
        assert not missing, missing
        requested.objects = names
    loaded = {}
    for ob in requested.objects:
        if ob is None:
            continue
        bpy.context.scene.collection.objects.link(ob)
        loaded[ob.name] = ob
    bpy.context.view_layer.update()
    return loaded["Armature"], loaded["AstraChar2_Meshy_HeadHair"], loaded["AstraChar2_Meshy_NeckBlend"], loaded["Godwyn_Sword"]


def world_bounds(ob):
    points = np.array([ob.matrix_world @ vertex.co for vertex in ob.data.vertices], dtype=float)
    return points.min(axis=0), points.max(axis=0), points


def transform_mesh_world(ob, transform):
    world = ob.matrix_world.copy()
    for vertex in ob.data.vertices:
        vertex.co = transform @ (world @ vertex.co)
    ob.matrix_world = Matrix.Identity(4)
    ob.data.update()


def bind_rigid(ob, rig, bone_name, modifier_name):
    ob.parent = rig
    ob.parent_type = "OBJECT"
    ob.matrix_parent_inverse = rig.matrix_world.inverted()
    ob.matrix_world = Matrix.Identity(4)
    for modifier in list(ob.modifiers):
        ob.modifiers.remove(modifier)
    ob.vertex_groups.clear()
    group = ob.vertex_groups.new(name=bone_name)
    group.add(range(len(ob.data.vertices)), 1.0, "REPLACE")
    modifier = ob.modifiers.new(modifier_name, "ARMATURE")
    modifier.object = rig


def bind_neck(neck, rig):
    neck.parent = rig
    neck.parent_type = "OBJECT"
    neck.matrix_parent_inverse = rig.matrix_world.inverted()
    neck.matrix_world = Matrix.Identity(4)
    for modifier in list(neck.modifiers):
        neck.modifiers.remove(modifier)
    neck.vertex_groups.clear()
    neck_group = neck.vertex_groups.new(name="neck")
    head_group = neck.vertex_groups.new(name="Head")
    z_values = [vertex.co.z for vertex in neck.data.vertices]
    lo, hi = min(z_values), max(z_values)
    for vertex in neck.data.vertices:
        amount = max(0.0, min(1.0, (vertex.co.z - lo) / max(hi - lo, 1e-8)))
        head_weight = max(0.0, min(1.0, (amount - 0.45) / 0.55))
        neck_group.add([vertex.index], 1.0 - head_weight, "REPLACE")
        if head_weight > 0:
            head_group.add([vertex.index], head_weight, "REPLACE")
    modifier = neck.modifiers.new("Astra V3 Neck Head blend", "ARMATURE")
    modifier.object = rig


def fit_head_and_neck(head, neck, target_measure):
    source_min, source_max, source_points = world_bounds(head)
    seam_band = source_points[np.abs(source_points[:, 2] - SEAM_Z) < 0.035]
    source_seam_xy = np.median(seam_band[:, :2], axis=0) if len(seam_band) else np.array((0.0, -0.235))
    target_seam_xy = np.array(target_measure["seam_center_xy_m"], dtype=float)
    target_crown = target_measure["crown_z_m"]
    uniform_scale = float(np.clip((target_crown - SEAM_Z) / max(source_max[2] - SEAM_Z, 1e-8), 0.98, 1.04))
    source_pivot = Vector((float(source_seam_xy[0]), float(source_seam_xy[1]), SEAM_Z))
    target_pivot = Vector((float(target_seam_xy[0]), float(target_seam_xy[1]), SEAM_Z))
    transform = Matrix.Translation(target_pivot) @ Matrix.Scale(uniform_scale, 4) @ Matrix.Translation(-source_pivot)
    transform_mesh_world(head, transform)
    transform_mesh_world(neck, transform)
    head_min, head_max, _ = world_bounds(head)
    neck_min, neck_max, _ = world_bounds(neck)
    source_eye = Vector((source_pivot.x, source_pivot.y, APPROVED_HEAD_EYE_Z))
    fitted_eye = transform @ source_eye
    report = {
        "method": "uniform fit about measured neck-seam center; scale clamped to 0.98..1.04",
        "source_bounds_m": [source_min.tolist(), source_max.tolist()],
        "target_removed_head": target_measure,
        "source_seam_center_xy_m": source_seam_xy.tolist(),
        "target_seam_center_xy_m": target_seam_xy.tolist(),
        "uniform_scale": uniform_scale,
        "transform": json_matrix(transform),
        "approved_source_eye_line_z_m": APPROVED_HEAD_EYE_Z,
        "fitted_eye_line_z_m": fitted_eye.z,
        "fitted_head_bounds_m": [head_min.tolist(), head_max.tolist()],
        "fitted_neck_bounds_m": [neck_min.tolist(), neck_max.tolist()],
        "crown_error_m": float(head_max[2] - target_crown),
        "seam_anchor_error_m": float(abs(neck_min[2] - SEAM_Z)),
    }
    return report


def dilate(mask):
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def save_crop(array, path, name):
    height, width = array.shape[:2]
    image = bpy.data.images.new(name, width=width, height=height, alpha=True, float_buffer=False)
    image.pixels.foreach_set(array.astype(np.float32).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def fix_neckline_texture(head, fitted_eye_z):
    material = head.data.materials[0]
    base_nodes = [node for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
    image = next((node.image for node in base_nodes if node.image.colorspace_settings.name == "sRGB"), None)
    assert image is not None
    before = image_array(image).copy()
    height, width = before.shape[:2]
    uv_layer = head.data.uv_layers.active
    skin = head.data.color_attributes.get("meshy_skin_mask")
    assert uv_layer is not None and skin is not None
    face_rows = []
    for poly in head.data.polygons:
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        if skin_value < 0.5:
            continue
        center = sum((head.matrix_world @ head.data.vertices[index].co for index in poly.vertices), Vector()) / len(poly.vertices)
        if not (SEAM_Z <= center.z <= fitted_eye_z - 0.095 and abs(center.x) <= 0.18):
            continue
        for loop_index in poly.loop_indices:
            uv = uv_layer.data[loop_index].uv
            x = min(width - 1, max(0, int(float(uv.x % 1.0) * (width - 1))))
            y = min(height - 1, max(0, int(float(uv.y % 1.0) * (height - 1))))
            color = before[y, x, :3]
            luma = float(color @ np.array((0.2126, 0.7152, 0.0722)))
            saturation = float(color.max() - color.min())
            face_rows.append((x, y, luma, saturation, color))
    assert face_rows
    lumas = np.array([row[2] for row in face_rows])
    sats = np.array([row[3] for row in face_rows])
    pale_threshold = max(0.62, float(np.quantile(lumas, 0.82)))
    saturation_threshold = min(0.24, float(np.quantile(sats, 0.45)))
    candidates = [row for row in face_rows if row[2] >= pale_threshold and row[3] <= saturation_threshold]
    if not candidates:
        candidates = sorted(face_rows, key=lambda row: (-row[2], row[3]))[: max(8, len(face_rows) // 20)]
    adjacent = [row[4] for row in face_rows if row[2] < pale_threshold and row[3] > saturation_threshold * 0.65]
    if not adjacent:
        adjacent = [row[4] for row in face_rows]
    median_skin = np.median(np.array(adjacent), axis=0)
    core = np.zeros((height, width), dtype=bool)
    radius = 5
    for x, y, _l, _s, _c in candidates:
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        core[y0:y1, x0:x1] |= (xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2
    alpha = core.astype(np.float32)
    ring = core.copy()
    feather_steps = 10
    for step in range(1, feather_steps + 1):
        expanded = dilate(ring)
        new_ring = expanded & ~ring
        alpha[new_ring] = max(alpha[new_ring].max(initial=0.0), 1.0 - step / (feather_steps + 1))
        ring = expanded
    after = before.copy()
    after[:, :, :3] = before[:, :, :3] * (1.0 - alpha[:, :, None]) + median_skin[None, None, :] * alpha[:, :, None]
    ys, xs = np.where(alpha > 0)
    assert len(xs) > 0
    margin = 64
    x0, x1 = max(0, int(xs.min()) - margin), min(width, int(xs.max()) + margin + 1)
    y0, y1 = max(0, int(ys.min()) - margin), min(height, int(ys.max()) + margin + 1)
    OUT.mkdir(parents=True, exist_ok=True)
    save_crop(before[y0:y1, x0:x1], OUT / "meshy_v3_neckline_before.png", "Astra V3 neckline before crop")
    save_crop(after[y0:y1, x0:x1], OUT / "meshy_v3_neckline_after.png", "Astra V3 neckline after crop")
    edited = image.copy()
    edited.name = "Astra_V3_Head_BaseColor_NecklineFixed"
    edited.pixels.foreach_set(after.astype(np.float32).ravel())
    edited.update()
    for node in base_nodes:
        if node.image == image:
            node.image = edited
    edited.pack()
    report = {
        "source_image": image.name,
        "new_packed_image": edited.name,
        "size": list(edited.size),
        "chin_line_definition": "skin-mask faces below fitted eye minus 95 mm and above gorget seam",
        "sampled_skin_loops": len(face_rows),
        "pale_sample_seeds": len(candidates),
        "edited_texels_core": int(core.sum()),
        "edited_texels_with_feather": int(np.sum(alpha > 0)),
        "pale_luma_threshold": pale_threshold,
        "low_saturation_threshold": saturation_threshold,
        "replacement_median_linear_rgb": median_skin.tolist(),
        "feather_steps_px": feather_steps,
        "crop_xyxy": [x0, y0, x1, y1],
        "before_crop": "renders/astra/char2/meshy_v3_neckline_before.png",
        "after_crop": "renders/astra/char2/meshy_v3_neckline_after.png",
    }
    (OUT / "meshy_v3_neckline_fix.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def attach_sword(sword, old_arm, target_arm):
    old_hand = old_arm.matrix_world @ old_arm.data.bones["RightHand"].matrix_local
    new_hand = target_arm.matrix_world @ target_arm.data.bones["RightHand"].matrix_local
    source_object_world = sword.matrix_world.copy()
    transform = new_hand @ old_hand.inverted()
    transform_mesh_world(sword, transform)
    bind_rigid(sword, target_arm, "RightHand", "Astra V3 rigid sword attachment")
    source_attr = sword.data.attributes.get("astra_sword_source")
    assert source_attr is not None
    source = np.asarray([item.vector[:] for item in source_attr.data])
    local = np.asarray([vertex.co[:] for vertex in sword.data.vertices])
    fit = np.linalg.lstsq(np.column_stack((source, np.ones(len(source)))), local, rcond=None)[0]
    hilt = np.array([61.2, -66.3, 167.0, 1.0]) @ fit
    hand_local_hilt = new_hand.inverted() @ Vector(hilt)
    return {
        "method": "old RightHand-local sword transform reapplied to new RightHand rest transform",
        "old_hand_rest_world": json_matrix(old_hand),
        "new_hand_rest_world": json_matrix(new_hand),
        "old_to_new_world_transform": json_matrix(transform),
        "source_sword_object_world": json_matrix(source_object_world),
        "hilt_world_rest_m": hilt.tolist(),
        "hilt_new_hand_local": list(hand_local_hilt),
        "vertices": len(sword.data.vertices),
        "parent": target_arm.name,
        "bone": "RightHand",
    }


def append_source_armature(path, name):
    with bpy.data.libraries.load(str(path), link=False) as (available, requested):
        assert "Armature" in available.objects
        requested.objects = ["Armature"]
    source = requested.objects[0]
    bpy.context.scene.collection.objects.link(source)
    source.name = f"Astra_V3_SourceRig_{name}"
    bpy.context.view_layer.update()
    assert source.animation_data and source.animation_data.action
    return source


def action_channelbag(action):
    layer = action.layers.new("Astra V3 Layer")
    strip = layer.strips.new(type="KEYFRAME")
    slot = action.slots.new(id_type="OBJECT", name="Astra_V3_Rig")
    return slot, strip.channelbag(slot, ensure=True)


def curve_key(channelbag, data_path, index, frame, value):
    curve = channelbag.fcurves.find(data_path, index=index) or channelbag.fcurves.new(data_path, index=index)
    point = curve.keyframe_points.insert(frame, value, options={"FAST"})
    point.interpolation = "LINEAR"
    return curve


def normalized_object_rotation(obj):
    return obj.matrix_world.to_quaternion().to_matrix()


def source_joint_positions(source):
    return {name: source.matrix_world @ source.pose.bones[name].head for name in BONES}


def target_rest_world(target, name):
    return target.matrix_world @ target.data.bones[name].head_local


def retarget_move(name, spec, target, target_height):
    scene = bpy.context.scene
    source = append_source_armature(spec["source"], name)
    source_action = source.animation_data.action
    source_rest = {bone: source.matrix_world @ source.data.bones[bone].head_local for bone in BONES}
    source_crown = max((source.matrix_world @ source.data.bones["head_end"].head_local).z,
                       (source.matrix_world @ source.data.bones["Head"].head_local).z)
    source_floor = min((source.matrix_world @ source.data.bones[bone].head_local).z
                       for bone in ("LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase"))
    skeletal_height = max(1e-6, source_crown - source_floor)
    target_crown = max(target_rest_world(target, "head_end").z, target_rest_world(target, "Head").z)
    target_floor = min(target_rest_world(target, bone).z
                       for bone in ("LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase"))
    height_ratio = (target_crown - target_floor) / skeletal_height
    if not 0.9 <= height_ratio <= 1.1:
        height_ratio = target_height / 3.1490283012390137

    action = bpy.data.actions.new(f"Godwyn_V3_{name}")
    action.use_fake_user = True
    action["astra_v3_move"] = name
    action["astra_v3_loop"] = spec["loop"]
    action["astra_v3_fps"] = 30
    action["astra_v3_frame_count"] = spec["frames"]
    if hasattr(action, "use_cyclic"):
        action.use_cyclic = spec["loop"]
    slot, channelbag = action_channelbag(action)

    target_rest_rot = {bone: target.data.bones[bone].matrix_local.to_3x3() for bone in BONES}
    target_parent = {bone: target.data.bones[bone].parent.name if target.data.bones[bone].parent else None for bone in BONES}
    target_heads = {bone: target.data.bones[bone].head_local.copy() for bone in BONES}
    target_aim_axis_local = {
        bone: (target_rest_rot[bone].inverted() @ (target_heads[child] - target_heads[bone])).normalized()
        for bone, child in CHILD.items() if bone != "Hips"
    }
    target_up = (target_heads["Spine02"] - target_heads["Hips"]).normalized()
    target_side = (target_heads["LeftUpLeg"] - target_heads["RightUpLeg"]).normalized()
    target_forward = target_side.cross(target_up).normalized()
    target_side = target_up.cross(target_forward).normalized()
    target_anatomical_frame = Matrix((target_side, target_up, target_forward)).transposed()
    target_rot_inv = normalized_object_rotation(target).inverted()
    target_scale = target.matrix_world.to_scale().x
    frame_samples = []
    for frame in range(1, spec["frames"] + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        positions = source_joint_positions(source)
        for pose_bone in target.pose.bones:
            pose_bone.matrix_basis.identity()
            pose_bone.rotation_mode = "QUATERNION"
        posed_world = {}
        for bone in ORDER:
            parent = target_parent[bone]
            rest_relative = (
                target_rest_rot[parent].inverted() @ target_rest_rot[bone]
                if parent else target_rest_rot[bone]
            )
            parent_world = posed_world.get(parent, Matrix.Identity(3))
            pre = parent_world @ rest_relative
            if bone == "Hips":
                up = (positions["Spine02"] - positions["Hips"]).normalized()
                side = (positions["LeftUpLeg"] - positions["RightUpLeg"]).normalized()
                forward = side.cross(up).normalized()
                side = up.cross(forward).normalized()
                desired_world = Matrix((side, up, forward)).transposed()
                desired_arm = target_rot_inv @ desired_world
                anatomical_delta = desired_arm @ target_anatomical_frame.inverted()
                world = anatomical_delta @ target_rest_rot[bone]
                basis = rest_relative.inverted() @ world
                posed_world[bone] = world
            elif bone in AIM:
                direction_world = positions[CHILD[bone]] - positions[bone]
                if direction_world.length < 1e-8:
                    basis = Matrix.Identity(3)
                    posed_world[bone] = pre
                else:
                    direction_arm = (target_rot_inv @ direction_world).normalized()
                    pre_axis = (pre @ target_aim_axis_local[bone]).normalized()
                    align = pre_axis.rotation_difference(direction_arm).to_matrix()
                    world = align @ pre
                    basis = rest_relative.inverted() @ parent_world.inverted() @ world
                    posed_world[bone] = world
            elif bone in LEAF_COPY_BASIS:
                basis = source.pose.bones[bone].matrix_basis.to_3x3()
                posed_world[bone] = pre @ basis
            else:
                basis = Matrix.Identity(3)
                posed_world[bone] = pre
            quaternion = basis.to_quaternion().normalized()
            target.pose.bones[bone].rotation_quaternion = quaternion
        root_delta_world = (positions["Hips"] - source_rest["Hips"]) * height_ratio
        root_delta_arm = (target_rot_inv @ root_delta_world) / target_scale
        root_local = target_rest_rot["Hips"].inverted() @ root_delta_arm
        target.pose.bones["Hips"].location = root_local
        bpy.context.view_layer.update()

        desired_root_world = target_rest_world(target, "Hips") + root_delta_world
        target_inverse = target.matrix_world.inverted()
        # The two rigs do not share joint positions despite sharing names.  A
        # direction-only solve leaves 0.3-0.4 m wrist/toe errors.  After aiming
        # rotations, solve each non-root pose-bone head to the mapped source
        # joint position.  These are ordinary pose locations, not rest edits.
        for bone in ORDER[1:]:
            desired_world = desired_root_world + (positions[bone] - positions["Hips"]) * height_ratio
            desired_armature = target_inverse @ desired_world
            pose_bone = target.pose.bones[bone]
            matrix = pose_bone.matrix.copy()
            matrix.translation = desired_armature
            pose_bone.matrix = matrix
            bpy.context.view_layer.update()

        for bone in ORDER:
            pose_bone = target.pose.bones[bone]
            rotation_path = f'pose.bones["{bone}"].rotation_quaternion'
            location_path = f'pose.bones["{bone}"].location'
            for index, value in enumerate(pose_bone.rotation_quaternion):
                curve_key(channelbag, rotation_path, index, frame, value)
            for index, value in enumerate(pose_bone.location):
                curve_key(channelbag, location_path, index, frame, value)
        frame_samples.append({
            "frame": frame,
            "source_positions_world_m": {bone: list(positions[bone]) for bone in BONES},
        })
        if frame == 1 or frame == spec["frames"] or frame % 30 == 0:
            print("V3_RETARGET", name, frame, "/", spec["frames"], flush=True)
    for curve in channelbag.fcurves:
        curve.update()
    source_name = source_action.name
    bpy.data.objects.remove(source, do_unlink=True)
    if source_action.users == 0:
        bpy.data.actions.remove(source_action)
    return action, slot, {
        "source": str(spec["source"].relative_to(ROOT)),
        "source_sha256": sha256(spec["source"]),
        "source_action": source_name,
        "target_action": action.name,
        "frames": spec["frames"],
        "fps": 30,
        "loop": spec["loop"],
        "height_ratio": height_ratio,
        "source_rest_positions_world_m": {bone: list(source_rest[bone]) for bone in BONES},
        "samples": frame_samples,
    }


def assign_action(target, action, slot, frame=1):
    animation = target.animation_data_create()
    animation.action = action
    animation.action_slot = slot
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def evaluated_coordinates(ob):
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coords


def fcurves_for(action):
    return [curve for layer in action.layers for strip in layer.strips for bag in strip.channelbags for curve in bag.fcurves]


def add_curve_value_at_frame(curve, frame, delta):
    for point in curve.keyframe_points:
        if abs(point.co.x - frame) < 1e-5:
            point.co.y += delta
            return
    raise RuntimeError(f"No exact key at frame {frame} on {curve.data_path}[{curve.array_index}]")


def sole_vertices(body):
    names = {group.index: group.name for group in body.vertex_groups}
    result = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        ids = []
        for vertex in body.data.vertices:
            point = body.matrix_world @ vertex.co
            weight = sum(item.weight for item in vertex.groups if names[item.group] in allowed)
            if point.z < 0.24 and weight > 0.50:
                ids.append(vertex.index)
        assert ids, side
        result[side] = np.asarray(ids, dtype=np.int32)
    return result


def correct_soles(target, body, actions):
    ids = sole_vertices(body)
    rest_rot = target.data.bones["Hips"].matrix_local.to_3x3()
    object_rot_inv = normalized_object_rotation(target).inverted()
    object_scale = target.matrix_world.to_scale().x
    report = {}
    for name, item in actions.items():
        action, slot = item["action"], item["slot"]
        assign_action(target, action, slot)
        curves = {(curve.data_path, curve.array_index): curve for curve in fcurves_for(action)}
        path = 'pose.bones["Hips"].location'
        before = []
        corrections = []
        for frame in range(1, MOVES[name]["frames"] + 1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            coords = evaluated_coordinates(body)
            minimum = min(float(coords[indices, 2].min()) for indices in ids.values())
            before.append(minimum)
            lift = max(0.0, -minimum + 0.0005)
            corrections.append(lift)
            if lift > 0:
                arm_delta = (object_rot_inv @ Vector((0.0, 0.0, lift))) / object_scale
                local_delta = rest_rot.inverted() @ arm_delta
                for index, value in enumerate(local_delta):
                    add_curve_value_at_frame(curves[(path, index)], frame, value)
        for curve in curves.values():
            curve.update()
        after = []
        for frame in range(1, MOVES[name]["frames"] + 1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            coords = evaluated_coordinates(body)
            after.append(min(float(coords[indices, 2].min()) for indices in ids.values()))
        report[name] = {
            "samples": MOVES[name]["frames"],
            "minimum_before_m": min(before),
            "minimum_after_m": min(after),
            "maximum_root_lift_m": max(corrections),
            "corrected_frames": sum(value > 0 for value in corrections),
            "gate_pass": min(after) >= -1e-6,
        }
        assert report[name]["maximum_root_lift_m"] < 0.50, report[name]
        assert report[name]["gate_pass"], report[name]
        print("V3_SOLE", name, json.dumps(report[name]), flush=True)
    return {"sole_vertex_counts": {key: len(value) for key, value in ids.items()}, "moves": report}


def main():
    args = cli()
    OUT.mkdir(parents=True, exist_ok=True)
    rigged = root_path(args.input)
    wip = root_path(args.out)
    protected_before = {str(path.relative_to(ROOT)): sha256(path) for path in PROTECTED}
    input_hashes = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in [rigged, SOURCE_PBR, PARTS_BLEND] + [item["source"] for item in MOVES.values()]
    }
    target, body = import_rigged(rigged)
    original_bounds = world_bounds(body)
    material = body.data.materials[0]
    images = import_source_pbr(material)
    segmentation = segment_body(body, images["base"], images["orm"])
    assert segmentation["weights"]["unweighted_vertices"] == 0
    assert segmentation["weights"]["bad_weight_sum_vertices"] == 0
    material_report = install_body_material(material, images)

    old_arm, head, neck, sword = append_parts()
    head.name = "AstraChar2_Meshy_HeadHair"
    neck.name = "AstraChar2_Meshy_NeckBlend"
    sword.name = "Godwyn_Sword"
    head_fit = fit_head_and_neck(head, neck, segmentation["removed_head_measurements"])
    neckline = fix_neckline_texture(head, head_fit["fitted_eye_line_z_m"])
    bind_rigid(head, target, "Head", "Astra V3 rigid Head binding")
    bind_neck(neck, target)
    sword_report = attach_sword(sword, old_arm, target)
    bpy.data.objects.remove(old_arm, do_unlink=True)

    target.rotation_mode = "QUATERNION"
    target.animation_data_clear()
    for pose_bone in target.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.matrix_basis.identity()
    target_height = float(original_bounds[1][2] - original_bounds[0][2])
    actions = {}
    samples = {
        "schema": "astra-v3-retarget-source-samples",
        "comparison_definition": "target root aligned plus source root-relative joint offsets scaled by per-move skeletal height ratio",
        "moves": {},
    }
    for name, spec in MOVES.items():
        action, slot, sample = retarget_move(name, spec, target, target_height)
        actions[name] = {"action": action, "slot": slot}
        samples["moves"][name] = sample
    keep_actions = {item["action"] for item in actions.values()}
    for action in list(bpy.data.actions):
        if action not in keep_actions:
            bpy.data.actions.remove(action)
    sole = correct_soles(target, body, actions)
    idle = actions["idle_guard"]
    assign_action(target, idle["action"], idle["slot"], 1)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = MOVES["idle_guard"]["frames"]
    scene.render.fps = 30
    scene["astra_v3"] = json.dumps({
        "input": str(rigged.relative_to(ROOT)),
        "actions": {name: item["action"].name for name, item in actions.items()},
        "head_fit": head_fit,
        "segmentation": {key: value for key, value in segmentation.items() if key != "components"},
    })
    mapping = {
        "schema": "astra-v3-bone-mapping",
        "source_skeleton_bones": 121,
        "target_skeleton_bones": 24,
        "mapping": {bone: bone for bone in BONES},
        "identity_mapping": True,
        "order": ORDER,
        "aim_child": CHILD,
        "aimed_bones": sorted(AIM),
        "root_frame": {"up": "Hips->Spine02", "side": "RightUpLeg->LeftUpLeg", "handedness": "forward=side cross up"},
        "leaf_basis_copy": sorted(LEAF_COPY_BASIS),
        "feet": "LeftFoot/RightFoot aim from ankle joint to the source ToeBase direction; ToeBase remains rest-relative. This uses the old rig's actual foot direction rather than SMPL tip points.",
        "method": "per-frame old-rig posed joint heads; parent-forward direction FK using each target bone's actual rest joint-to-child axis; then non-root pose locations solve each mapped joint head to the source-aligned position; root anatomical-frame delta and scaled translation (glTF synthetic tails are not used as joint axes)",
        "moves": {name: {"frames": spec["frames"], "fps": 30, "loop": spec["loop"]} for name, spec in MOVES.items()},
    }
    (OUT / "meshy_v3_bone_mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    (OUT / "meshy_v3_retarget_samples.json").write_text(json.dumps(samples, indent=2) + "\n")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(wip))
    protected_after = {str(path.relative_to(ROOT)): sha256(path) for path in PROTECTED}
    assert protected_before == protected_after
    report = {
        "schema": "astra-v3-build",
        "blender": bpy.app.version_string,
        "input_hashes": input_hashes,
        "protected_v2_before": protected_before,
        "protected_v2_after": protected_after,
        "protected_v2_unchanged": True,
        "rig": {
            "object": target.name,
            "bones": len(target.data.bones),
            "bone_names": [bone.name for bone in target.data.bones],
            "finger_bones": [bone.name for bone in target.data.bones if "finger" in bone.name.lower() or "thumb" in bone.name.lower()],
        },
        "body_original_bounds_m": [original_bounds[0].tolist(), original_bounds[1].tolist()],
        "segmentation": segmentation,
        "head_fit": head_fit,
        "neckline_texture_fix": neckline,
        "sword": sword_report,
        "material": material_report,
        "retarget": {
            name: {
                key: value for key, value in samples["moves"][name].items()
                if key not in {"samples", "source_rest_positions_world_m"}
            }
            for name in MOVES
        },
        "sole_correction": sole,
        "actions": [action.name for action in keep_actions],
        "wip": str(wip.relative_to(ROOT)),
        "wip_sha256": sha256(wip),
        "wip_bytes": wip.stat().st_size,
    }
    (OUT / "meshy_v3_build.json").write_text(json.dumps(report, indent=2) + "\n")
    print("V3_BUILD_PASS", json.dumps({
        "wip": report["wip"],
        "bytes": report["wip_bytes"],
        "bones": report["rig"]["bones"],
        "actions": report["actions"],
        "body_faces": segmentation["after"]["faces"],
        "head_scale": head_fit["uniform_scale"],
        "protected": report["protected_v2_unchanged"],
    }), flush=True)


if __name__ == "__main__":
    main()
