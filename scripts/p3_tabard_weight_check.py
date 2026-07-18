"""p3_tabard_weight_check.py - Deep check of tabard vertex weights."""
import bpy, sys

tabard = bpy.data.objects.get('Godwyn_Tabard')
if not tabard:
    print('[check] Godwyn_Tabard MISSING')
    sys.exit(1)

total_verts = len(tabard.data.vertices)
print(f'[check] Total verts: {total_verts}')

# Sample first 10 verts
print('[check] First 10 verts and their groups:')
for i, v in enumerate(tabard.data.vertices[:10]):
    groups = [(tabard.vertex_groups[ge.group].name, ge.weight) for ge in v.groups]
    print(f'  v{i}: {groups}')

# Count verts with any non-zero weight
weighted = sum(1 for v in tabard.data.vertices if any(ge.weight > 0.0 for ge in v.groups))
unweighted = sum(1 for v in tabard.data.vertices if not v.groups or all(ge.weight == 0.0 for ge in v.groups))
print(f'[check] Verts with any weight > 0: {weighted}')
print(f'[check] Verts with all weights = 0 or no groups: {unweighted}')

# Check if tabard is bound to armature via the armature modifier
arm = None
for m in tabard.modifiers:
    if m.type == 'ARMATURE':
        arm = m.object
        print(f'[check] Armature modifier object: {arm.name if arm else None}')
        break

# Check the body vertex groups for comparison
body = bpy.data.objects.get('Godwyn_Body')
if body:
    body_weighted = sum(1 for v in body.data.vertices if any(ge.weight > 0.01 for ge in v.groups))
    print(f'[check] Godwyn_Body verts with weight>0.01: {body_weighted} / {len(body.data.vertices)}')
