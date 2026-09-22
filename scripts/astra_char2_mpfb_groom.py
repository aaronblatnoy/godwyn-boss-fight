"""Salvage the existing layered R4 curve groom and three-bundle plaits on MPFB."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_groom_geometry import weights,bind
from astra_char2_r5_geometry import mesh,bind as bind_geo
from astra_char2_mpfb_clay import render_views
from astra_char2_mpfb_ornament import decorate

def groom(iteration=1):
    bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_graft_i03.blend'));reset_pose()
    h=bpy.data.objects['AstraChar2_Mpfb_Head'];tree=BVHTree.FromObject(h,bpy.context.evaluated_depsgraph_get())
    center=Vector((0,-.24,3.01));reports=[]
    for cu in list(bpy.data.objects):
        if cu.type!='CURVES' or not cu.name.startswith('AstraChar2_R4_Curves_'):continue
        suffix=cu.name.removeprefix('AstraChar2_R4_Curves_');ctl=bpy.data.objects['AstraChar2_R4_Control_'+suffix];portable=bpy.data.objects['AstraChar2_R4_Strands_'+suffix]
        n=len(cu.data.curves);K=len(cu.data.points)//n
        raw=np.empty(len(cu.data.points)*3,np.float32);cu.data.position_data.foreach_get('vector',raw);old=raw.reshape(n,K,3);p=old.copy()
        fades=np.exp(-np.arange(K)/4.5)
        root_dist=[]
        for j in range(n):
            root=Vector(p[j,0]);desired=root.copy();desired.z=max(desired.z,3.025 if 'Back' in suffix else 3.065)
            d=(desired-center).normalized();hit,normal,_,_=tree.ray_cast(center,d,.8)
            if hit:
                actual=hit+normal*.00055;delta=np.array(actual)-p[j,0];p[j]+=fades[:,None]*delta
                root_dist.append(float(np.linalg.norm(delta)))
            for k in range(K):
                if p[j,k,2]<2.90:continue
                q=Vector(p[j,k]);hit,normal,_,distance=tree.find_nearest(q)
                if hit and (q-hit).dot(normal)<.0003:
                    p[j,k]=hit+normal*(.00055 if k==0 else .0012)
        delta=(p-old).reshape(-1,3)
        cu.data.position_data.foreach_set('vector',p.ravel());ctl.data.vertices.foreach_set('co',p.ravel());ctl.data.update()
        # Exact same displacement for each three-vertex tube cross-section.
        assert len(portable.data.vertices)==n*K*3
        verts=np.empty(len(portable.data.vertices)*3,np.float32);portable.data.vertices.foreach_get('co',verts)
        verts=verts.reshape(-1,3)+np.repeat(delta,3,axis=0);portable.data.vertices.foreach_set('co',verts.ravel());portable.data.update()
        chain='front_'+('L' if suffix.startswith('L_') else 'R') if ('Front' in suffix or 'Braids' in suffix) else 'back'
        w,names=weights(p.reshape(-1,3),chain);ww=w.reshape(n,K,5)
        for k in range(4):
            a=math.exp(-k);ww[:,k]*=1-a;ww[:,k,0]+=a
        for ob,weight in [(ctl,w),(portable,np.repeat(w,3,axis=0))]:
            ob.vertex_groups.clear()
            for m in list(ob.modifiers):
                if m.type=='ARMATURE':ob.modifiers.remove(m)
            bind(ob,weight,names)
        cu.hide_render=False;cu.hide_set(False);ctl.hide_render=True;ctl.hide_set(True);portable.hide_render=True;portable.hide_set(True)
        cu['mpfb_rerooted']=True;cu['groom_strands']=n;cu['groom_points_per_strand']=K;cu['chain']=chain
        reports.append({'group':suffix,'strands':n,'points_per_strand':K,'chain':chain,'root_movement_max_m':max(root_dist),'root_movement_mean_m':float(np.mean(root_dist))})
        print('MPFB_REROOT',suffix,n,flush=True)
    # Replace the full sphere underlay by only the anatomical scalp above the hairline.
    old=bpy.data.objects['AstraChar2_R4_Scalp'];old.data.clear_geometry();old.hide_render=True
    scalp=bpy.data.objects['AstraChar2_R4_ScalpRoots'];slots=list(scalp.data.materials)
    selected=[]
    for f in h.data.polygons:
        p=f.center
        threshold=3.099-.31*abs(p.x) if p.y<-.28 else 2.995
        if p.z>threshold:selected.append(f)
    used=sorted({i for f in selected for i in f.vertices});lookup={i:j for j,i in enumerate(used)}
    vv=[tuple(h.data.vertices[i].co+h.data.vertices[i].normal*.00035) for i in used]
    ff=[tuple(lookup[i] for i in f.vertices) for f in selected]
    scalp=mesh(scalp.name,vv,ff,slots);scalp.matrix_world.identity();bind_geo(scalp,lambda p:{'Head':1});scalp.hide_render=False;scalp.hide_set(False)
    report={'method':'Salvaged R4 guides, fine strands and 6 three-bundle plaits. Geometric scalp projection; UV-independent.',
            'groups':reports,'native_strands':sum(x['strands'] for x in reports),'hair_bones':12,'scalp_faces':len(ff),
            'portable_correspondence':'Same per-point displacement applied to native/control and each portable triangle cross-section; quantitative test follows.'}
    report['forged_plate_relief']=decorate()
    (O/f'mpfb_groom_i{iteration:02}.json').write_text(json.dumps(report,indent=2))
    reset_pose();assert len(bpy.data.actions)==0 and len(bpy.data.objects['Armature'].data.bones)==121
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/f'models/astra_character_v2_mpfb_groom_i{iteration:02}.blend'))
    render_views(f'mpfb_groom_i{iteration:02}_clay',('front','side','three_quarter','body'))

if __name__=='__main__':groom()
