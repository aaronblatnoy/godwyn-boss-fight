"""Fix the actual head base-color collar band and physically hide the seam."""

import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
BLEND = ROOT / "models/astra_character_v3_wip.blend"


def image_array(image):
    values = np.empty(len(image.pixels), dtype=np.float32)
    image.pixels.foreach_get(values)
    return values.reshape(image.size[1], image.size[0], image.channels)


def save_crop(array, path, name):
    height, width = array.shape[:2]
    image = bpy.data.images.new(name, width=width, height=height, alpha=True, float_buffer=False)
    image.pixels.foreach_set(array.astype(np.float32).ravel())
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def dilate(mask):
    output = mask.copy()
    output[1:] |= mask[:-1]
    output[:-1] |= mask[1:]
    output[:, 1:] |= mask[:, :-1]
    output[:, :-1] |= mask[:, 1:]
    return output


def actual_base_node(material):
    nodes = material.node_tree.nodes
    mix = nodes.get("Meshy i02 skin mix")
    if mix and mix.inputs[1].links:
        node = mix.inputs[1].links[0].from_node
        if node.type == "TEX_IMAGE" and node.image:
            return node
    multiply = nodes.get("Meshy i02 SPEC multiply")
    if multiply and multiply.inputs[1].links:
        node = multiply.inputs[1].links[0].from_node
        if node.type == "TEX_IMAGE" and node.image:
            return node
    raise RuntimeError("Could not resolve approved head base-color image node")


def restore_wrong_emission_edit(material):
    wrong = bpy.data.images.get("Astra_V3_Head_BaseColor_NecklineFixed")
    original = bpy.data.images.get("Image_3")
    rewired = 0
    if wrong and original:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image == wrong:
                node.image = original
                rewired += 1
        if wrong.users == 0:
            bpy.data.images.remove(wrong)
    return rewired


