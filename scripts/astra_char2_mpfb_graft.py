"""Reuse round-5 replacement/skin/cloth-fit mechanics with the reviewed MPFB head."""
import bpy,bmesh,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_geometry import bind,head_weights,tube
from astra_char2_r5_armor import build as armor_build
from astra_char2_r5_fit import fit
from astra_char2_mpfb_clay import render_views

def neck_extension(h,tighten=False):
    bm=bmesh.new();bm.from_mesh(h.data)
    if tighten:
        for v in bm.verts:
            t=max(0,min(1,(2.815-v.co.z)/.070));t=t*t*(3-2*t)
            # Remove the MPFB trapezius flare below the mandible, preserving the face.
            v.co.x*=1-.38*t
    zcut=2.745
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,zcut),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    edge=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-zcut)<1e-4 for v in e.verts)]
    verts=set(v for e in edge for v in e.verts)
    # One neck boundary, bridged with matching topology into a collar-contained seam.
    start=next(iter(verts));ring=[start];last=None;cur=start
    while True:
        choices=[e.other_vert(cur) for e in cur.link_edges if e in edge and e.other_vert(cur)!=last]
        nxt=next((v for v in choices if v not in ring),None)
        if nxt is None:break
        ring.append(nxt);last,cur=cur,nxt
    assert len(ring)==len(verts),(len(ring),len(verts))
    initial=np.array([v.co[:] for v in ring]);angles=np.arctan2(initial[:,0],-(initial[:,1]+.195))
    previous=ring
    for k in range(1,13):
        t=k/12;ease=t*t*(3-2*t);z=zcut+(2.605-zcut)*t
        target=np.column_stack([.072*np.sin(angles),-.175-.085*np.cos(angles),np.full(len(ring),z)])
        pts=initial*(1-ease)+target*ease;pts[:,2]=z
        current=[bm.verts.new(p) for p in pts]
        for i in range(len(ring)):
            j=(i+1)%len(ring);bm.faces.new((previous[i],previous[j],current[j],current[i]))
        previous=current
    bm.faces.new(tuple(reversed(previous)))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(h.data);bm.free()
    return len(ring)

