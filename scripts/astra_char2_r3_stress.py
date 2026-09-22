import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_character_common import reset_pose
from astra_xslash_v2_poses import apply_pose,FRAMES
from astra_char2_r3_render import shot
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();ob=bpy.data.objects['char1'];rig=bpy.data.objects['Armature']
def coords():
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());return np.array([ev.matrix_world@v.co for v in ev.data.vertices])
rest=coords();surface_edges={tuple(sorted(e)) for f in ob.data.polygons for e in f.edge_keys};edges=np.array([e.vertices[:] for e in ob.data.edges if tuple(sorted(e.vertices)) in surface_edges]);length=np.linalg.norm(rest[edges[:,1]]-rest[edges[:,0]],axis=1)
r={'poses':{},'weight_sums':{}}
for o in [ob,bpy.data.objects['Astra_Undersleeves']]:
 used={i for f in o.data.polygons for i in f.vertices};sums=np.array([sum(g.weight for g in o.data.vertices[i].groups) for i in used]);r['weight_sums'][o.name]={'zero':int(sum(sums<1e-5)),'nonunit':int(sum(abs(sums-1)>.01)),'min':float(sums.min()),'max':float(sums.max())}
for name in ['windup','cross','follow']:
 bpy.context.scene.frame_set(FRAMES[name]);apply_pose(rig,name);p=coords();r['poses'][name]={}
 for region in ['shoulder','cape_root']:
  if region=='shoulder':
   # Right/left refers to model; capture the higher stressed arm's junction.
   sides=[]
   for side in [-1,1]:
    mask=(rest[:,2]>2.25)&(rest[:,2]<2.73)&(rest[:,0]*side>.28)&(rest[:,0]*side<.65)
    sides.append((float(np.median(p[mask,2])),mask))
   mask=max(sides,key=lambda x:x[0])[1];offset=Vector((0,-3,.35))
  else:mask=(rest[:,2]>2.2)&(rest[:,2]<2.75)&(rest[:,1]>.10)&(abs(rest[:,0])<.42);offset=Vector((1.5,3,.45))
  center=Vector(np.median(p[mask],axis=0));em=mask[edges[:,0]]&mask[edges[:,1]]&(length>.0005);rat=np.linalg.norm(p[edges[em,1]]-p[edges[em,0]],axis=1)/length[em]
  r['poses'][name][region]={'edge_ratio_p50_p95_p99_max':np.percentile(rat,[50,95,99,100]).tolist(),'edges_over_2x':int(sum(rat>2)),'edges_measured':int(len(rat)),'target':list(center)}
  for label,mats in [('cloth_only',(1,4)),('armor_only',(0,))]:
   selected={vi for f in ob.data.polygons if f.material_index in mats for vi in f.vertices};sub=np.zeros(len(rest),dtype=bool);sub[list(selected)]=True;sub &= mask;se=sub[edges[:,0]]&sub[edges[:,1]]&(length>.0005)
   rr=np.linalg.norm(p[edges[se,1]]-p[edges[se,0]],axis=1)/length[se]
   if len(rr):r['poses'][name][region][label]={'edge_ratio_p95':float(np.percentile(rr,95)),'edges_over_2x':int(sum(rr>2)),'edges_measured':int(len(rr))}
  if '--metrics-only' not in sys.argv:shot('stress_'+name+'_'+region,center+offset,center,1.4)
reset_pose();bpy.context.scene.frame_set(1);reset_pose();r['neutral_restored_in_memory']=True
(OUT/('r3_stress_probe.json' if '--metrics-only' in sys.argv else 'r3_stress.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
