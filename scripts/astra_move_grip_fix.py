"""Derived-only grip cleanup: correct misclassified blue faces on the gold gauntlet."""
import bpy,bmesh,json
from mathutils import Vector

def fix_grip():
    body=bpy.data.objects['char1'];rig=bpy.data.objects['Armature'];idx=body.vertex_groups['RightHand'].index
    if body.get('astra_move_grip_clean'):return
    # The imported palm includes faces classified as blue cloth. Assign the hand-weighted
    # faces to existing gold and remove only the probed dangling inner-cuff strip.
    bad=[];sliver=[]
    for p in body.data.polygons:
        if p.material_index not in [1,4]:continue
        vs=[body.data.vertices[i] for i in p.vertices];center=sum((body.matrix_world@v.co for v in vs),Vector())/len(vs)
        weight=sum(sum(g.weight for g in v.groups if g.group==idx) for v in vs)/len(vs)
        if weight>.20 and center.z<1.665 and -.68<center.x<-.28 and -.53<center.y<-.08:bad.append(p.index)
        if weight>.20 and center.z<1.64 and -.395<center.x<-.28 and -.53<center.y<-.315:sliver.append(p.index)
    for i in bad:body.data.polygons[i].material_index=0
    bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sliver],context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
    body['astra_move_palm_sliver_faces']=len(sliver)
    # Close the existing relaxed fingers around the existing hilt, tapering to
    # zero at the wrist. Positions change only on the derived hand mesh.
    import numpy as np
    sword=bpy.data.objects['Godwyn_Sword'];src=np.array([v.vector[:] for v in sword.data.attributes['astra_sword_source'].data]);loc=np.array([v.co[:] for v in sword.data.vertices]);fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),loc,rcond=None)[0]
    g=sword.matrix_world@Vector(np.array([61.2,-66.3,167,1])@fit);tip=sword.matrix_world@sword.data.vertices[int(src[:,2].argmin())].co;axis=-(sword.matrix_world.to_3x3()@Vector(fit[2])).normalized();hand_points=np.array([sword.matrix_world@Vector(v) for v in loc[(src[:,2]>=160)&(src[:,2]<=175)]])-np.array(g);axis_np=np.array(axis);radii=np.linalg.norm(hand_points-(hand_points@axis_np)[:,None]*axis_np,axis=1);envelope=float(max(radii))+.001;print('HILT ENVELOPE',envelope,flush=True);inv=body.matrix_world.inverted();ids=[];changes=[]
    for v in body.data.vertices:
        w=sum(q.weight for q in v.groups if q.group==idx);p=body.matrix_world@v.co
        if w<.72 or p.z>1.635 or not(-.61<p.x<-.29 and -.46<p.y<-.12):continue
        axial=(p-g).dot(axis);rad=p-g-axis*axial;distance=rad.length
        if distance<1e-6:continue
        blend=max(0,min(1,(1.635-p.z)/.07));blend=blend*blend*(3-2*blend)
        factor=1-.56*blend
        # Fingers remain outside the measured shaft envelope, with 1 mm clearance.
        rr=max(envelope,distance*factor);new=g+axis*axial+rad*(rr/distance)
        v.co=inv@new;ids.append(v.index);changes.append((new-p).length)
    for group in body.vertex_groups:
        if group.index!=idx:group.remove(ids)
    body.vertex_groups['RightHand'].add(ids,1,'REPLACE')
    body['astra_move_hilt_envelope_m']=envelope;body['astra_move_closed_finger_vertices']=len(ids);body['astra_move_max_finger_adjustment_m']=max(changes,default=0)
    body.data.update()
    body['astra_move_grip_clean']=True;body['astra_move_gold_palm_faces']=len(bad)
    print('GRIP MATERIAL FACES',len(bad),'SLIVER',len(sliver),flush=True)