def graft(iteration=1,head_iteration=4):
    bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_premfpb.blend'));reset_pose()
    arm=bpy.data.objects['Armature'];char=bpy.data.objects['char1'];slots=list(char.data.materials)
    original={o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if hasattr(o.data,'materials')}
    rests={b.name:np.array(b.matrix_local) for b in arm.data.bones}
    def protected(f):
        return f.material_index in (1,4) and (max((char.matrix_world@char.data.vertices[i].co).z for i in f.vertices)<2.15 if iteration>=3 else f.center.z<277)
    cloth=[f for f in char.data.polygons if protected(f)]
    ids=sorted({i for f in cloth for i in f.vertices});raw=np.array([char.data.vertices[i].co[:] for i in ids]);faces=[tuple(f.vertices) for f in cloth]
    oldeyes={label:(bpy.data.objects['AstraChar2_Eyeball_'+label].matrix_world.translation.copy(),list(bpy.data.objects['AstraChar2_Eyeball_'+label].data.materials)) for label in ['L','R']}
    # Save exact original eye world extents for the existing component alignment.
    eyeinfo={}
    for label in ['L','R']:
        ob=bpy.data.objects['AstraChar2_Eyeball_'+label];p=np.array([ob.matrix_world@v.co for v in ob.data.vertices]);eyeinfo[label]=((p.min(0)+p.max(0))/2,(p.max(0)-p.min(0)).max()/2)
    bm=bmesh.new();bm.from_mesh(char.data);removed={};kill=[]
    for f in bm.faces:
        c=char.matrix_world@f.calc_center_median();m=f.material_index
        replace=(m==2 and c.z>2.60) or (m in (0,3) and ((c.z>2.53 and abs(c.x)<.31) or (c.z>2.43 and .24<abs(c.x)<.62))) or (m==4 and c.z>2.77)
        if iteration>=2:
            replace=(m==2 and c.z>2.60) or (m in (0,3) and ((c.z>2.18 and abs(c.x)<.62) or (c.z>1.98 and abs(c.x)<.30))) or (m==4 and c.z>2.77)
        if iteration>=3:
            replace=replace or (m in (1,4) and c.z>2.43 and abs(c.x)<.67) or (2.18<c.z<2.70 and .28<abs(c.x)<.67)
            if m==4 and max((char.matrix_world@v.co).z for v in f.verts)>2.74:replace=True
        if replace:kill.append(f);removed[str(m)]=removed.get(str(m),0)+1
    bmesh.ops.delete(bm,geom=kill,context='FACES_ONLY');bm.to_mesh(char.data);bm.free();char.data.update()
    # Source append uses the round-5 library-rebase pattern, preserving the destination rig.
    with bpy.data.libraries.load(str(R/f'models/astra_character_mpfb_head_i{head_iteration:02}.blend'),link=False) as (src,dst):
        dst.objects=['AstraChar2_Mpfb_Head']
    h=dst.objects[0];bpy.context.scene.collection.objects.link(h)
    for mod in list(h.modifiers):h.modifiers.remove(mod)
    ringcount=neck_extension(h,iteration>=2)
    h.data.materials.clear()
    for m in slots:h.data.materials.append(m)
    for f in h.data.polygons:f.material_index=2;f.use_smooth=True
    # Apply anatomical subdivision before the unchanged armature modifier, so GLB geometry matches.
    bpy.context.view_layer.objects.active=h;h.select_set(True)
    sub=h.modifiers.new('Anatomical final topology','SUBSURF');sub.levels=2;sub.render_levels=2
    bpy.ops.object.modifier_apply(modifier=sub.name)
    bind(h,head_weights)
    info=json.loads((O/f'mpfb_head_i{head_iteration:02}_parameters.json').read_text())
    eye_report={}
    for label in ['L','R']:
        oldcenter,oldradius=eyeinfo[label]
        which='L' if oldcenter[0]>0 else 'R';newcenter=np.array(info['eyes'][which]['center']);newradius=info['eyes'][which]['radius'];scale=float(newradius/oldradius)
        eye_report[label]={'old_center':oldcenter.tolist(),'new_center':newcenter.tolist(),'radius_scale':scale}
        for stem in ['Eyeball','Iris','Pupil','Cornea','TearCorner','Wetline','Lashes','Eyebrows']:
            ob=bpy.data.objects.get('AstraChar2_'+stem+'_'+label)
            if not ob:continue
            world=ob.matrix_world.copy();inv=world.inverted()
            for v in ob.data.vertices:
                p=np.array(world@v.co);p=newcenter+(p-oldcenter)*scale;v.co=inv@Vector(p)
            bind(ob,lambda p:{'Head':1})
            ob.hide_render=False;ob.hide_set(False)
        # The old nostril masks would duplicate the actual MPFB cavities.
        ob=bpy.data.objects.get('AstraChar2_Nostril_'+label)
        if ob:ob.data.clear_geometry();ob.hide_render=True
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(h,bpy.context.evaluated_depsgraph_get())
    projected=0
    for label in ['L','R']:
        ob=bpy.data.objects['AstraChar2_Eyebrows_'+label];inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:
            p=ob.matrix_world@v.co;hit,n,_,_=tree.ray_cast(Vector((p.x,-1,p.z)),Vector((0,1,0)),2)
            if hit:v.co=inv@(hit+n*.00065);projected+=1
    # Keep the original ornate torso and sleeves; rebuild only the broken collar/shoulder zone.
    armor_build(slots)
    if iteration>=3:
        # Smooth skinned blue undersleeves close the armor articulation gaps.
        under=bpy.data.objects['Astra_Undersleeves'];underslots=list(under.data.materials);under.data.clear_geometry();under.hide_render=True
        for label,bone,end in [('L','LeftArm','LeftForeArm'),('R','RightArm','RightForeArm')]:
            a=arm.matrix_world@arm.data.bones[bone].head_local;b=arm.matrix_world@arm.data.bones[end].head_local
            pts=[tuple(a.lerp(b,t)) for t in np.linspace(0,1.10,32)]
            ob=tube('AstraChar2_Mpfb_Undersleeve_'+label,pts,np.linspace(.115,.094,32),underslots,sides=48)
            bind(ob,lambda p,bn=bone:{bn:1})
        old=bpy.data.objects.get('AstraChar2_R3_ChasedLaurel')
        if old:old.data.clear_geometry();old.hide_render=True
    fitted=fit()
    vg=char.vertex_groups.get('AstraChar2_R5_CollarFit')
    if iteration<2:
        for v in char.data.vertices:
            p=char.matrix_world@v.co
            if p.z<2.43:vg.remove([v.index])
            elif any(g.group==vg.index for g in v.groups):vg.add([v.index],min(1,(p.z-2.43)/.09),'REPLACE')
    discarded=[]
    for ob in list(bpy.data.objects):
        if iteration<2 and ob.name.startswith(('AstraChar2_R5_Cuirass','AstraChar2_R5_UpperArm_','AstraChar2_R5_SacredEmblem','AstraChar2_R5_SunRay_')):
            discarded.append(ob.name);bpy.data.objects.remove(ob,do_unlink=True)
        elif ob.name.startswith(('AstraChar2_R4_','AstraChar2_R2_Hair','AstraChar2_R3_Flow','AstraChar2_R3_Plait')):
            ob.hide_render=True
    # Remaining body surfaces must never respond to hair-only physics.
    used={i for f in char.data.polygons for i in f.vertices};hairidx={g.index for g in char.vertex_groups if g.name.startswith('phys_hair')};cleaned=0
    for i in used:
        v=char.data.vertices[i]
        if not any(g.group in hairidx and g.weight>1e-7 for g in v.groups):continue
        entries=[(g.group,g.weight) for g in v.groups if g.group not in hairidx];total=sum(w for g,w in entries if char.vertex_groups[g].name in arm.data.bones)
        for gi in hairidx:char.vertex_groups[gi].remove([i])
        if total:
            for gi,w in entries:
                if char.vertex_groups[gi].name in arm.data.bones:char.vertex_groups[gi].add([i],w/total,'REPLACE')
        cleaned+=1
    reset_pose()
    error=max(float(np.abs(np.array(b.matrix_local)-rests[b.name]).max()) for b in arm.data.bones)
    assert error==0 and len(arm.data.bones)==121 and len(bpy.data.actions)==0
    assert all([m.name if m else None for m in bpy.data.objects[n].data.materials]==mats for n,mats in original.items())
    assert np.array_equal(raw,np.array([char.data.vertices[i].co[:] for i in ids]))
    aftercloth=[tuple(f.vertices) for f in char.data.polygons if protected(f)]
    assert aftercloth==faces
    report={'head_source_iteration':head_iteration,'graft_iteration':iteration,'bones':121,'actions':0,'rest_matrix_error':error,
            'stable_existing_names_and_material_slots':True,'original_cloth_rest_vertices_exact':True,'protected_cloth_vertex_count':len(ids),
            'removed_faces_by_material':removed,'neck_bridge_vertices_per_ring':ringcount,'neck_bridge_rows':12,
            'seam':'Closed MPFB neck extended to z=2.605m inside original body/collar; overlapping armor-concealed seam, no claim of body topology weld.',
            'eyes':eye_report,'eyebrow_vertices_projected':projected,'collar_fit_candidate_vertices':fitted,'visible_body_hair_weights_cleaned':cleaned,
            'new_head_vertices':len(h.data.vertices),'new_head_faces':len(h.data.polygons),'clay_gate':'PENDING'}
    report['protected_cloth_scope']='All original cloth faces entirely below z=2.15m; damaged upper fragments explicitly removed.' if iteration>=3 else 'Original cloth through z=2.77m.'
    (O/f'mpfb_graft_i{iteration:02}.json').write_text(json.dumps(report,indent=2))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(R/f'models/astra_character_v2_mpfb_graft_i{iteration:02}.blend'))
    render_views(f'mpfb_graft_i{iteration:02}_clay',('front','side','three_quarter','collar','body'))

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['1'];graft(int(args[0]))
