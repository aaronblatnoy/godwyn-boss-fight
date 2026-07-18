"""p3_phase3_probe.py - Probe current .blend state for Phase 3 re-rig."""
import bpy, sys

print('[probe] === Phase 3 Pre-Rig Probe ===')
objs = [(o.name, o.type) for o in bpy.data.objects]
print('[probe] Objects in scene:')
for n, t in sorted(objs):
    print(f'  {t:12s} {n}')

arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if arms:
    arm = arms[0]
    print(f'[probe] Armature: {arm.name}, {len(arm.data.bones)} bones')
    bone_names = sorted(b.name for b in arm.data.bones)
    print('[probe] Bones:', bone_names)
else:
    print('[probe] No armature found')

body = bpy.data.objects.get('Godwyn_Body')
if body:
    print(f'[probe] Godwyn_Body verts: {len(body.data.vertices)}')
    if body.data.shape_keys:
        sk_names = [k.name for k in body.data.shape_keys.key_blocks]
        print(f'[probe] Shape keys ({len(sk_names)}): {sk_names}')
    else:
        print('[probe] Godwyn_Body has NO shape keys')
    print(f'[probe] Godwyn_Body parent: {body.parent}')
    print(f'[probe] Godwyn_Body modifiers: {[(m.name, m.type) for m in body.modifiers]}')
    print(f'[probe] Godwyn_Body vertex_groups: {[g.name for g in body.vertex_groups[:10]]} ...')
else:
    print('[probe] Godwyn_Body MISSING')

for name in ('Godwyn_Armor', 'Godwyn_Tabard', 'Godwyn_Hair', 'Godwyn_Sword', 'Godwyn_Eyes'):
    obj = bpy.data.objects.get(name)
    if obj:
        mods = [(m.name, m.type) for m in obj.modifiers]
        vg_count = len(obj.vertex_groups)
        parent = obj.parent.name if obj.parent else 'None'
        pbone = obj.parent_bone if obj.parent_type == 'BONE' else '-'
        print(f'[probe] {name}: parent={parent}, pbone={pbone}, mods={mods}, vg_count={vg_count}')
    else:
        print(f'[probe] {name}: MISSING')

print('[probe] === Done ===')
