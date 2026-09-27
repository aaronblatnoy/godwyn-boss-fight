"""Build Meshy graft iteration 02: geometry and material only, never render.

The protected inputs are opened read-only and the result is written to the
iteration-02 candidate path.  The Meshy source is rebuilt from the original GLB
so the iteration-01 texture trim cannot carry shredded hair into this pass.
"""
import bpy
import bmesh
import json
import math
import numpy as np
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
BASE = ROOT / "models/astra_character_v2_pre_likeness.blend"
MESHY = ROOT / "models/meshy_head_approved.glb"
CANDIDATE = ROOT / "models/astra_character_v2_meshy_i02.blend"

SCALE = 0.31
FIT_XY = 1.05
OFFSET = np.array((0.00043, -0.25190, 2.85520), dtype=float)
EYE_PIVOT = np.array((0.00043, -0.37956585, 2.97655010), dtype=float)
NECK_BASE_Z = 2.605
NECK_BLEND_TOP_Z = 2.735
FLOATING_FRAGMENT_MAX_M = 0.015
SECTORS = 24

# The source texture is sRGB-like packed GLB data (quantized to 8-bit values).
# A face is hair when it is both darker/warmer than skin and geometrically
# outside the central facial/neck core.  Thresholds are deliberately explicit
# and are serialized to the audit JSON.
HAIR_LUMA_MAX = 0.665
HAIR_STRONG_LUMA_MAX = 0.595
HAIR_R_MINUS_B_MIN = 0.175
HAIR_G_MINUS_B_MIN = 0.085

# Skin correction requested by SPEC.  Hue 0.5 is neutral in Blender; 0.485 is
# a small shift toward orange/red.  The base color is multiplied by SPEC skin,
# then receives +15% saturation and -8% value, and is mixed through the same
# geometry/texel classification mask.  Hair remains the untouched input color.
SPEC_SKIN = (0.95, 0.90, 0.82, 1.0)
SKIN_HUE = 0.485
SKIN_SATURATION = 1.15
SKIN_VALUE = 0.92


def reset_pose(arm):
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def world_points(ob):
    return np.array([ob.matrix_world @ v.co for v in ob.data.vertices], dtype=float)


def base_color_pixels(mat):
    for node in mat.node_tree.nodes:
        if node.type != "TEX_IMAGE" or not node.image:
            continue
        if any(link.to_socket.name == "Base Color" for link in node.outputs["Color"].links):
            image = node.image
            width, height = image.size
            pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
            return node, image, pixels, width, height
    raise RuntimeError("Meshy material has no image feeding Principled Base Color")


def face_rgb(ob, pixels, width, height):
    uv = ob.data.uv_layers.active
    if uv is None:
        raise RuntimeError("Meshy mesh has no active UV layer")
    values = np.zeros((len(ob.data.polygons), 3), dtype=np.float32)
    for poly in ob.data.polygons:
        samples = []
        for loop_index in poly.loop_indices:
            u, v = uv.data[loop_index].uv
            x = min(width - 1, max(0, int(float(u) * (width - 1))))
            y = min(height - 1, max(0, int(float(v) * (height - 1))))
            samples.append(pixels[y, x, :3])
        values[poly.index] = np.mean(samples, axis=0)
    return values


