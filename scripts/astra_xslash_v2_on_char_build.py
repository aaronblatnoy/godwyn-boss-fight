"""Copy the approved saved v2 action onto the upgraded character, unchanged.
Preserve new skin/geometry/materials and native rigid sword binding. Re-sample
only the existing temporal blur geometry to match the new blade, not motion.
Run: blender --background --gpu-backend metal --python-exit-code 1 --python THIS
"""
import bpy, sys, json, math, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'renders/astra/v2_on_char'
SOURCE = ROOT/'models/astra_character_v2.blend'

def action_digest(action):
    h = hashlib.sha256(); curves = keys = 0
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    curves += 1
                    h.update(repr((fc.data_path, fc.array_index, fc.extrapolation)).encode())
                    for k in fc.keyframe_points:
                        keys += 1
                        h.update(repr((tuple(k.co), tuple(k.handle_left), tuple(k.handle_right), k.interpolation, k.handle_left_type, k.handle_right_type)).encode())
    return {'sha256': h.hexdigest(), 'fcurves': curves, 'keys': keys}

def sword_landmarks(sw):
    """Read character-track source-coordinate attribute, without editing it."""
    import numpy as np
    attr = sw.data.attributes['astra_sword_source']
    source = np.array([p.vector[:] for p in attr.data])
    local = np.array([v.co[:] for v in sw.data.vertices])
    fit = np.linalg.lstsq(np.column_stack((source, np.ones(len(source)))), local, rcond=None)[0]
    residual = float(np.max(np.abs(np.column_stack((source, np.ones(len(source))))@fit-local)))
    assert residual < .001, residual
    tip_index = int(source[:, 2].argmin())
    grip = Vector(np.array([61.2, -66.3, 167.0, 1.0])@fit)
    return sw.data.vertices[tip_index].co.copy(), grip, tip_index

