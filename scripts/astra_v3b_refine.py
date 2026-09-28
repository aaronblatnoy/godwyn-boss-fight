import bpy,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3b_materials as mat
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(R/sys.argv[sys.argv.index('--blend')+1] if '--blend' in sys.argv else O/'candidate_r2.blend'))
rep=json.loads((O/'build_r2.json').read_text());skin,skin_report=mat.flat_neck(bpy.data.objects['AstraChar2_Meshy_HeadHair'])
for name in ['AstraChar2_Meshy_NeckBlend','AstraChar2_V3B_CollarLiner']:
 ob=bpy.data.objects[name];ob.data.materials.clear();ob.data.materials.append(skin)
liner=bpy.data.objects['AstraChar2_V3B_CollarLiner'];top=rep['measurement']['rim_top_m']-.012;outer=rep['liner']['wall_contact_z']
for j in range(5):
 t=j/4;z=top+(outer-top)*(t*t*(3-2*t))
 for k in range(72):liner.data.vertices[j*72+k].co.z=z
liner.data.update();rep['liner']['neck_cut_ring_z']=top;rep['skin_material']=skin_report;rep['revision']='r3: recessed collar loft and explicit sRGB-to-linear sampling';(O/'liner_refine.json').write_text(json.dumps(rep,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else O/'candidate_r3.blend'));print('V3B_REFINE',json.dumps({'liner':rep['liner'],'skin':skin_report}),flush=True)
