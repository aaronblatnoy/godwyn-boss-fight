"""Fade smoothing at belt and constrain penetrating hem through existing leg/hip weights."""
import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'));import astra_v3m_retarget_world as w
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);allowed=['Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase'];names={g.index:g.name for g in body.vertex_groups}
def weights(ob):
 A=np.zeros((len(ob.data.vertices),len(allowed)));ns={g.index:g.name for g in ob.vertex_groups}
 for v in ob.data.vertices:
  for g in v.groups:
   if ns[g.group] in allowed:A[v.index,allowed.index(ns[g.group])]=g.weight
 return A
W=weights(body);before=W.copy()
with bpy.data.libraries.load(str(O/'first_cloth.blend'),link=False) as (a,d):d.objects=['V4_Body']
orig=d.objects[0];old=weights(orig);bpy.data.objects.remove(orig,do_unlink=True);t=np.clip((1.55-pts[:,2])/.45,0,1);t=t*t*(3-2*t);W=old*(1-t[:,None])+W*t[:,None]
# Hem vertices are identified by actual floor violation under current skinned motion.
ids=np.where((pts[:,2]<.25)&(W.sum(1)>.999))[0];P=np.column_stack((pts[ids],np.ones(len(ids))));transforms=[]
for clip in ['Combat_Stance','sword_slash_r']:
 for frame in range(1,int(bpy.data.actions[clip].frame_range[1])+1):
  w.assign(rig,bpy.data.actions[clip],frame);transforms.append(np.array([(rig.matrix_world@rig.pose.bones[n].matrix@rig.data.bones[n].matrix_local.inverted()@rig.matrix_world.inverted())[2][:] for n in allowed]))
Z=np.einsum('fbc,vc->fvb',np.array(transforms),P);height=np.einsum('fvb,vb->fv',Z,W[ids]);bad=height.min(0)<-.014;ids=ids[bad];Z=Z[:,bad,:];V=W[ids].copy();initial=V.copy();total=V.sum(1);V/=total[:,None];worst=[]
# Cyclic halfspace projections on the probability simplex. No animated vertex edits.
for iteration in range(100):
 for z in Z:
  h=(z*V).sum(1);violation=np.maximum(0,-.014-h);direction=z-z.mean(1)[:,None];norm=(direction*direction).sum(1);V+=direction*(violation/np.maximum(norm,1e-12))[:,None];V=np.maximum(V,0);V/=V.sum(1)[:,None]
 low=float(np.einsum('fvb,vb->fv',Z,V).min());worst.append(low)
 if low>=-.0141:break
W[ids]=V*total[:,None];changed=np.where(abs(W-before).max(1)>1e-8)[0]
for j,n in enumerate(allowed):
 group=body.vertex_groups[n]
 for idx in changed:
  if W[idx,j]>1e-8:group.add([int(idx)],float(W[idx,j]),'REPLACE')
  else:group.remove([int(idx)])
rep={'belt_fade_z_m':[1.10,1.55],'hem_vertices_corrected':len(ids),'hem_constraint_m':-.014,'hem_predicted_min_m':worst[-1],'iterations':len(worst),'max_weight_change':float(abs(W-before).max()),'changed_vertices':len(changed),'only_existing_leg_hip_weights':True,'geometry_unchanged':True};(O/'cloth_finish.json').write_text(json.dumps(rep,indent=2));w.assign(rig,bpy.data.actions['Combat_Stance'],1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate.blend'));print('V4P_CLOTH_FINISH',json.dumps(rep),flush=True)
