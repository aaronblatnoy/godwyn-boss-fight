"""Evaluate existing surfaces for foot-floor and cloth contact diagnostics."""
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from astra_xslash_v2_on_char_build import sword_landmarks,sword_points
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
label=args[0] if args else 'before'
source=ROOT/('models/astra_xslash_v2_final_prefix.blend' if label=='before' else 'models/astra_xslash_v2_final_wip.blend')
if len(args)>1:source=Path(args[1])
if not source.exists():source=ROOT/'models/astra_xslash_v2_final_wip.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene;r=bpy.data.objects['Armature'];body=bpy.data.objects['char1'];sw=bpy.data.objects['Godwyn_Sword'];stage=bpy.data.objects['Astra_Stage']
floor=max((stage.matrix_world@v.co).z for v in stage.data.vertices)
tip,grip,_=sword_landmarks(sw)
gnames={g.index:g.name for g in body.vertex_groups}
regions={k:[] for k in ['LeftFoot','RightFoot','cloth']};cloth_families={}
for v in body.data.vertices:
    pos=body.matrix_world@v.co
    ws={gnames[g.group]:g.weight for g in v.groups}
    for side in ['Left','Right']:
        if sum(w for n,w in ws.items() if n in [side+'Foot',side+'ToeBase'])>.65 and pos.z<.12:regions[side+'Foot'].append(v.index)
    cw=sum(w for n,w in ws.items() if n.startswith('phys_robe') or n.startswith('phys_cape'))
    if cw>.65 and pos.z<1.45:
        regions['cloth'].append(v.index)
for p in r.pose.bones:
    if p.name.startswith('phys_'):
        fam=p.name.rsplit('_',1)[0];cloth_families[fam]={'root_parent':r.data.bones[fam+'_00'].parent.name,'count':sum(1 for b in r.pose.bones if b.name.startswith(fam+'_'))}
rows=[]
for f in range(1,91):
    s.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();ob=body.evaluated_get(dg);me=ob.to_mesh()
    co=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);M=np.array(ob.matrix_world);co=co@M[:3,:3].T+M[:3,3]
    foot={n:{'min_clearance_m':float(np.min(co[ix,2])-floor),'p05_clearance_m':float(np.quantile(co[ix,2],.05)-floor),'centroid':co[ix].mean(axis=0).tolist()} for n,ix in regions.items() if 'Foot' in n}
    t,g=sword_points(r,sw,tip,grip);cv=co[regions['cloth']]
    axis=np.array(t-g);rel=cv-np.array(g);u=np.clip(rel@axis/np.dot(axis,axis),0,1);dist=np.linalg.norm(rel-u[:,None]*axis,axis=1)
    # Capsule proxies identify candidates only; do not assert mesh intersections from distance alone.
    near={}
    for side in ['Left','Right']:
        for a,b in [('UpLeg','Leg'),('Leg','Foot')]:
            pa=np.array(r.matrix_world@r.pose.bones[side+a].matrix.translation);pb=np.array(r.matrix_world@r.pose.bones[side+b].matrix.translation)
            v=pb-pa;rel=cv-pa;u=np.clip(rel@v/np.dot(v,v),0,1);dd=np.linalg.norm(rel-u[:,None]*v,axis=1)
            near[side+a]={'min_distance_m':float(dd.min()),'vertices_within_0_065m':int((dd<.065).sum())}
    rows.append({'frame':f,'feet':foot,'sword_tip':list(t),'sword_grip':list(g),'cloth_sword_min_vertex_centerline_m':float(dist.min()),'cloth_leg_capsule_candidates':near,'cloth_min_z':float(cv[:,2].min())})
    ob.to_mesh_clear()
report={'floor_z':floor,'foot_sole_vertex_counts':{n:len(ix) for n,ix in regions.items()},'cloth_families':cloth_families,'rows':rows}
(ROOT/f'renders/astra/naturalness_surface_{label}.json').write_text(json.dumps(report,indent=2))
print('SURFACE',label,'floor',floor,'counts',report['foot_sole_vertex_counts'])
print('FOOT RANGE',{side:(min(x['feet'][side]['min_clearance_m'] for x in rows),max(x['feet'][side]['min_clearance_m'] for x in rows if x['frame']<=29 or x['frame']>=40)) for side in ['LeftFoot','RightFoot']})
print('CLOTH SWORD',[(r['frame'],r['cloth_sword_min_vertex_centerline_m']) for r in rows if r['cloth_sword_min_vertex_centerline_m']<.1])
