"""Fit existing eye object slots to the MPFB eye helpers; never alter the head."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_r5_geometry import mesh,bind
from astra_char2_mpfb_clay import render_views
from astra_character_common import reset_pose

def cap(stem,side,center,radius,disc,offset,delta=0):
 ob=bpy.data.objects['AstraChar2_'+stem+'_'+side];mats=list(ob.data.materials);v=[(center[0],center[1]-math.sqrt(radius*radius-delta*delta)-offset,center[2])];f=[];N=64;K=12
 for j in range(1,K+1):
  rr=disc*j/K
  for i in range(N):
   a=math.tau*i/N;v.append((center[0]+rr*math.cos(a),center[1]-math.sqrt(radius*radius-rr*rr-2*rr*math.sin(a)*delta-delta*delta)-offset,center[2]+rr*math.sin(a)))
 for i in range(N):f.append((0,1+i,1+(i+1)%N))
 for j in range(K-1):
  for i in range(N):
   a=1+j*N+i;b=1+j*N+(i+1)%N;f.append((a,a+N,b+N,b))
 ob=mesh(ob.name,v,f,mats);ob.matrix_world.identity();bind(ob,lambda p:{'Head':1});ob.hide_render=False;ob.hide_set(False)
 uv=ob.data.uv_layers.new(name='UVMap')
 for poly in ob.data.polygons:
  for li in poly.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=((p.x-center[0])/(2*disc)+.5,(p.z-center[2])/(2*disc)+.5)
 return ob
def main():
 bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_textured_i02.blend'));reset_pose();info=json.loads((O/'mpfb_graft_i04.json').read_text())['eyes']
 for side in ['L','R']:
  c=info[side]['center'];r=info[side]['radius'];cc=[c[0],c[1],c[2]-.004]
  cap('Iris',side,cc,r,.0103,.00012,-.004);cap('Pupil',side,cc,r,.0035,.00020,-.004);cap('Cornea',side,cc,r,.0112,.00030,-.004)
  bpy.data.objects['AstraChar2_Cornea_'+side].hide_render=True
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_eyefit_i02.blend'))
 render_views('mpfb_eyefit_i02_clay')
if __name__=='__main__':main()