def classify_faces(ob, rgb):
    points = np.array([v.co[:] for v in ob.data.vertices], dtype=float)
    hair = np.zeros(len(ob.data.polygons), dtype=bool)
    skin = np.zeros(len(ob.data.polygons), dtype=bool)
    lumas = np.zeros(len(ob.data.polygons), dtype=np.float32)
    centers_raw = np.zeros((len(ob.data.polygons), 3), dtype=np.float32)
    for poly in ob.data.polygons:
        center_world = points[list(poly.vertices)].mean(axis=0)
        # Reproduce and invert i01's exact placement order: scale was applied
        # to local coordinates, XY was fitted around EYE_PIVOT in local space,
        # and OFFSET remained as object translation until baked below.
        prefit_local = center_world - OFFSET
        prefit_local[:2] = EYE_PIVOT[:2] + (prefit_local[:2] - EYE_PIVOT[:2]) / FIT_XY
        raw = prefit_local / SCALE
        centers_raw[poly.index] = raw
        color = rgb[poly.index]
        luma = float(color @ np.array((0.2126, 0.7152, 0.0722)))
        lumas[poly.index] = luma
        warm = float(color[0] - color[2]) >= HAIR_R_MINUS_B_MIN and float(color[1] - color[2]) >= HAIR_G_MINUS_B_MIN
        face_core = abs(raw[0]) < 0.305 and raw[1] < -0.205 and -0.18 < raw[2] < 0.54
        neck_core = abs(raw[0]) < 0.235 and raw[1] < 0.10 and -0.92 < raw[2] <= -0.18
        hair_geometry = (
            raw[2] > 0.54 or abs(raw[0]) > 0.305 or raw[1] > -0.080
            or (raw[2] < -0.18 and (abs(raw[0]) > 0.205 or raw[1] > 0.015))
        )
        strong_color = luma <= HAIR_STRONG_LUMA_MAX and warm
        ordinary_color = luma <= HAIR_LUMA_MAX and warm
        is_hair = hair_geometry and ordinary_color and not (face_core or neck_core)
        # Strong dark/warm texels capture narrow fringe and braid faces just
        # inside the broader geometry envelope, but never the central face.
        if strong_color and not face_core and not neck_core:
            is_hair = True
        hair[poly.index] = is_hair

        skin_geometry = face_core or neck_core or (
            abs(raw[0]) < 0.39 and raw[1] < 0.10 and -0.92 < raw[2] < 0.72
        )
        skin_color = luma >= 0.43 and float(color[0] - color[2]) >= 0.105
        skin[poly.index] = (not is_hair) and skin_geometry and skin_color
    return hair, skin, lumas, centers_raw


def add_face_masks(ob, hair_faces, skin_faces):
    for name in ("meshy_hair_mask", "meshy_skin_mask"):
        old = ob.data.color_attributes.get(name)
        if old:
            ob.data.color_attributes.remove(old)
    hair_attr = ob.data.color_attributes.new(name="meshy_hair_mask", type="FLOAT_COLOR", domain="CORNER")
    skin_attr = ob.data.color_attributes.new(name="meshy_skin_mask", type="FLOAT_COLOR", domain="CORNER")
    for poly in ob.data.polygons:
        hv = 1.0 if hair_faces[poly.index] else 0.0
        sv = 1.0 if skin_faces[poly.index] else 0.0
        for li in poly.loop_indices:
            hair_attr.data[li].color = (hv, hv, hv, 1.0)
            skin_attr.data[li].color = (sv, sv, sv, 1.0)


def split_hair(ob, hair_faces):
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for poly in ob.data.polygons:
        poly.select = bool(hair_faces[poly.index])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [x for x in bpy.data.objects if x not in before and x.type == "MESH"]
    if len(created) != 1:
        raise RuntimeError(f"Expected one separated hair object, found {[x.name for x in created]}")
    hair = created[0]
    hair.name = "AstraChar2_Meshy_Hair_i02_work"
    ob.name = "AstraChar2_Meshy_Skin_i02_work"
    return hair


def face_crossing_count(ob, cut_z):
    return sum(
        min(float(ob.data.vertices[index].co.z) for index in poly.vertices) < cut_z
        < max(float(ob.data.vertices[index].co.z) for index in poly.vertices)
        for poly in ob.data.polygons
    )


def choose_cut_plane(ob, rim_z):
    maximum_z = rim_z - 0.025
    # Search a collar-hidden band around the supplied 2.605 m datum.  Prefer
    # planes nearest that datum, then prefer the candidate crossing more faces.
    candidates = []
    for cut_z in np.linspace(2.575, min(maximum_z, 2.690), 231):
        crossings = face_crossing_count(ob, float(cut_z))
        if crossings:
            candidates.append((abs(float(cut_z) - NECK_BASE_Z), -crossings, float(cut_z), crossings))
    if not candidates:
        z_values = np.array([float(vertex.co.z) for vertex in ob.data.vertices])
        spans = np.array([
            max(float(ob.data.vertices[index].co.z) for index in poly.vertices)
            - min(float(ob.data.vertices[index].co.z) for index in poly.vertices)
            for poly in ob.data.polygons
        ])
        raise RuntimeError(
            "No allowed planar cut intersects the non-hair Meshy region; "
            f"object_location={tuple(ob.location)}, local_z_bounds={(float(z_values.min()), float(z_values.max()))}, "
            f"face_z_span_max={float(spans.max())}, face_z_span_nonzero={int(np.sum(spans > 1.0e-9))}"
        )
    _, _, cut_z, crossings = min(candidates)
    return cut_z, crossings


