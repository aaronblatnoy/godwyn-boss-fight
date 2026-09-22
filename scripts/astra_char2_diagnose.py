import bpy,sys,collections,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_render import render
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_char2_work.blend'))
o=bpy.data.objects['char1'];print('ATTRS',[(a.name,a.domain,a.data_type) for a in o.data.attributes]);print('CUSTOM',o.data.has_custom_normals)
for m in o.modifiers:print('MOD',m.name,[(p.identifier,getattr(m,p.identifier)) for p in m.bl_rna.properties if p.type in ['FLOAT','STRING','BOOLEAN','INT']])
print('SMOOTH',collections.Counter((f.material_index,f.use_smooth) for f in o.data.polygons))
# Recompute geometry normals, completely removing baked split directions for this diagnostic.
if 'custom_normal' in o.data.attributes:o.data.attributes.remove(o.data.attributes['custom_normal'])
if 'sharp_edge' in o.data.attributes:o.data.attributes.remove(o.data.attributes['sharp_edge'])
m=o.data.materials[2];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for l in list(bs.inputs['Normal'].links):m.node_tree.links.remove(l)
render('normal_diagnostic',['face'])
