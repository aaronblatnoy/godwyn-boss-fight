"""Fit and graft the approved Meshy head/hair onto the protected Godwyn body."""
import bpy
import bmesh
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
BASE = ROOT / "models/astra_character_v2_pre_likeness.blend"
GLB = ROOT / "models/meshy_head_approved.glb"
CANDIDATE = ROOT / "models/astra_character_v2_meshy_i01.blend"
SCALE = .31
FIT_XY = 1.05
OFFSET = np.array((.00043, -.2519, 2.8552))
NECK_CUT = 2.745
NECK_BASE = 2.605


def reset(arm):
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def image_pixels(mat):
    node = next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and
                any(link.to_socket.name == "Base Color" for link in n.outputs["Color"].links))
    im = node.image
    w, h = im.size
    return im, np.asarray(im.pixels[:], dtype=np.float32).reshape(h, w, 4), w, h


def trim_lower_bust(ob):
    mat = ob.data.materials[0]
    _, pixels, w, h = image_pixels(mat)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.active
    kill = []
    for face in bm.faces:
        c = face.calc_center_median()
        if c.z >= -.36:
            continue
        colors = []
        for loop in face.loops:
            u, v = loop[uv].uv
            x = min(w - 1, max(0, int(u * (w - 1))))
            y = min(h - 1, max(0, int(v * (h - 1))))
            colors.append(pixels[y, x, :3])
        rgb = np.mean(colors, axis=0)
        luma = float(rgb @ np.array((.2126, .7152, .0722)))
        goldish = rgb[0] > rgb[2] * 1.55 and rgb[1] > rgb[2] * 1.22
        broad = abs(c.x) > .34
        deep = c.z < -.70
        # Meshy fused a large part of the source bust/collar into the same
        # triangle soup as the face and hair.  Keep the darker long hair but
        # remove pale skin/garment islands below the prior MPFB neck cut.
        central_front = abs(c.x) < .46 and c.y < .32
        # Preserve Meshy's own narrow neck down into the gorget.  Only trim
        # the lower central chest and upward-facing shoulder/collar facets.
        bust_skin = central_front and c.z < -.55 and luma > .60
        shoulder_skin = broad and face.normal.z > .25 and luma > .58
        geometric_bust = c.z < -.50 and abs(c.x) < .38
        old_lower = c.z < -.43
        if bust_skin or shoulder_skin or geometric_bust or (old_lower and deep and luma > .70) or (old_lower and goldish and luma > .74):
            kill.append(face)
    removed = len(kill)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return removed


def bind_meshy(ob, arm):
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    for mod in list(ob.modifiers):
        ob.modifiers.remove(mod)
    ob.vertex_groups.clear()
    for group in bpy.data.objects["char1"].vertex_groups:
        ob.vertex_groups.new(name=group.name)
    head = ob.vertex_groups["Head"]
    neck = ob.vertex_groups["neck"]
    spine = ob.vertex_groups["Spine"]
    counts = {"head": len(ob.data.vertices), "neck_blend": 0}
    head.add(range(len(ob.data.vertices)), 1.0, "REPLACE")
    mod = ob.modifiers.new("Existing 121-bone skin", "ARMATURE")
    mod.object = arm
    return counts
    # Retained below as a documented rejected experiment: per-vertex geometric
    # neck inference split Meshy disconnected triangle patches and stretched.
    for vert in ob.data.vertices:
        p = ob.matrix_world @ vert.co
        raw = (np.array(p) - OFFSET) / SCALE
        central_neck = raw[2] < -.10 and abs(raw[0]) < .30 and raw[1] < .26
        if not central_neck:
            head.add([vert.index], 1.0, "REPLACE")
            counts["head"] += 1
        elif p.z >= 2.79:
            head.add([vert.index], 1.0, "REPLACE")
            counts["head"] += 1
        elif p.z >= 2.72:
            t = (p.z - 2.72) / .07
            neck.add([vert.index], 1.0 - t, "REPLACE")
            head.add([vert.index], t, "REPLACE")
            counts["neck_blend"] += 1
        else:
            t = max(0.0, min(1.0, (p.z - 2.64) / .08))
            spine.add([vert.index], 1.0 - t, "REPLACE")
            neck.add([vert.index], t, "REPLACE")
            counts["neck_blend"] += 1
    mod = ob.modifiers.new("Existing 121-bone skin", "ARMATURE")
    mod.object = arm
    return counts


