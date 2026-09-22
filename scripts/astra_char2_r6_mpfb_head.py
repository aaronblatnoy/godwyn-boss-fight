"""Human-sculpted MPFB topology and local morph targets on the unchanged Godwyn rig.
Directly reads the installed CC0 OBJ/targets. No addon registration, network or installs.
"""
import sys,bpy,bmesh,gzip,json,numpy as np,math
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';A=Path.home()/'Library/Application Support/Blender/5.2/extensions/user_default/mpfb';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_geometry import mesh,bind,head_weights
ITER=2
MORPHS={
 'macrodetails/caucasian-male-young':1.,
 'macrodetails/universal-male-young-averagemuscle-averageweight':1.,
 'head/head-fat-decr':.12,'head/head-rectangular':.08,'head/head-scale-horiz-decr':.12,
 'forehead/forehead-temple-decr':.10,'eyebrows/eyebrows-trans-forward':.20,
 'chin/chin-bones-incr':.20,'chin/chin-prominent-incr':.10,'chin/chin-width-decr':.18,
 'nose/nose-scale-depth-decr':.08,'nose/nose-width2-decr':.08,
 'mouth/mouth-upperlip-volume-incr':.10,'mouth/mouth-lowerlip-volume-incr':.06,
}
for side in ['l','r']:
 MORPHS[f'cheek/{side}-cheek-bones-incr']=.25;MORPHS[f'cheek/{side}-cheek-volume-decr']=.10
 MORPHS[f'eyes/{side}-eye-push1-in']=.15;MORPHS[f'eyes/{side}-eye-push2-in']=.08;MORPHS[f'eyes/{side}-eye-height1-decr']=.05;MORPHS[f'eyes/{side}-eye-scale-incr']=.28
for side in ['left','right']:MORPHS[f'expression/units/caucasian/eyebrows-{side}-inner-up']=.06
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_collar_banked.blend'));reset_pose();arm=bpy.data.objects['Armature'];char=bpy.data.objects['char1'];slots=list(char.data.materials);rest={b.name:np.array(b.matrix_local) for b in arm.data.bones};original={o.name:[m.name for m in o.data.materials] for o in bpy.data.objects if hasattr(o.data,'materials')}
verts=[];uvs=[];faces=[];group='';groups={}
for line in (A/'data/3dobjs/base.obj').open():
 s=line.split()
 if not s:continue
 if s[0]=='v':verts.append([float(x) for x in s[1:4]])
 elif s[0]=='vt':uvs.append([float(x) for x in s[1:3]])
 elif s[0]=='g':group=s[1]
 elif s[0]=='f':
  ids=[int(x.split('/')[0])-1 for x in s[1:]];uv=[int(x.split('/')[1])-1 for x in s[1:]];faces.append((group,ids,uv));groups.setdefault(group,set()).update(ids)
v=np.array(verts,dtype=float)
for name,weight in MORPHS.items():
 for line in gzip.open(A/'data/targets'/(name+'.target.gz'),'rt'):
  s=line.split()
  if len(s)==4 and not s[0].startswith('#'):v[int(s[0])]+=weight*np.array(list(map(float,s[1:])))
eye_native=(v[list(groups['joint-l-eye'])].mean(0)+v[list(groups['joint-r-eye'])].mean(0))/2
# Physical scale, with the eye line and skull depth located on the existing rig.
scale=np.array([.18,.18,.18]);world=np.empty_like(v);world[:,0]=v[:,0]*scale[0];world[:,1]=-.345-(v[:,2]-eye_native[2])*scale[2];world[:,2]=2.974+(v[:,1]-eye_native[1])*scale[1]
# Fit only the basal graft inside the existing gorget, leaving facial anatomy intact.
for p in world:
 if p[2]<2.79:
  t=np.clip((2.79-p[2])/.045,0,1);rad=math.sqrt((p[0]/.084)**2+((p[1]+.196)/.098)**2);factor=1/max(rad,1)
  p[0]*=1-t+t*factor;p[1]=-.196+(p[1]+.196)*(1-t+t*factor)
