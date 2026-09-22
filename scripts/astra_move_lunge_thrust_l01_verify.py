"""Fresh evaluated geometry comparison for the L01 quaternion-only correction."""
import sys,json,math,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'

def check(path):
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['Armature'];body=bpy.data.objects['char1'];sw=bpy.data.objects['Godwyn_Sword']
    body.hide_viewport=False;sw.hide_viewport=False
    groups={g.index:g.name for g in body.vertex_groups}
    soles={side:[v.index for v in body.data.vertices if (body.matrix_world@v.co).z<.13 and sum(g.weight for g in v.groups if groups[g.group] in [side+'Foot',side+'ToeBase'])>.6] for side in ['Left','Right']}
    families={p.name.rsplit('_',1)[0]:[] for p in r.pose.bones if p.name.startswith(('phys_robe','phys_cape'))}
    for v in body.data.vertices:
        if (body.matrix_world@v.co).z>.4:continue
        weights={}
        for g in v.groups:
            fam=groups[g.group].rsplit('_',1)[0]
            if fam in families:weights[fam]=weights.get(fam,0)+g.weight
        for fam,w in weights.items():
            if w>.55:families[fam].append(v.index)
    families={k:v for k,v in families.items() if len(v)>10}
    src=np.array([p.vector[:] for p in sw.data.attributes['astra_sword_source'].data])
    blade_polys=[tuple(p.vertices) for p in sw.data.polygons if max(src[list(p.vertices),2])<145]
    contacts=[];clearance=[]
    for f in range(1,65):
        s.frame_set(f);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=body.evaluated_get(dg);me=ev.to_mesh()
        co=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);M=np.array(ev.matrix_world);co=co@M[:3,:3].T+M[:3,3]
        contacts.append({'frame':f,'sole':{k:float(co[v,2].min())+.015 for k,v in soles.items()},'hem':{k:float(co[v,2].min())+.015 for k,v in families.items()}})
        if 37<=f<=64:
            body_tree=BVHTree.FromPolygons(co.tolist(),[tuple(p.vertices) for p in me.polygons])
            se=sw.evaluated_get(dg);sm=se.to_mesh();sv=[se.matrix_world@v.co for v in sm.vertices]
            blade_tree=BVHTree.FromPolygons(sv,blade_polys)
            ids=sorted(set(i for p in blade_polys for i in p));near=min(body_tree.find_nearest(sv[i])[3] for i in ids)
            overlaps=blade_tree.overlap(body_tree)
            clearance.append({'frame':f,'blade_body_triangle_overlap_pairs':len(overlaps),'min_sampled_blade_vertex_body_distance_m':near,'blade_floor_clearance_m':min(sv[i].z for i in ids)+.015})
            se.to_mesh_clear()
        ev.to_mesh_clear()
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'contacts':contacts,'blade_clearance':clearance}

before=check(ROOT/'models/astra_move_lunge_thrust_pre_l01.blend')
after=check(ROOT/'models/astra_move_lunge_thrust_wip.blend')
delta=max(abs(a[k][n]-b[k][n]) for a,b in zip(before['contacts'],after['contacts']) for k in ['sole','hem'] for n in a[k])
report={'before':before,'after':after,'max_sole_or_hem_change_m':delta,'clearance_method':'Evaluated character and blade-only triangles (source Z<145), BVH overlap and nearest blade vertex, sampled recovery frames. Excludes hilt/grasp; does not certify unsampled subframe collisions.'}
(OUT/'lunge_thrust_l01_geometry.json').write_text(json.dumps(report,indent=2))
p=OUT/'lunge_thrust_contacts.json';contacts=json.loads(p.read_text());contacts['after']=after['contacts'];p.write_text(json.dumps(contacts,indent=2))
print(json.dumps({'max_contact_change_m':delta,'before_clearance':before['blade_clearance'],'after_clearance':after['blade_clearance']},indent=2),flush=True)
assert delta<.00001