def make_neck_material():
    mat = bpy.data.materials.new("AstraChar2 Meshy skin blend")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (.82, .62, .50, 1.0)
    bsdf.inputs["Roughness"].default_value = .48
    bsdf.inputs["IOR"].default_value = 1.45
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = .025
    return mat


def neck_band(arm, mat):
    verts = []
    faces = []
    rows, sides = 9, 64
    for i in range(rows):
        t = i / (rows - 1)
        z = NECK_BASE + (2.700 - NECK_BASE) * t
        rx = .090 + .005 * t
        ry = .070 + .008 * t
        cy = -.235 - .008 * t
        for j in range(sides):
            a = math.tau * j / sides
            verts.append((rx * math.cos(a), cy + ry * math.sin(a), z))
    for i in range(rows - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    me = bpy.data.meshes.new("AstraChar2 Meshy neck blend mesh")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("AstraChar2_Meshy_NeckBlend", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    for group in bpy.data.objects["char1"].vertex_groups:
        ob.vertex_groups.new(name=group.name)
    for v in ob.data.vertices:
        if v.co.z >= 2.66:
            t = min(1.0, (v.co.z - 2.66) / .04)
            ob.vertex_groups["neck"].add([v.index], 1 - t, "REPLACE")
            ob.vertex_groups["Head"].add([v.index], t, "REPLACE")
        else:
            t = max(0.0, min(1.0, (v.co.z - 2.64) / .08))
            ob.vertex_groups["Spine"].add([v.index], 1 - t, "REPLACE")
            ob.vertex_groups["neck"].add([v.index], t, "REPLACE")
    mod = ob.modifiers.new("Existing 121-bone skin", "ARMATURE")
    mod.object = arm
    return ob


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    arm = bpy.data.objects["Armature"]
    reset(arm)
    rests = {b.name: np.array(b.matrix_local) for b in arm.data.bones}
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    old_head = bpy.data.objects["AstraChar2_Mpfb_Head"]
    old_p = np.array([old_head.matrix_world @ v.co for v in old_head.data.vertices], float)
    eyes = {}
    for side in ("L", "R"):
        eye = bpy.data.objects["AstraChar2_Eyeball_" + side]
        p = np.array([eye.matrix_world @ v.co for v in eye.data.vertices], float)
        eyes[side] = ((p.min(0) + p.max(0)) * .5).tolist()
    remove_prefixes = ("AstraChar2_Mpfb_Head", "AstraChar2_Eyeball_", "AstraChar2_Iris_",
                       "AstraChar2_Pupil_", "AstraChar2_Cornea_", "AstraChar2_Wetline_",
                       "AstraChar2_TearCorner_", "AstraChar2_Eyebrows_", "AstraChar2_Lashes_",
                       "AstraChar2_Nostril_", "AstraChar2_R5_Curves_MPFB_",
                       "AstraChar2_R5_Control_MPFB_", "AstraChar2_R5_Strands_MPFB_",
                       "AstraChar2_R4_", "AstraChar2_R2_Hair", "AstraChar2_R3_Flow_",
                       "AstraChar2_R3_Plait_")
    removed_objects = []
    for ob in list(bpy.data.objects):
        if ob.name.startswith(remove_prefixes):
            removed_objects.append(ob.name)
            bpy.data.objects.remove(ob, do_unlink=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    assert len(imported) == 1
    ob = imported[0]
    raw = np.array([v.co[:] for v in ob.data.vertices], float)
    raw_bounds = [raw.min(0).tolist(), raw.max(0).tolist()]
    removed_faces = trim_lower_bust(ob)
    ob.name = "AstraChar2_Meshy_HeadHair"
    ob.data.name = "AstraChar2 Meshy approved head and hair"
    ob.scale = (SCALE,) * 3
    ob.location = OFFSET
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mat = ob.data.materials[0]
    pivot = np.array((.00043, -.37956585, 2.9765501))
    for vert in ob.data.vertices:
        q = np.array(vert.co)
        q[:2] = pivot[:2] + FIT_XY * (q[:2] - pivot[:2])
        vert.co = q
    ob.data.update()
    mat.name = "AstraChar2 Meshy approved PBR head+hair"
    for image in bpy.data.images:
        if image.name in {"Image_0", "Image_1", "Image_3", "normal"}:
            image.pack()
    weight_counts = bind_meshy(ob, arm)
    band = neck_band(arm, make_neck_material())
    bpy.context.view_layer.update()
    p = np.array([ob.matrix_world @ v.co for v in ob.data.vertices], float)
    post_bounds = [p.min(0).tolist(), p.max(0).tolist()]
    error = max(float(np.max(np.abs(np.array(b.matrix_local) - rests[b.name]))) for b in arm.data.bones)
    assert error == 0 and len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    target_eye = np.mean(np.array(list(eyes.values())), axis=0)
    source_landmarks = {"eye_line_z_proxy_raw": .391, "chin_z_proxy_raw": -.163,
                        "crown_z_raw": float(raw[:, 2].max()), "ear_width_proxy_raw": 1.00,
                        "neck_seam_proxy_raw": -.807}
    transformed_landmarks = {k.replace("_raw", "_world_m"): (float(v * SCALE + OFFSET[2]) if "width" not in k else float(v * SCALE))
                             for k, v in source_landmarks.items()}
    transformed_landmarks["eye_center_x_world_m"] = float(OFFSET[0])
    transformed_landmarks["neck_seam_proxy_world_m"] = float(source_landmarks["neck_seam_proxy_raw"] * SCALE + OFFSET[2])
    fit = {
        "source": str(GLB.relative_to(ROOT)), "candidate": str(CANDIDATE.relative_to(ROOT)),
        "orientation": "GLB already upright and facing -Y; no rotation applied.",
        "uniform_scale": SCALE, "translation_m": OFFSET.tolist(),
        "postfit_xy_scale_about_eye_line": FIT_XY,
        "mpfb": {"eye_centers_world_m": eyes, "eye_line_z_m": float(target_eye[2]),
                 "chin_proxy_z_m": 2.78, "crown_z_m": float(old_p[:, 2].max()),
                 "ear_width_m": float(np.quantile(old_p[:, 0], .995) - np.quantile(old_p[:, 0], .005)),
                 "prior_neck_cut_z_m": NECK_CUT, "collar_hidden_base_z_m": NECK_BASE},
        "meshy_raw_landmark_proxies": source_landmarks,
        "meshy_transformed_landmark_proxies": transformed_landmarks,
        "raw_bounds": raw_bounds, "post_trim_world_bounds": post_bounds,
        "removed_lower_bust_faces": removed_faces, "removed_legacy_objects": removed_objects,
        "weighting": {"method": "inseparable Meshy head+hair rigid Head binding; separate hidden neck band uses the proven Head/neck/Spine blend",
                      "counts": weight_counts},
        "neck_blend": {"object": band.name, "rows": 9, "sides": 64,
                       "z_range_m": [NECK_BASE, 2.700], "inside_gorget": True},
        "material": {"name": mat.name, "pbr_maps_preserved": True, "repainted": False,
                     "subsurface_added": False,
                     "reason": "Single fused skin/hair/eyes material has no reliable skin-only mask; only the separate neck blend uses a modest 0.025 SSS weight."},
        "bones": 121, "actions": 0, "rest_matrix_error": error,
    }
    (OUT / "meshy_fit.json").write_text(json.dumps(fit, indent=2) + "\n")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
    print("MESHY_BUILD_PASS", json.dumps({"candidate": str(CANDIDATE), "bounds": post_bounds,
          "removed_faces": removed_faces, "weights": weight_counts}), flush=True)


if __name__ == "__main__":
    main()