selected=[(ids,uv) for g,ids,uv in faces if g=='body' and max(world[i,2] for i in ids)>2.685];ids=sorted({i for f,u in selected for i in f});lookup={old:i for i,old in enumerate(ids)}
head=mesh('AstraChar2_R6_MPFB_Head',world[ids].tolist(),[tuple(lookup[i] for i in f) for f,u in selected],slots,2)
uv=head.data.uv_layers.new(name='UVMap')
for p,(_,u) in zip(head.data.polygons,selected):
 for li,ui in zip(p.loop_indices,u):uv.data[li].uv=uvs[ui]
# A real neck cut, below the gorget. Only this basal boundary is closed.
bm=bmesh.new();bm.from_mesh(head.data);bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,2.69),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
base=[e for e in bm.edges if e.is_boundary and all(abs(x.co.z-2.69)<1e-5 for x in e.verts)];fill=bmesh.ops.holes_fill(bm,edges=base,sides=0);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(head.data);bm.free()
# Remove all inherited head surfaces and the temporary collar neck. No Gaussian blend.
bm=bmesh.new();bm.from_mesh(char.data);doomed=[f for f in bm.faces if (f.material_index==2 and f.calc_center_median().z>260) or (f.material_index==4 and f.calc_center_median().z>277)];removed=len(doomed);bmesh.ops.delete(bm,geom=doomed,context='FACES_ONLY');bm.to_mesh(char.data);bm.free()
retired=[]
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 if ob.name in ['AstraChar2_R6_NeckGraft','AstraChar2_R5_Head','AstraChar2_R5_Ear_L','AstraChar2_R5_Ear_R','AstraChar2_R4_Scalp','AstraChar2_R4_ScalpRoots'] or ob.name.startswith(('AstraChar2_Cornea_','AstraChar2_Iris_','AstraChar2_Pupil_','AstraChar2_Eyebrows_','AstraChar2_Lashes_','AstraChar2_Nostril_','AstraChar2_TearCorner_','AstraChar2_Wetline_')):
  ob.data.clear_geometry();ob.hide_render=True;retired.append(ob.name)
# Subdivision follows the anatomical orbital, nasal, lip and jaw loops from MPFB.
sub=head.modifiers.new('MPFB anatomical subdivision','SUBSURF');sub.levels=2;sub.render_levels=2;bpy.context.view_layer.objects.active=head;bpy.ops.object.modifier_apply(modifier=sub.name);bind(head,head_weights)
eyes={}
for label,g in [('L','helper-l-eye'),('R','helper-r-eye')]:
 fs=[ids for group,ids,uv in faces if group==g];ids=sorted({i for f in fs for i in f});mp={i:j for j,i in enumerate(ids)};name='AstraChar2_Eyeball_'+label;old=bpy.data.objects[name]
 eye=mesh(name,world[ids].tolist(),[tuple(mp[i] for i in f) for f in fs],list(old.data.materials));eye.matrix_world.identity();eye.hide_render=False;eye.hide_set(False)
 for oldmod in list(eye.modifiers):eye.modifiers.remove(oldmod)
 sub=eye.modifiers.new('MPFB fitted eye subdivision','SUBSURF');sub.levels=3;sub.render_levels=3;bpy.context.view_layer.objects.active=eye;bpy.ops.object.modifier_apply(modifier=sub.name);bind(eye,lambda p:{'Head':1});eyes[label]={'center_world':world[ids].mean(0).tolist()}
reset_pose();bpy.context.view_layer.update();error=max(float(abs(np.array(b.matrix_local)-rest[b.name]).max()) for b in arm.data.bones);assert error==0 and len(arm.data.bones)==121 and len(bpy.data.actions)==0
assert all([m.name for m in bpy.data.objects[n].data.materials]==names for n,names in original.items())
r={'iteration':ITER,'source':str(A/'data/3dobjs/base.obj'),'morphs':MORPHS,'scale':scale.tolist(),'eye_reference_native':eye_native.tolist(),'eyes':eyes,'removed_inherited_head_faces':removed,'retired_objects':retired,'head_vertices':len(head.data.vertices),'head_faces':len(head.data.polygons),'neck_boundary_caps':len(fill['faces']),'bones':121,'actions':0,'rest_matrix_error':error,'gaussian_geometry_used':False,'gate':'PENDING THREE VIEW CLAY'}
head['source']='Installed MPFB CC0 base mesh with local morph targets';head['clay_gate']='PENDING';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r6_head.blend'));(O/f'r6_head_iter{ITER:02}_build.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