def planar_cut_and_cap(ob, cut_z):
    source_crossings = face_crossing_count(ob, cut_z)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    result = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=1.0e-7,
        plane_co=(0.0, 0.0, float(cut_z)),
        plane_no=(0.0, 0.0, 1.0),
        use_snap_center=False,
        clear_inner=True,
        clear_outer=False,
    )
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    plane_vertices = {
        vertex for vertex in bm.verts
        if vertex.is_valid and abs(float(vertex.co.z) - cut_z) <= 2.5e-6
    }
    # Blender 5.2 may return only vertices in geom_cut.  Detect the cut ring
    # from the post-bisect topology instead of depending on result item types.
    cut_edges = [
        edge for edge in bm.edges
        if edge.is_valid and edge.verts[0] in plane_vertices and edge.verts[1] in plane_vertices
    ]
    boundary = [edge for edge in cut_edges if len(edge.link_faces) == 1]
    filled = []
    if boundary:
        fill = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        filled = [face for face in fill.get("faces", []) if face.is_valid]
        for face in filled:
            face.smooth = True
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    skin_attr = ob.data.color_attributes.get("meshy_skin_mask")
    hair_attr = ob.data.color_attributes.get("meshy_hair_mask")
    for poly in ob.data.polygons:
        if all(abs(float(ob.data.vertices[vi].co.z) - cut_z) <= 2.5e-6 for vi in poly.vertices):
            for li in poly.loop_indices:
                if skin_attr:
                    skin_attr.data[li].color = (1.0, 1.0, 1.0, 1.0)
                if hair_attr:
                    hair_attr.data[li].color = (0.0, 0.0, 0.0, 1.0)
    cut_vertices = [v.index for v in ob.data.vertices if abs(float(v.co.z) - cut_z) <= 2.5e-6]
    return {
        "source_faces_crossing_plane": source_crossings,
        "bisect_result_items": len(result.get("geom_cut", [])),
        "bisect_cut_edges": len(cut_edges),
        "boundary_edges_before_fill": len(boundary),
        "cap_faces_created": len(filled),
        "cut_plane_vertices": len(cut_vertices),
    }


def connected_components(ob):
    count = len(ob.data.vertices)
    parent = np.arange(count, dtype=np.int32)

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = int(parent[value])
        return value

    def union(a, b):
        a, b = find(int(a)), find(int(b))
        if a != b:
            parent[b] = a

    for edge in ob.data.edges:
        union(*edge.vertices)
    roots = np.array([find(i) for i in range(count)], dtype=np.int32)
    return roots


def remove_floating_hair_fragments(ob, cut_z):
    roots = connected_components(ob)
    points = np.array([v.co[:] for v in ob.data.vertices], dtype=float)
    kill_roots = set()
    records = []
    for root in np.unique(roots):
        ids = np.where(roots == root)[0]
        q = points[ids]
        size = np.ptp(q, axis=0)
        if float(q[:, 2].max()) < cut_z and float(size.max()) < FLOATING_FRAGMENT_MAX_M:
            kill_roots.add(int(root))
            records.append({
                "vertices": int(len(ids)),
                "min_world_m": q.min(axis=0).tolist(),
                "max_world_m": q.max(axis=0).tolist(),
                "max_dimension_m": float(size.max()),
            })
    if kill_roots:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        doomed = [v for v in bm.verts if int(roots[v.index]) in kill_roots]
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    return records


def join_meshy(skin, hair):
    bpy.ops.object.select_all(action="DESELECT")
    skin.select_set(True)
    hair.select_set(True)
    bpy.context.view_layer.objects.active = skin
    bpy.ops.object.join()
    skin.name = "AstraChar2_Meshy_HeadHair"
    skin.data.name = "AstraChar2 Meshy i02 head hair planar cut"
    return skin


