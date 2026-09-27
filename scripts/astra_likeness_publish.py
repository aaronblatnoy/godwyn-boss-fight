"""Publish i05 only after native, hero, export, and round-trip gates pass."""
import bpy
import sys
import json
import hashlib
import shutil
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
ORIGINAL_BLEND = 'c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386'
ORIGINAL_GLB = '74674393fbc8447b084d62f4ed89f6c44b6b145a720f840926e10ac225fe8775'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(source, glb):
    native = json.loads((OUT / 'likeness_final_validation.json').read_text())
    roundtrip = json.loads((OUT / 'likeness_roundtrip_validation.json').read_text())
    hero = json.loads((OUT / 'likeness_final_hero_assembly.json').read_text())
    assert native['source'] == source and native['bones'] == 121 and native['actions'] == 0
    assert native['rest_matrix_error'] == 0 and native['neutral_restored']
    assert native['weights']['unweighted_or_bad_sum_vertices'] == 0
    assert native['banked_armor_hashes_preserved']
    assert roundtrip['source'] == glb and roundtrip['bones'] == 121 and roundtrip['actions'] == 0
    assert roundtrip['neutral_restored'] and roundtrip['weights']['unweighted_or_bad_sum_vertices'] == 0
    assert roundtrip['bone_names_and_hierarchy_preserved'] and not roundtrip['glb_animations']
    assert hero['rest_transform_max_error'] == 0 and hero['character_path'] == str(ROOT / source)
    canonical_blend = ROOT / 'models/astra_character_v2.blend'
    canonical_glb = ROOT / 'models/astra_character_v2.glb'
    backup_blend = ROOT / 'models/astra_character_v2_pre_likeness.blend'
    backup_glb = ROOT / 'models/astra_character_v2_pre_likeness.glb'
    assert digest(backup_blend) == ORIGINAL_BLEND and digest(backup_glb) == ORIGINAL_GLB
    assert digest(canonical_blend) == ORIGINAL_BLEND and digest(canonical_glb) == ORIGINAL_GLB
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / source))
    arm = bpy.data.objects['Armature']
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(canonical_blend))
    shutil.copyfile(glb, canonical_glb)
    result = {
        'astra_character_v2.blend': digest(canonical_blend),
        'astra_character_v2.glb': digest(canonical_glb),
        'validated_candidate': source,
        'validated_roundtrip_glb': glb,
        'pre_likeness_blend_sha256': digest(backup_blend),
        'pre_likeness_glb_sha256': digest(backup_glb),
    }
    (OUT / 'likeness_published.json').write_text(json.dumps(result, indent=2) + '\n')
    print('LIKENESS_PUBLISHED', result, flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    main(args[0], args[1])
