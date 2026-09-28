"""Blend root attachments by strand arc length to remove single-segment pin jumps."""
import bpy,sys,json,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_r5_groom_geometry import weights,bind,smooth
from astra_char2_mpfb_validate import hair_check
from astra_char2_mpfb_clay import render_views
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_eyefit_i01.blend'));reset_pose()
for cu in bpy.context.scene.objects:
 if cu.type!='CURVES' or not cu.name.startswith('AstraChar2_R5_Curves_MPFB_') or cu.name.endswith('ScalpBed'):continue
 suffix=cu.name.removeprefix('AstraChar2_R5_Curves_');n=cu['groom_strands'];k=cu['groom_points_per_strand'];p=np.empty(n*k*3,np.float32);cu.data.position_data.foreach_get('vector',p);p=p.reshape(n,k,3)
 w,names=weights(p.reshape(-1,3),cu['chain']);w=w.reshape(n,k,5)
 arc=np.concatenate([np.zeros((n,1)),np.cumsum(np.linalg.norm(np.diff(p,axis=1),axis=2),axis=1)],axis=1)
 pin=1-smooth((arc-.025)/.10);w*=1-pin[:,:,None];w[:,:,0]+=pin
 idx=np.unique(np.r_[np.arange(0,k,2),k-1])
 for ob,ww in [(bpy.data.objects['AstraChar2_R5_Control_'+suffix],w.reshape(-1,5)),(bpy.data.objects['AstraChar2_R5_Strands_'+suffix],np.repeat(w[:,idx].reshape(-1,5),3,axis=0))]:
  ob.vertex_groups.clear()
  for m in list(ob.modifiers):
   if m.type=='ARMATURE':ob.modifiers.remove(m)
  bind(ob,ww,names)
reset_pose();r=hair_check(bpy.data.objects['Armature']);(O/'mpfb_root_blend_check.json').write_text(json.dumps(r,indent=2))
assert max(v['segment_stretch_max'] for v in r.values())<4
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_fit_i02.blend'))
render_views('mpfb_fit_i02_clay')
