"""Read-only inventory for the approved MPFB surface source."""
import bpy
import json
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / 'models/astra_character_v2_mpfb_surface_finish_i03.blend'

bpy.ops.wm.open_mainfile(filepath=str(SRC))
out = {
    'objects': {},
    'materials': {},
    'scene': {
        'engine': bpy.context.scene.render.engine,
        'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None,
    },
}
for ob in bpy.data.objects:
    if ob.name.startswith('AstraChar2') or ob.name in {'Armature', 'char1', 'Godwyn_Sword'}:
        item = {
            'type': ob.type,
            'hidden_render': bool(ob.hide_render),
            'parent': ob.parent.name if ob.parent else None,
            'modifiers': [(m.name, m.type, getattr(m, 'object', None).name if getattr(m, 'object', None) else None) for m in ob.modifiers],
            'materials': [m.name if m else None for m in getattr(ob.data, 'materials', [])],
        }
        if ob.type == 'MESH':
            item.update(vertices=len(ob.data.vertices), edges=len(ob.data.edges), polygons=len(ob.data.polygons))
            coords = [v.co[:] for v in ob.data.vertices]
            if coords:
                item['bounds_local'] = [[min(v[i] for v in coords) for i in range(3)], [max(v[i] for v in coords) for i in range(3)]]
        elif ob.type == 'CURVES':
            item.update(curves=len(ob.data.curves), points=len(ob.data.points))
        out['objects'][ob.name] = item
for mat in bpy.data.materials:
    if mat.use_nodes:
        nodes = []
        for n in mat.node_tree.nodes:
            if n.type in {'BSDF_PRINCIPLED', 'BSDF_HAIR_PRINCIPLED', 'TEX_IMAGE'}:
                vals = {}
                for key in ('Base Color', 'Roughness', 'Metallic', 'Subsurface Weight', 'Subsurface Radius', 'Coat Weight', 'Coat Roughness'):
                    if key in n.inputs and not n.inputs[key].is_linked:
                        val = n.inputs[key].default_value
                        try: val = list(val)
                        except TypeError: val = float(val)
                        vals[key] = val
                nodes.append({'name': n.name, 'type': n.type, 'values': vals, 'image': n.image.name if n.type == 'TEX_IMAGE' and n.image else None})
        if nodes:
            out['materials'][mat.name] = nodes
print('LIKENESS_INSPECT_JSON_BEGIN')
print(json.dumps(out, indent=2))
print('LIKENESS_INSPECT_JSON_END')