def sword_points(rig, sw, tip, grip):
    # Exact rigid ARMATURE deformation: all sword vertices weight RightHand 1.0.
    deform = rig.matrix_world @ rig.pose.bones['RightHand'].matrix @ rig.data.bones['RightHand'].matrix_local.inverted() @ rig.matrix_world.inverted() @ sw.matrix_world
    return deform@tip, deform@grip

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Snapshot the input to /tmp so a concurrent character save cannot change this run.
    data = SOURCE.read_bytes(); source_hash = hashlib.sha256(data).hexdigest()
    snapshot = Path('/tmp/astra_xslash_v2_character_input.blend'); snapshot.write_bytes(data)
    del data
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_v2_wip.blend'))
    scene = bpy.context.scene; old = bpy.data.objects['Armature']
    source_action = old.animation_data.action
    digest = action_digest(source_action)
    names = ['Armature', 'char1', 'Godwyn_Sword', 'Astra_Undersleeves']
    with bpy.data.libraries.load(str(snapshot), link=False) as (src, dst):
        assert set(names).issubset(src.objects)
        dst.objects = names[:]
    loaded = dict(zip(names, dst.objects))
    for obj in loaded.values(): scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    rig = loaded['Armature']; body = loaded['char1']; sw = loaded['Godwyn_Sword']
    assert set(old.pose.bones.keys()) == set(rig.pose.bones.keys())
    rest_error = max(abs(old.data.bones[n].matrix_local[i][j]-rig.data.bones[n].matrix_local[i][j]) for n in old.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0
    for bone in old.data.bones:
        other = rig.data.bones[bone.name]
        assert (bone.parent.name if bone.parent else None) == (other.parent.name if other.parent else None)
    assert max(abs(old.matrix_world[i][j]-rig.matrix_world[i][j]) for i in range(4) for j in range(4)) == 0
    for obj in loaded.values():
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE': assert mod.object == rig
    assert sw.parent == rig and sw.parent_type == 'OBJECT'
    assert list(sw.vertex_groups.keys()) == ['RightHand']
    assert all(len(v.groups) == 1 and abs(v.groups[0].weight-1) < 1e-7 for v in sw.data.vertices)
    for p in old.pose.bones:
        other = rig.pose.bones[p.name]
        assert not other.constraints
        other.rotation_mode = p.rotation_mode
        other.scale = p.scale
    rig.animation_data_clear(); rig.animation_data_create()
    rig.animation_data.action = source_action.copy()
    rig.animation_data.action.name = 'Astra_Godwyn_XSlash_V2_On_Character'
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    assert action_digest(rig.animation_data.action) == digest
    # Verify all bones at every quarter-frame before deleting old scene objects.
    mesh_states = [(o, o.hide_viewport) for o in scene.objects if o.type == 'MESH']
    for o, _ in mesh_states: o.hide_viewport = True
    max_error = 0.0; secondary_motion = {p.name: 0.0 for p in rig.pose.bones if p.name.startswith('phys_')}
    for q in range(4, 361):
        frame = q/4; scene.frame_set(int(frame), subframe=frame%1); bpy.context.view_layer.update()
        for p in old.pose.bones:
            other = rig.pose.bones[p.name]
            max_error = max(max_error, max(abs(p.matrix[i][j]-other.matrix[i][j]) for i in range(4) for j in range(4)))
            if p.name in secondary_motion:
                secondary_motion[p.name] = max(secondary_motion[p.name], math.degrees(other.rotation_quaternion.angle))
    assert max_error < 1e-6, max_error
    for o, hidden in mesh_states: o.hide_viewport = hidden
    for name in ['Godwyn_Sword', 'char1', 'Armature']:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for name, obj in loaded.items(): obj.name = name
    tip, grip, tip_index = sword_landmarks(sw)
    # Retain the approved ribbon material, alpha ramp, shutter and visibility keys.
    # Only replace ribbon vertex coordinates, since the new blade bind/length differs.
    ribbon_count = 0
    for obj in scene.objects:
        if not obj.name.startswith('Astra_v2_blur_'): continue
        f = int(obj.name.rsplit('_', 1)[1]); ribbon_count += 1
        for j in range(13):
            t = f-.70+.70*j/12; scene.frame_set(int(t), subframe=t%1); bpy.context.view_layer.update()
            point, handle = sword_points(rig, sw, tip, grip)
            for k, radial in enumerate([.30, .88, 1.0]): obj.data.vertices[j*3+k].co = handle.lerp(point, radial)
        obj.data.update()
    # Check the analytic rigid sword evaluator against Blender's evaluated mesh.
    sword_error = 0.0
    for f in [1, 30, 40, 41, 57, 60, 90]:
        scene.frame_set(f); bpy.context.view_layer.update()
        point, _ = sword_points(rig, sw, tip, grip)
        evaluated = sw.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = evaluated.to_mesh()
        sword_error = max(sword_error, (evaluated.matrix_world@mesh.vertices[tip_index].co-point).length)
        evaluated.to_mesh_clear()
    assert sword_error < 1e-5, sword_error
    scene.frame_set(1); scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.preferences.filepaths.save_version = 0
    target = ROOT/'models/astra_xslash_v2_on_char_wip.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    report = {'character_source': str(SOURCE.relative_to(ROOT)), 'character_source_sha256_at_load': source_hash,
        'character_snapshot': str(snapshot), 'action_source': 'models/astra_xslash_v2_wip.blend',
        'source_action': source_action.name, 'action_data_identical': True, 'action_digest': digest,
        'bone_count': len(rig.pose.bones), 'rest_matrix_max_error': rest_error,
        'all_bones_357_subframes_max_matrix_error': max_error,
        'secondary_bones': len(secondary_motion), 'secondary_peak_degrees': secondary_motion,
        'retargeting': False, 'weight_material_geometry_edits': False,
        'native_sword_attachment': 'ARMATURE modifier; RightHand weight 1.0; unchanged',
        'sword_evaluator_max_error_m': sword_error, 'ribbons_resampled': ribbon_count,
        'sword_blade_length_m': (tip-grip).length*.01,
        'image_packing': [{'name': im.name, 'packed': bool(im.packed_file), 'size': list(im.size)} for im in bpy.data.images if im.users],
        'comparison_staging': 'Original v2 scene, lights, world, AgX look, exposure -0.7 and shutter 0.55 retained'}
    (OUT/'transfer_verification.json').write_text(json.dumps(report, indent=2))
    print('ASTRA_TRANSFER_COMPLETE', json.dumps({k:v for k,v in report.items() if k not in ['secondary_peak_degrees', 'image_packing']}), flush=True)

if __name__ == '__main__': main()
