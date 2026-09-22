"""Apply the existing layered skin machinery to MPFB face UVs after the clay gate."""
import bpy,sys,json,inspect,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
import astra_char2_skin as skin
from astra_char2_mpfb_clay import render_views
from astra_character_common import reset_pose

def main(src):
 bpy.ops.wm.open_mainfile(filepath=str(R/src));reset_pose();h=bpy.data.objects['AstraChar2_Mpfb_Head']
 uv=h.data.uv_layers.get(skin.UV) or h.data.uv_layers.new(name=skin.UV)
 for f in h.data.polygons:
  for li in f.loop_indices:
   p=h.data.vertices[h.data.loops[li].vertex_index].co
   z=float(np.interp(p.z,[2.76,2.787,2.82,2.858,2.904,2.976,3.001,3.16],[2.76,2.785,2.815,2.849,2.889,2.953,2.980,3.16]))
   uv.data[li].uv=((p.x*.92+.16)/.32,(z-2.76)/.40) if p.y<-.27 else (.95+p.x*.1,.70+(p.z-3)*.05)
 h.data.uv_layers.active=uv
 # Reuse deterministic reference microstructure, maps, normal and SSS nodes.
 # Redirect all generated assets to this campaign's prefix; do not overwrite prior maps.
 code=inspect.getsource(skin.maps).replace("f'skin_{k}_1536.png'","f'mpfb_skin_{k}_1536.png'")
 code=code.replace("[.34,.185,.112]","[.47,.305,.215]").replace("[.38,.145,.098]","[.48,.245,.18]").replace("[.17,.072,.045]","[.31,.17,.115]").replace("[.32,.115,.085]","[.44,.26,.205]")
 code=code.replace(".031,.017)*.50",".031,.017)*.24").replace("ref[:,:,None]*1.4","ref[:,:,None]*.8").replace("broad[:,:,None]*.24","broad[:,:,None]*.10")
 code=code.replace('crease[:,:,None]*.55','crease[:,:,None]*.12')
 code=code.replace("glow=.014+.050","glow=.003+.008").replace("+.020*np.clip","+.004*np.clip")
 exec(compile(code,'<mpfb existing skin map adapter>','exec'),skin.__dict__)
 m=skin.apply_skin();m['mpfb_surface']='Pale restrained warm skin, original packed-map/SSS machinery; MPFB landmark-warped UV projection.'
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Subsurface Weight'].default_value=.20
 # Correct the legacy dark sclera. Refit iris caps have their own clearcoat,
 # avoiding the magnifying/offset legacy cornea insert (retained hidden).
 for side in ['L','R']:
  ob=bpy.data.objects['AstraChar2_Eyeball_'+side]
  for mat in ob.data.materials:
   for node in mat.node_tree.nodes:
    if node.type=='BSDF_PRINCIPLED':
     node.inputs['Base Color'].default_value=(.52,.50,.45,1);node.inputs['Roughness'].default_value=.26
  ob=bpy.data.objects['AstraChar2_Iris_'+side]
  for mat in ob.data.materials:
   for node in mat.node_tree.nodes:
    if node.type=='BSDF_PRINCIPLED':
     node.inputs['Coat Weight'].default_value=.8;node.inputs['Coat Roughness'].default_value=.07
 # Existing brows are retained meshes. Fine, muted golden brows fit the approved hair.
 for side in ['L','R']:
  ob=bpy.data.objects['AstraChar2_Eyebrows_'+side]
  for mat in ob.data.materials:
   if not mat or not mat.use_nodes:continue
   for node in mat.node_tree.nodes:
    if node.type=='BSDF_PRINCIPLED':node.inputs['Base Color'].default_value=(.18,.105,.036,1);node.inputs['Roughness'].default_value=.66
 for mat in bpy.data.materials:
  if not mat.name.startswith(('AstraChar2 R4 Native blonde','AstraChar2 R4 Portable blonde')):continue
  for node in mat.node_tree.nodes:
   if node.type=='BSDF_HAIR_PRINCIPLED':
    node.inputs['Melanin'].default_value=.32;node.inputs['Random Color'].default_value=.30;node.inputs['Roughness'].default_value=.45
   elif node.type=='BSDF_PRINCIPLED':
    node.inputs['Base Color'].default_value=(.40,.24,.085,1);node.inputs['Roughness'].default_value=.46
 bpy.context.scene.view_layers[0].material_override=None;bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_textured_i02.blend'))
 render_views('mpfb_textured_i02',clay=False,samples=64,width=850)
if __name__=='__main__':main(sys.argv[sys.argv.index('--')+1])