def densest_crop(seeds, width, height, crop=512):
    bins = 32
    histogram = np.zeros((bins, bins), dtype=np.int32)
    for x, y in seeds:
        histogram[min(bins - 1, y * bins // height), min(bins - 1, x * bins // width)] += 1
    by, bx = np.unravel_index(int(np.argmax(histogram)), histogram.shape)
    cx = int((bx + 0.5) * width / bins)
    cy = int((by + 0.5) * height / bins)
    half = crop // 2
    x0 = max(0, min(width - crop, cx - half))
    y0 = max(0, min(height - crop, cy - half))
    return x0, y0, x0 + crop, y0 + crop


def fix_base_color(head):
    material = head.data.materials[0]
    rewired_emission_nodes = restore_wrong_emission_edit(material)
    node = actual_base_node(material)
    source = node.image
    before = image_array(source).copy()
    height, width = before.shape[:2]
    uv = head.data.uv_layers.active
    skin = head.data.color_attributes["meshy_skin_mask"]
    samples = []
    for poly in head.data.polygons:
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        if skin_value < 0.5:
            continue
        center = sum((head.data.vertices[index].co for index in poly.vertices), Vector()) / len(poly.vertices)
        if not (2.605 <= center.z <= 2.875 and abs(center.x) <= 0.22):
            continue
        for loop_index in poly.loop_indices:
            texcoord = uv.data[loop_index].uv
            x = min(width - 1, max(0, int(float(texcoord.x % 1.0) * (width - 1))))
            y = min(height - 1, max(0, int(float(texcoord.y % 1.0) * (height - 1))))
            color = before[y, x, :3]
            luma = float(color @ np.array((0.2126, 0.7152, 0.0722)))
            saturation = float(color.max() - color.min())
            samples.append((x, y, luma, saturation, color))
    assert samples
    lumas = np.asarray([item[2] for item in samples])
    saturations = np.asarray([item[3] for item in samples])
    luma_cut = max(0.30, float(np.quantile(lumas, 0.76)))
    saturation_cut = float(np.quantile(saturations, 0.42))
    candidates = [item for item in samples if item[2] >= luma_cut and item[3] <= saturation_cut]
    assert candidates
    adjacent = [item[4] for item in samples if item[2] < luma_cut and item[3] > saturation_cut]
    if not adjacent:
        adjacent = [item[4] for item in samples if item[2] < luma_cut]
    median_skin = np.median(np.asarray(adjacent), axis=0)
    core = np.zeros((height, width), dtype=bool)
    radius = 6
    seeds = []
    for x, y, _luma, _sat, _color in candidates:
        seeds.append((x, y))
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        yy, xx = np.ogrid[y0:y1, x0:x1]
        core[y0:y1, x0:x1] |= (xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2
    alpha = core.astype(np.float32)
    active = core.copy()
    for step in range(1, 13):
        expanded = dilate(active)
        ring = expanded & ~active
        alpha[ring] = 1.0 - step / 13.0
        active = expanded
    after = before.copy()
    after[:, :, :3] = before[:, :, :3] * (1.0 - alpha[:, :, None]) + median_skin[None, None, :] * alpha[:, :, None]
    crop = densest_crop(seeds, width, height)
    x0, y0, x1, y1 = crop
    save_crop(before[y0:y1, x0:x1], OUT / "meshy_v3_neckline_before.png", "Astra V3 actual base before")
    save_crop(after[y0:y1, x0:x1], OUT / "meshy_v3_neckline_after.png", "Astra V3 actual base after")
    corrected = source.copy()
    corrected.name = "Astra_V3_Head_BaseColor_NecklineFixed"
    corrected.pixels.foreach_set(after.astype(np.float32).ravel())
    corrected.update()
    for image_node in material.node_tree.nodes:
        if image_node.type == "TEX_IMAGE" and image_node.image == source:
            image_node.image = corrected
    corrected.pack()
    return {
        "resolved_base_node": node.name,
        "source_base_image": source.name,
        "corrected_packed_image": corrected.name,
        "restored_emission_nodes": rewired_emission_nodes,
        "samples": len(samples),
        "candidate_seeds": len(candidates),
        "edited_core_texels": int(core.sum()),
        "edited_feathered_texels": int(np.sum(alpha > 0)),
        "luma_cut": luma_cut,
        "saturation_cut": saturation_cut,
        "median_adjacent_skin_linear_rgb": median_skin.tolist(),
        "crop_xyxy": list(crop),
    }


def make_sleeve(rig, neck):
    old = bpy.data.objects.get("Astra_V3_SeamSleeve")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    points = np.asarray([vertex.co[:] for vertex in neck.data.vertices], dtype=float)
    center_x = float(np.median(points[:, 0]))
    center_y = float(np.median(points[:, 1]))
    rows, sides = 12, 64
    z0, z1 = 2.585, 2.815
    vertices = []
    faces = []
    for row in range(rows):
        amount = row / (rows - 1)
        z = z0 + (z1 - z0) * amount
        rx = 0.135 * (1.0 - amount) + 0.095 * amount
        ry = 0.110 * (1.0 - amount) + 0.076 * amount
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append((center_x + rx * math.cos(angle), center_y + ry * math.sin(angle), z))
    for row in range(rows - 1):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    bottom = len(vertices)
    vertices.append((center_x, center_y, z0))
    top = len(vertices)
    vertices.append((center_x, center_y, z1))
    for side in range(sides):
        faces.append((bottom, (side + 1) % sides, side))
        a = (rows - 1) * sides + side
        b = (rows - 1) * sides + (side + 1) % sides
        faces.append((top, a, b))
    mesh = bpy.data.meshes.new("Astra V3 closed under-gorget seam sleeve")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(neck.data.materials[0])
    sleeve = bpy.data.objects.new("Astra_V3_SeamSleeve", mesh)
    bpy.context.scene.collection.objects.link(sleeve)
    sleeve.parent = rig
    sleeve.matrix_parent_inverse = rig.matrix_world.inverted()
    neck_group = sleeve.vertex_groups.new(name="neck")
    head_group = sleeve.vertex_groups.new(name="Head")
    for vertex in mesh.vertices:
        amount = max(0.0, min(1.0, (vertex.co.z - z0) / (z1 - z0)))
        head_weight = max(0.0, min(1.0, (amount - 0.50) / 0.50))
        neck_group.add([vertex.index], 1.0 - head_weight, "REPLACE")
        if head_weight:
            head_group.add([vertex.index], head_weight, "REPLACE")
    modifier = sleeve.modifiers.new("Astra V3 Neck Head seam binding", "ARMATURE")
    modifier.object = rig
    return {
        "object": sleeve.name,
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "closed": True,
        "center_xy_m": [center_x, center_y],
        "z_range_m": [z0, z1],
        "bottom_radii_m": [0.135, 0.110],
        "top_radii_m": [0.095, 0.076],
        "binding": "neck/Head linear blend",
    }


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    neck = bpy.data.objects["AstraChar2_Meshy_NeckBlend"]
    texture = fix_base_color(head)
    sleeve = make_sleeve(rig, neck)
    bpy.context.scene["astra_v3_seam_fix"] = json.dumps({"texture": texture, "sleeve": sleeve})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report = {"schema": "astra-v3-seam-fix", "texture": texture, "sleeve": sleeve}
    (OUT / "meshy_v3_seam_fix.json").write_text(json.dumps(report, indent=2) + "\n")
    print("V3_SEAM_FIX_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
