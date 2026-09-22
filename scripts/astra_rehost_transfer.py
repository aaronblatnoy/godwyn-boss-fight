"""Rehost the five approved actions onto the immutable published char2 base.

Each output starts from the byte-copied v2 base, retains the source clip's full
staging scene, replaces only its old character objects, copies the approved
Armature action without retargeting, reapplies the derived-only grip repair,
and saves only the requested new files.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from astra_move_grip_fix import fix_grip

BASE = ROOT / "models/astra_move_character_base_v2.blend"
OUT = ROOT / "renders/astra/rehost"
TINT_MATERIALS = {
    "Astra Round2 royal blue and continuous gold trim",
    "Astra Round2 royal blue undersleeves",
}
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_wip.blend",
                   ROOT / "models/astra_move_idle_guard_v2_wip.blend"),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_wip.blend",
                   ROOT / "models/astra_move_walk_stalk_v2_wip.blend"),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_wip.blend",
                     ROOT / "models/astra_move_lunge_thrust_v2_wip.blend"),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_wip.blend",
                    ROOT / "models/astra_move_rising_spin_v2_wip.blend"),
    "xslash": (ROOT / "models/astra_xslash_v2_final_wip.blend",
               ROOT / "models/astra_xslash_v2_final_on_char2_wip.blend"),
}


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def action_digest(action):
    h = hashlib.sha256()
    curves = [fc for layer in action.layers for strip in layer.strips
              for bag in strip.channelbags for fc in bag.fcurves]
    for fc in sorted(curves, key=lambda x: (x.data_path, x.array_index)):
        h.update(f"{fc.data_path}|{fc.array_index}|".encode())
        for key in fc.keyframe_points:
            h.update(("%.9g,%.9g,%s;" %
                      (key.co.x, key.co.y, key.interpolation)).encode())
        for mod in fc.modifiers:
            h.update(f"mod:{mod.type};".encode())
    return h.hexdigest(), len(curves), sum(len(fc.keyframe_points) for fc in curves)


def original_name(name):
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def apply_blue(materials):
    applied = []
    for material in materials:
        if material.name not in TINT_MATERIALS or not material.node_tree:
            continue
        nt = material.node_tree
        if nt.nodes.get("Astra Rehost Deep Blue") or nt.nodes.get("Astra XSlash Final Deep Blue Multiply") or nt.nodes.get("Astra Move Deep Blue"):
            applied.append({"material": material.name, "status": "existing override retained"})
            continue
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        color = bsdf.inputs["Base Color"].links[0].from_socket
        metallic = bsdf.inputs["Metallic"].links[0].from_socket
        scale = nt.nodes.new("ShaderNodeMixRGB")
        scale.name = "Astra Rehost Deep Blue"
        scale.blend_type = "MULTIPLY"
        scale.inputs[0].default_value = 1.0
        scale.inputs[2].default_value = (.025, .20, .62, 1.0)
        nt.links.new(color, scale.inputs[1])
        bypass = nt.nodes.new("ShaderNodeMixRGB")
        bypass.name = "Astra Rehost Preserve Gold"
        nt.links.new(metallic, bypass.inputs[0])
        nt.links.new(scale.outputs[0], bypass.inputs[1])
        nt.links.new(color, bypass.inputs[2])
        nt.links.new(bypass.outputs[0], bsdf.inputs["Base Color"])
        applied.append({"material": material.name, "status": "override added"})
    return applied


def rehost(name, source, target):
    base_sha = file_hash(BASE)
    source_sha = file_hash(source)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    character_scene = bpy.context.scene
    # Preserve the complete published character assembly, including hidden
    # retired surfaces, native curves, portable fibers, brows and eye inserts.
    character_objects = [o for o in character_scene.objects
                         if o.type not in {"LIGHT", "CAMERA"}
                         and o.name != "Astra evaluation ground"]
    character_set = set(character_objects)
    rig = bpy.data.objects["Armature"]
    body = bpy.data.objects["char1"]
    sword = bpy.data.objects["Godwyn_Sword"]
    materials = {m for o in character_objects if o.type == "MESH"
                 for m in o.data.materials if m}

    with bpy.data.libraries.load(str(source), link=False) as (src, dst):
        assert len(src.scenes) == 1
        dst.scenes = src.scenes[:]
    scene = dst.scenes[0]
    bpy.context.window.scene = scene
    appended = set(scene.objects)
    old_rig = next(o for o in appended if o.type == "ARMATURE")
    old_body = next(o for o in appended if original_name(o.name) == "char1")
    old_sword = next(o for o in appended if original_name(o.name) == "Godwyn_Sword")
    old_under = next((o for o in appended if original_name(o.name) == "Astra_Undersleeves"), None)
    source_action = old_rig.animation_data.action
    source_digest, curve_count, key_count = action_digest(source_action)

    for obj in character_objects:
        scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    assert len(old_rig.data.bones) == len(rig.data.bones) == 121
    assert set(old_rig.pose.bones.keys()) == set(rig.pose.bones.keys())
    rest_error = max(abs(old_rig.data.bones[n].matrix_local[i][j] -
                         rig.data.bones[n].matrix_local[i][j])
                     for n in old_rig.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0.0
    assert old_rig.matrix_world == rig.matrix_world
    for bone in old_rig.data.bones:
        other = rig.data.bones[bone.name]
        assert (bone.parent.name if bone.parent else None) == (other.parent.name if other.parent else None)
    for obj in character_objects:
        if obj.type == "MESH":
            for mod in obj.modifiers:
                if mod.type == "ARMATURE":
                    assert mod.object == rig
    assert sword.parent == rig and sword.parent_type == "OBJECT"
    assert list(sword.vertex_groups.keys()) == ["RightHand"]
    assert all(len(v.groups) == 1 and abs(v.groups[0].weight - 1.0) < 1e-7
               for v in sword.data.vertices)

    for bone in old_rig.pose.bones:
        other = rig.pose.bones[bone.name]
        other.rotation_mode = bone.rotation_mode
        other.scale = bone.scale
    rig.animation_data_clear()
    rig.animation_data_create()
    transferred = source_action.copy()
    transferred.name = source_action.name + "_OnChar2"
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    copied_digest, copied_curves, copied_keys = action_digest(transferred)
    assert (copied_digest, copied_curves, copied_keys) == (source_digest, curve_count, key_count)

    # Directly prove the same pose matrices at every authored quarter-frame.
    mesh_states = [(o, o.hide_viewport) for o in scene.objects if o.type in {"MESH", "CURVES"}]
    for obj, _ in mesh_states:
        obj.hide_viewport = True
    samples_end = int(round(source_action.frame_range[1]))
    pose_error = 0.0
    for qf in range(4, 4 * samples_end + 1):
        frame = qf / 4.0
        scene.frame_set(int(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        for bone in old_rig.pose.bones:
            other = rig.pose.bones[bone.name]
            pose_error = max(pose_error, max(abs(bone.matrix[i][j] - other.matrix[i][j])
                                             for i in range(4) for j in range(4)))
    assert pose_error < 1e-6, pose_error
    for obj, hidden in mesh_states:
        obj.hide_viewport = hidden

    for obj in [old_rig, old_body, old_sword, old_under]:
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    retained = set(scene.objects)
    for obj in list(bpy.data.objects):
        if obj not in retained:
            bpy.data.objects.remove(obj, do_unlink=True)

    scene.name = "Astra Rehost " + name
    scene["astra_rehost"] = name
    scene["astra_character_source_sha256"] = base_sha
    scene["astra_action_source_sha256"] = source_sha
    scene["astra_action_digest"] = source_digest
    scene["astra_retargeting"] = False
    scene.render.fps = 30
    scene.frame_start = 1
    # Keep the source scene's authored output range; cyclic action endpoints
    # remain present in the action but omitted from the rendered range.
    if name == "idle_guard":
        scene.frame_end = 96
    elif name == "walk_stalk":
        scene.frame_end = 72
    else:
        scene.frame_end = samples_end

    # Reapply the move-only static repair to the new, denser char2 body.
    fix_grip()
    grip_props = {k: body[k] for k in body.keys() if k.startswith("astra_move_")}
    blue = apply_blue(materials)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    assert file_hash(BASE) == base_sha and file_hash(source) == source_sha
    target_sha = file_hash(target)
    report = {
        "name": name,
        "method": "complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting",
        "base": str(BASE.relative_to(ROOT)),
        "base_sha256": base_sha,
        "action_source": str(source.relative_to(ROOT)),
        "action_source_sha256": source_sha,
        "output": str(target.relative_to(ROOT)),
        "output_sha256": target_sha,
        "bone_count": len(rig.pose.bones),
        "rest_matrix_max_error": rest_error,
        "quarter_frame_pose_matrix_max_error": pose_error,
        "action_digest": source_digest,
        "action_data_identical": True,
        "action_fcurves": curve_count,
        "action_keys": key_count,
        "samples_end": samples_end,
        "render_frame_end": scene.frame_end,
        "character_objects_retained": len(character_set),
        "final_scene_objects": len(scene.objects),
        "grip_repair": grip_props,
        "blue_material_override": blue,
        "source_files_unchanged": True,
        "blender_version": bpy.app.version_string,
    }
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "transfer_verification.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print("REHOST TRANSFER COMPLETE", name, json.dumps(report, default=str), flush=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = args or list(JOBS)
    assert BASE.exists()
    for name in names:
        source, target = JOBS[name]
        rehost(name, source, target)


if __name__ == "__main__":
    main()
