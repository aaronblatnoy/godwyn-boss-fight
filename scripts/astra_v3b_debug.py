import bpy,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
bpy.ops.wm.open_mainfile(filepath=str(R/'renders/astra/v3b/candidate_r6.blend'))
for name,col in [('char1',(.2,.2,.2,1)),('AstraChar2_Meshy_NeckBlend',(0,1,0,1)),('AstraChar2_V3B_CollarLiner',(0,0,1,1)),('AstraChar2_Meshy_HeadHair',(1,.05,.05,1))]:
 ob=bpy.data.objects[name];mat=bpy.data.materials.new('debug '+name);mat.diffuse_color=col;mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=col;bs.inputs['Roughness'].default_value=.7;ob.data.materials.clear();ob.data.materials.append(mat)
 for f in ob.data.polygons:f.material_index=0
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'renders/astra/v3b/debug.blend'))
