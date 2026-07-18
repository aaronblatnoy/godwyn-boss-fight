"""p3_tabard_probe.py - Probe the tabard vertex group distribution."""
import bpy, sys
from collections import defaultdict

tabard = bpy.data.objects.get('Godwyn_Tabard')
if not tabard:
    print('[tabard] Godwyn_Tabard MISSING')
    sys.exit(1)

print(f'[tabard] Godwyn_Tabard: {len(tabard.data.vertices)} verts, {len(tabard.vertex_groups)} groups')
print('[tabard] Vertex groups:', [g.name for g in tabard.vertex_groups])

# Count weights per bone
bone_vert_counts = defaultdict(int)
for v in tabard.data.vertices:
    for ge in v.groups:
        gname = tabard.vertex_groups[ge.group].name
        if ge.weight > 0.01:
            bone_vert_counts[gname] += 1

print('[tabard] Verts per bone (weight > 0.01):')
for bone, count in sorted(bone_vert_counts.items(), key=lambda x: -x[1]):
    print(f'  {bone}: {count}')

# Check tabard material
print('[tabard] Materials:', [m.name for m in tabard.data.materials])
print('[tabard] Modifier:', [(m.name, m.type, m.object.name if hasattr(m,'object') and m.object else '?') for m in tabard.modifiers])
