"""Finish legacy eye inserts and eyebrow fit without altering accepted head geometry."""
import bpy,sys,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_clay import render_views
from astra_char2_skin import png,srgb
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_eyefit_i02.blend'));reset_pose()
h=bpy.data.objects['AstraChar2_Mpfb_Head'];tree=BVHTree.FromObject(h,bpy.context.evaluated_depsgraph_get())
for side in ['L','R']:
 for stem in ['Wetline','Lashes','TearCorner']:
  ob=bpy.data.objects['AstraChar2_'+stem+'_'+side];ob.hide_render=True;ob.hide_set(True)
 ob=bpy.data.objects['AstraChar2_Eyebrows_'+side];p=np.array([ob.matrix_world@v.co for v in ob.data.vertices]);c=(p.min(0)+p.max(0))/2;inv=ob.matrix_world.inverted()
 for v in ob.data.vertices:
  q=ob.matrix_world@v.co;q.x=c[0]+(q.x-c[0])*1.4;q.z=c[2]+(q.z-c[2])*1.65
  hit,n,_,_=tree.ray_cast(Vector((q.x,-1,q.z)),Vector((0,1,0)),2)
  if hit:q=hit+n*.0007
  v.co=inv@q
 for mat in ob.data.materials:
  for node in mat.node_tree.nodes:
   if node.type=='BSDF_PRINCIPLED':node.inputs['Base Color'].default_value=(.14,.085,.03,1)
 for mat in bpy.data.objects['AstraChar2_Eyeball_'+side].data.materials:
  for node in mat.node_tree.nodes:
   if node.type=='BSDF_PRINCIPLED':node.inputs['Base Color'].default_value=(.33,.32,.30,1)
N=1024;u=(np.arange(N)+.5)/N;x,y=np.meshgrid(u*2-1,u*2-1);r=np.sqrt(x*x+y*y);a=np.arctan2(y,x)
fiber=.40*np.sin(a*121+np.sin(r*37)*2)+.20*np.sin(a*317+r*45)+.15*np.sin(a*61-r*16)
col=np.ones((N,N,3))*np.array([.12,.145,.060]);col*=1+fiber[:,:,None]*.45
inner=np.exp(-((r-.4)/.19)**2);col=col*(1-inner[:,:,None]*.35)+np.array([.22,.13,.038])*inner[:,:,None]*.35
limb=np.clip((r-.86)/.13,0,1);col*=1-limb[:,:,None]*.75
p=O/'mpfb_iris_radial.png';png(p,srgb(col));im=bpy.data.images.load(str(p),check_existing=False);im.name='MPFB hazel iris radial detail';im.pack()
for side in ['L','R']:
 for mat in bpy.data.objects['AstraChar2_Iris_'+side].data.materials:
  ns=mat.node_tree.nodes;ls=mat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');tx=ns.new('ShaderNodeTexImage');tx.image=im;ls.new(tx.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Coat Weight'].default_value=.5;bs.inputs['Coat Roughness'].default_value=.09
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_surface_finish_i03.blend'))
render_views('mpfb_surface_finish_i03_clay')
