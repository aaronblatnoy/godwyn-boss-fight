import bpy,sys,json,shutil,collections,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
for ext in ['blend','glb']:
 d=R/f'models/astra_character_v2_preround4.{ext}'
 if not d.exists():shutil.copy2(R/f'models/astra_character_v2.{ext}',d)
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround4.blend'))
c=bpy.data.hair_curves.new('R4 API probe');print('CURVES_API',[(p.identifier,p.description[:100]) for p in c.bl_rna.properties]);print('FUNCS',[f.identifier for f in c.bl_rna.functions]);c.add_curves([4,4]);print('ATTR',[(a.name,a.data_type,a.domain) for a in c.attributes]);print('POINTPROP',[p.identifier for p in c.points[0].bl_rna.properties]);print('CURVEPROP',[p.identifier for p in c.curves[0].bl_rna.properties])
mat=bpy.data.materials.new('R4 probe');mat.use_nodes=True;n=mat.node_tree.nodes.new('ShaderNodeBsdfHairPrincipled');print('HAIR_SHADER',[(s.name,str(s.default_value) if hasattr(s,'default_value') else '') for s in n.inputs]);print('HAIRPROPS',[(p.identifier,p.description[:100]) for p in n.bl_rna.properties if p.identifier in ['model','parametrization']])
o=bpy.data.objects['char1'];m=o.data;r={'regions':{},'hair_bones':[]}
for slot in [0,1,2,3,4]:
 ids={i for f in m.polygons if f.material_index==slot for i in f.vertices};pos=np.array([o.matrix_world@m.vertices[i].co for i in ids]);p=pos[pos[:,2]>2.75];r['regions'][slot]={'head_verts':len(p),'min':p.min(0).tolist() if len(p) else None,'max':p.max(0).tolist() if len(p) else None}
arm=bpy.data.objects['Armature']
for b in arm.data.bones:
 if b.name.startswith('phys_hair'):r['hair_bones'].append({'name':b.name,'head':list(arm.matrix_world@b.head_local),'tail':list(arm.matrix_world@b.tail_local),'connected':b.use_connect,'matrix':[list(row) for row in b.matrix_local]})
r['char_transform']=[list(row) for row in o.matrix_world];r['arm_transform']=[list(row) for row in arm.matrix_world]
(O/'r4_probe.json').write_text(json.dumps(r,indent=2));print('REPORT',json.dumps(r))