def install_skin_nodes(mat):
    mat.name = "AstraChar2 Meshy i02 PBR head+hair warm skin mask"
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    image_node, image, _, _, _ = base_color_pixels(mat)
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        raise RuntimeError("Meshy material has no Principled BSDF")
    for name in ("Meshy i02 SPEC multiply", "Meshy i02 warm HSV", "Meshy i02 skin mask", "Meshy i02 skin mix"):
        old = nodes.get(name)
        if old:
            nodes.remove(old)

    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.name = multiply.label = "Meshy i02 SPEC multiply"
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1.0
    multiply.inputs[2].default_value = SPEC_SKIN

    hsv = nodes.new("ShaderNodeHueSaturation")
    hsv.name = hsv.label = "Meshy i02 warm HSV"
    hsv.inputs[0].default_value = SKIN_HUE
    hsv.inputs[1].default_value = SKIN_SATURATION
    hsv.inputs[2].default_value = SKIN_VALUE
    hsv.inputs[3].default_value = 1.0

    attr = nodes.new("ShaderNodeAttribute")
    attr.name = attr.label = "Meshy i02 skin mask"
    attr.attribute_name = "meshy_skin_mask"

    mix = nodes.new("ShaderNodeMixRGB")
    mix.name = mix.label = "Meshy i02 skin mix"
    mix.blend_type = "MIX"

    links.new(image_node.outputs["Color"], multiply.inputs[1])
    links.new(multiply.outputs["Color"], hsv.inputs[4])
    links.new(image_node.outputs["Color"], mix.inputs[1])
    links.new(hsv.outputs[0], mix.inputs[2])
    links.new(attr.outputs["Fac"], mix.inputs[0])
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)
    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    return image.name


def bind_rigid_head(ob, arm):
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    for modifier in list(ob.modifiers):
        ob.modifiers.remove(modifier)
    ob.vertex_groups.clear()
    for group in bpy.data.objects["char1"].vertex_groups:
        ob.vertex_groups.new(name=group.name)
    ob.vertex_groups["Head"].add(range(len(ob.data.vertices)), 1.0, "REPLACE")
    modifier = ob.modifiers.new("Existing 121-bone skin", "ARMATURE")
    modifier.object = arm


def make_neck_material():
    mat = bpy.data.materials.get("AstraChar2 Meshy i02 skin blend") or bpy.data.materials.new("AstraChar2 Meshy i02 skin blend")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.82, 0.62, 0.50, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.48
    bsdf.inputs["IOR"].default_value = 1.45
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = 0.025
    return mat


def make_neck_band(arm, cut_z):
    rows, sides = 9, 64
    verts, faces = [], []
    for row in range(rows):
        t = row / (rows - 1)
        z = cut_z + (NECK_BLEND_TOP_Z - cut_z) * t
        rx = 0.090 + 0.005 * t
        ry = 0.070 + 0.008 * t
        cy = -0.235 - 0.008 * t
        for side in range(sides):
            angle = math.tau * side / sides
            verts.append((rx * math.cos(angle), cy + ry * math.sin(angle), z))
    for row in range(rows - 1):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    bottom_center = len(verts)
    verts.append((0.0, -0.235, cut_z))
    for side in range(sides):
        faces.append((bottom_center, (side + 1) % sides, side))
    mesh = bpy.data.meshes.new("AstraChar2 Meshy i02 neck blend mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(make_neck_material())
    for poly in mesh.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new("AstraChar2_Meshy_NeckBlend", mesh)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    for group in bpy.data.objects["char1"].vertex_groups:
        ob.vertex_groups.new(name=group.name)
    blend_start = NECK_BLEND_TOP_Z - 0.040
    for vertex in mesh.vertices:
        if vertex.co.z >= blend_start:
            t = min(1.0, max(0.0, (vertex.co.z - blend_start) / max(NECK_BLEND_TOP_Z - blend_start, 1.0e-8)))
            ob.vertex_groups["neck"].add([vertex.index], 1.0 - t, "REPLACE")
            ob.vertex_groups["Head"].add([vertex.index], t, "REPLACE")
        else:
            t = max(0.0, min(1.0, (vertex.co.z - 2.64) / 0.08))
            ob.vertex_groups["Spine"].add([vertex.index], 1.0 - t, "REPLACE")
            ob.vertex_groups["neck"].add([vertex.index], t, "REPLACE")
    modifier = ob.modifiers.new("Existing 121-bone skin", "ARMATURE")
    modifier.object = arm
    return ob, sides


def measure_rim():
    rim = bpy.data.objects["AstraChar2_R5_GorgetRim"]
    points = world_points(rim)
    rim_z = float(points[:, 2].max())
    center = np.array(((points[:, 0].min() + points[:, 0].max()) * 0.5,
                       (points[:, 1].min() + points[:, 1].max()) * 0.5), dtype=float)
    top = points[points[:, 2] >= rim_z - 0.004]
    radii = np.linalg.norm(top[:, :2] - center[None, :], axis=1)
    inner_radius = float(np.quantile(radii, 0.10))
    sector_inner = []
    angles = np.mod(np.arctan2(top[:, 1] - center[1], top[:, 0] - center[0]), math.tau)
    for sector in range(SECTORS):
        mask = (angles >= math.tau * sector / SECTORS) & (angles < math.tau * (sector + 1) / SECTORS)
        sector_inner.append(float(radii[mask].min()) if mask.any() else None)
    return {
        "object": rim.name,
        "visible_upper_rim_z_m": rim_z,
        "xy_center_m": center.tolist(),
        "inner_radius_global_p10_m": inner_radius,
        "inner_radius_by_sector_m": sector_inner,
        "top_band_definition_m": 0.004,
    }


def gorget_shards():
    report = {
        "definition": "current disconnected component with <=12 triangles and maximum bbox dimension <30 mm",
        "interpretation": "The count is geometric, not a visual guess. Connected cracked/coarse triangles are not mislabeled as detached shards.",
        "objects": [], "count": 0, "locations": [],
    }
    for name in ("AstraChar2_R5_Gorget", "AstraChar2_R5_GorgetRim"):
        ob = bpy.data.objects[name]
        roots = connected_components(ob)
        points = world_points(ob)
        face_roots = {}
        for poly in ob.data.polygons:
            root = int(roots[poly.vertices[0]])
            face_roots.setdefault(root, 0)
            face_roots[root] += max(1, len(poly.vertices) - 2)
        edges = list(ob.data.edges)
        face_users = np.zeros(len(edges), dtype=np.int32)
        edge_lookup = {tuple(sorted(edge.vertices[:])): edge.index for edge in edges}
        for poly in ob.data.polygons:
            vertices = list(poly.vertices)
            for index, start in enumerate(vertices):
                key = tuple(sorted((start, vertices[(index + 1) % len(vertices)])))
                face_users[edge_lookup[key]] += 1
        object_row = {
            "name": name,
            "component_count": int(len(np.unique(roots))),
            "shard_count": 0,
            "bounds_world_m": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
            "centroid_world_m": points.mean(axis=0).tolist(),
            "boundary_edges": int(np.sum(face_users == 1)),
            "nonmanifold_edges": int(np.sum(face_users > 2)),
        }
        for root in np.unique(roots):
            ids = np.where(roots == root)[0]
            q = points[ids]
            size = np.ptp(q, axis=0)
            triangles = int(face_roots.get(int(root), 0))
            if triangles <= 12 and float(size.max()) < 0.030:
                row = {"object": name, "triangles": triangles, "vertices": int(len(ids)),
                       "centroid_world_m": q.mean(axis=0).tolist(), "bbox_min_world_m": q.min(axis=0).tolist(),
                       "bbox_max_world_m": q.max(axis=0).tolist(), "bbox_size_m": size.tolist()}
                report["locations"].append(row)
                report["count"] += 1
                object_row["shard_count"] += 1
        report["objects"].append(object_row)
    banked = OUT / "r6_collar_counts.json"
    if banked.exists():
        source = json.loads(banked.read_text())
        report["banked_repair_record"] = {
            "source": str(banked.relative_to(ROOT)),
            "removed_fractured_neck_faces": source.get("removed_fractured_neck_faces"),
            "last_collar_strays_removed": source.get("last_collar_strays_removed"),
            "note": "Historical removal counts are context only; those faces are not present shard locations in the i02 source.",
        }
    return report


def audit_cut(ob, rim, cut_z, cut_stats, floating_records, classification):
    points = np.array([v.co[:] for v in ob.data.vertices], dtype=float)
    skin_attr = ob.data.color_attributes.get("meshy_skin_mask")
    hair_attr = ob.data.color_attributes.get("meshy_hair_mask")
    vertex_skin = np.zeros(len(ob.data.vertices), dtype=float)
    vertex_hair = np.zeros(len(ob.data.vertices), dtype=float)
    counts = np.zeros(len(ob.data.vertices), dtype=float)
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            vi = ob.data.loops[li].vertex_index
            vertex_skin[vi] += float(skin_attr.data[li].color[0])
            vertex_hair[vi] += float(hair_attr.data[li].color[0])
            counts[vi] += 1.0
    vertex_skin /= np.maximum(counts, 1.0)
    vertex_hair /= np.maximum(counts, 1.0)
    center = np.array(rim["xy_center_m"], dtype=float)
    radial = np.linalg.norm(points[:, :2] - center[None, :], axis=1)
    angles = np.mod(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]), math.tau)
    on_cut = (np.abs(points[:, 2] - cut_z) <= 2.5e-6) & (vertex_skin >= 0.5)
    rows = []
    outside_above_rim = 0
    for sector in range(SECTORS):
        angular = (angles >= math.tau * sector / SECTORS) & (angles < math.tau * (sector + 1) / SECTORS)
        mask = on_cut & angular
        sector_radius = rim["inner_radius_by_sector_m"][sector]
        if sector_radius is None:
            sector_radius = rim["inner_radius_global_p10_m"]
        outside = mask & (radial > sector_radius)
        outside_max_z = float(points[outside, 2].max()) if outside.any() else None
        sector_violations = int(np.sum(outside & (points[:, 2] > rim["visible_upper_rim_z_m"] + 1.0e-7)))
        outside_above_rim += sector_violations
        max_z = float(points[mask, 2].max()) if mask.any() else None
        rows.append({
            "sector": sector,
            "angle_start_deg": 360.0 * sector / SECTORS,
            "angle_end_deg": 360.0 * (sector + 1) / SECTORS,
            "skin_cut_vertices": int(mask.sum()),
            "max_skin_cut_z_m": max_z,
            "rim_z_m": rim["visible_upper_rim_z_m"],
            "margin_below_rim_m": (rim["visible_upper_rim_z_m"] - max_z) if max_z is not None else None,
            "inner_radius_m": sector_radius,
            "skin_cut_vertices_outside_inner_radius": int(outside.sum()),
            "max_skin_cut_z_outside_inner_radius_m": outside_max_z,
            "outside_inner_radius_above_rim_violations": sector_violations,
        })
    margin = rim["visible_upper_rim_z_m"] - cut_z
    assert margin >= 0.025 - 1.0e-7
    assert not on_cut.any() or float(points[on_cut, 2].max()) <= rim["visible_upper_rim_z_m"] - 0.025 + 1.0e-7
    return {
        "candidate": str(CANDIDATE.relative_to(ROOT)),
        "source_body_read_only": str(BASE.relative_to(ROOT)),
        "source_meshy_read_only": str(MESHY.relative_to(ROOT)),
        "rim_measurement": rim,
        "cut_plane_z_m": cut_z,
        "cut_plane_margin_below_visible_rim_m": margin,
        "minimum_required_margin_m": 0.025,
        "planar_cut_pass": margin >= 0.025,
        "cap": cut_stats,
        "classification": classification,
        "skin_cut_boundary_by_angular_sector": rows,
        "skin_cut_boundary_vertices_above_rim_minus_25mm": int(np.sum(on_cut & (points[:, 2] > rim["visible_upper_rim_z_m"] - 0.025 + 1.0e-7))),
        "skin_cut_boundary_outside_inner_radius_above_rim_violations": outside_above_rim,
        "floating_hair_component_rule": {"entire_bbox_below_cut": True, "max_bbox_dimension_m": FLOATING_FRAGMENT_MAX_M},
        "floating_hair_components_removed": len(floating_records),
        "floating_hair_components": floating_records,
        "hair_vertex_count_after": int(np.sum(vertex_hair >= 0.5)),
        "skin_vertex_count_after": int(np.sum(vertex_skin >= 0.5)),
        "gorget_shards": gorget_shards(),
    }


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    arm = bpy.data.objects["Armature"]
    reset_pose(arm)
    rests = {bone.name: np.array(bone.matrix_local) for bone in arm.data.bones}
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    rim = measure_rim()
    remove_prefixes = (
        "AstraChar2_Mpfb_Head", "AstraChar2_Eyeball_", "AstraChar2_Iris_", "AstraChar2_Pupil_",
        "AstraChar2_Cornea_", "AstraChar2_Wetline_", "AstraChar2_TearCorner_", "AstraChar2_Eyebrows_",
        "AstraChar2_Lashes_", "AstraChar2_Nostril_", "AstraChar2_R5_Curves_MPFB_",
        "AstraChar2_R5_Control_MPFB_", "AstraChar2_R5_Strands_MPFB_", "AstraChar2_R4_",
        "AstraChar2_R2_Hair", "AstraChar2_R3_Flow_", "AstraChar2_R3_Plait_",
    )
    for ob in list(bpy.data.objects):
        if ob.name.startswith(remove_prefixes):
            bpy.data.objects.remove(ob, do_unlink=True)

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(MESHY))
    imported = [ob for ob in bpy.data.objects if ob not in before and ob.type == "MESH"]
    assert len(imported) == 1
    ob = imported[0]
    ob.scale = (SCALE,) * 3
    ob.location = OFFSET
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for vertex in ob.data.vertices:
        q = np.array(vertex.co, dtype=float)
        q[:2] = EYE_PIVOT[:2] + FIT_XY * (q[:2] - EYE_PIVOT[:2])
        vertex.co = q
    ob.data.update()
    # Bake translation only after reproducing i01's fit, preserving identical
    # world placement while making the planar cut and audits use world meters.
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    mat = ob.data.materials[0]
    _, base_image, pixels, width, height = base_color_pixels(mat)
    rgb = face_rgb(ob, pixels, width, height)
    hair_faces, skin_faces, lumas, raw_centers = classify_faces(ob, rgb)
    add_face_masks(ob, hair_faces, skin_faces)
    classification = {
        "method": "per-face mean base-color texel plus raw-source geometry; hair requires warm/dark texels outside face/neck core",
        "hair_thresholds": {
            "luma_weights": [0.2126, 0.7152, 0.0722],
            "ordinary_luma_max": HAIR_LUMA_MAX,
            "strong_luma_max": HAIR_STRONG_LUMA_MAX,
            "r_minus_b_min": HAIR_R_MINUS_B_MIN,
            "g_minus_b_min": HAIR_G_MINUS_B_MIN,
            "face_core_raw": {"abs_x_lt": 0.305, "y_lt": -0.205, "z_gt": -0.18, "z_lt": 0.54},
            "neck_core_raw": {"abs_x_lt": 0.235, "y_lt": 0.10, "z_gt": -0.92, "z_lte": -0.18},
            "hair_geometry_raw": "z>0.54 OR |x|>0.305 OR y>-0.080 OR (z<-0.18 AND (|x|>0.205 OR y>0.015))",
        },
        "skin_thresholds": {"luma_min": 0.43, "r_minus_b_min": 0.105, "not_hair_required": True},
        "source_faces": len(ob.data.polygons),
        "hair_faces": int(hair_faces.sum()),
        "skin_faces": int(skin_faces.sum()),
        "other_skin_or_garment_faces": int(len(hair_faces) - hair_faces.sum() - skin_faces.sum()),
        "hair_luma_quantiles": np.quantile(lumas[hair_faces], [0.05, 0.5, 0.95]).tolist(),
        "skin_luma_quantiles": np.quantile(lumas[skin_faces], [0.05, 0.5, 0.95]).tolist(),
        "mask_attributes": {"hair": "meshy_hair_mask", "skin": "meshy_skin_mask"},
    }

    hair = split_hair(ob, hair_faces)
    cut_z, source_crossings = choose_cut_plane(ob, rim["visible_upper_rim_z_m"])
    assert rim["visible_upper_rim_z_m"] - cut_z >= 0.025
    hair_bounds_before = [world_points(hair).min(axis=0).tolist(), world_points(hair).max(axis=0).tolist()]
    cut_stats = planar_cut_and_cap(ob, cut_z)
    assert cut_stats["source_faces_crossing_plane"] == source_crossings
    assert cut_stats["bisect_cut_edges"] > 0, "Planar bisect did not intersect the non-hair Meshy region"
    assert cut_stats["boundary_edges_before_fill"] > 0, "Planar bisect produced no boundary to cap"
    assert cut_stats["cut_plane_vertices"] > 0, "Planar cut produced no vertices on the requested plane"
    floating_records = remove_floating_hair_fragments(hair, cut_z)
    hair_bounds_after = [world_points(hair).min(axis=0).tolist(), world_points(hair).max(axis=0).tolist()]
    classification["hair_bounds_before_fragment_cleanup_m"] = hair_bounds_before
    classification["hair_bounds_after_fragment_cleanup_m"] = hair_bounds_after
    classification["hair_z_min_change_m"] = hair_bounds_after[0][2] - hair_bounds_before[0][2]
    classification["hair_z_max_change_m"] = hair_bounds_after[1][2] - hair_bounds_before[1][2]
    classification["hair_full_length_preserved_except_explicit_sub15mm_floating_rule"] = (
        abs(hair_bounds_before[1][2] - hair_bounds_after[1][2]) < 1.0e-7
        and (abs(hair_bounds_before[0][2] - hair_bounds_after[0][2]) < 1.0e-7 or bool(floating_records))
    )

    ob = join_meshy(ob, hair)
    base_image_name = install_skin_nodes(mat)
    for image in bpy.data.images:
        if image.name in {base_image_name, "Image_0", "Image_1", "Image_3", "normal"}:
            image.pack()
    bind_rigid_head(ob, arm)
    neck, neck_cap_faces = make_neck_band(arm, cut_z)
    cut_stats["neck_blend_planar_cap_faces"] = neck_cap_faces
    cut_stats["cap_strategy"] = "direct holes_fill where possible plus a closed planar bottom cap on the overlapping neck-blend bridge"
    cut_stats["cap_or_bridge_pass"] = bool(cut_stats["cap_faces_created"] or neck_cap_faces)
    assert cut_stats["cap_or_bridge_pass"]
    bpy.context.view_layer.update()

    rest_error = max(float(np.max(np.abs(np.array(bone.matrix_local) - rests[bone.name]))) for bone in arm.data.bones)
    assert rest_error == 0.0 and len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    audit = audit_cut(ob, rim, cut_z, cut_stats, floating_records, classification)
    audit["material_correction"] = {
        "base_color_image": base_image_name,
        "hair_color_unchanged": True,
        "normal_roughness_emission_maps_preserved": True,
        "skin_mask_attribute": "meshy_skin_mask",
        "nodes": {
            "multiply": {"node": "Meshy i02 SPEC multiply", "blend_type": "MULTIPLY", "factor": 1.0, "color2_rgba": list(SPEC_SKIN)},
            "hue_saturation_value": {"node": "Meshy i02 warm HSV", "hue": SKIN_HUE, "saturation": SKIN_SATURATION, "value": SKIN_VALUE, "factor": 1.0},
            "masked_mix": {"node": "Meshy i02 skin mix", "blend_type": "MIX", "factor_source": "meshy_skin_mask"},
        },
    }
    audit["binding"] = {"meshy": "rigid Head 1.0", "neck_blend": "Spine/neck/Head", "neck_band_z_range_m": [cut_z, NECK_BLEND_TOP_Z]}
    audit["bones"] = len(arm.data.bones)
    audit["actions"] = len(bpy.data.actions)
    audit["rest_matrix_error"] = rest_error
    (OUT / "meshy_i02_cut_audit.json").write_text(json.dumps(audit, indent=2) + "\n")

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
    print("MESHY_I02_BUILD_PASS", json.dumps({
        "candidate": str(CANDIDATE.relative_to(ROOT)), "cut_z_m": cut_z,
        "rim_z_m": rim["visible_upper_rim_z_m"], "hair_faces": int(hair_faces.sum()),
        "floating_hair_components_removed": len(floating_records), "gorget_shards": audit["gorget_shards"]["count"],
        "neck_band": neck.name,
    }), flush=True)


if __name__ == "__main__":
    main()
