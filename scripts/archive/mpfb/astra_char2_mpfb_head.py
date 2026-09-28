"""MPFB anatomical head source; targets remain editable in isolated source checkpoints."""
import bpy,bmesh,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_probe import enable_mpfb,EXT
from astra_char2_mpfb_clay import render_views

def recipe(iteration):
    macro={'gender':1.,'age':.30,'muscle':.60,'weight':.40,'proportions':.65,'height':.5,'cupsize':.5,'firmness':.5,'race':{'caucasian':1.,'asian':0.,'african':0.}}
    targets={'head/head-rectangular':.25,'head/head-oval':.10,'head/head-scale-vert-incr':.12,
             'chin/chin-width-incr':.25,'chin/chin-bones-incr':.30,'chin/chin-prominent-incr':.10,
             'eyebrows/eyebrows-trans-forward':.30,'eyebrows/eyebrows-trans-down':.10,
             'nose/nose-greek-incr':.20,'nose/nose-width3-decr':.12,
             'mouth/mouth-scale-horiz-incr':.10,'mouth/mouth-lowerlip-volume-decr':.08}
    for side in ['l','r']:
        targets[f'eyes/{side}-eye-push2-in']=.15
        targets[f'cheek/{side}-cheek-bones-incr']=.20
        targets[f'ears/{side}-ear-scale-decr']=.08
    if iteration>=2:
        macro.update(age=.5,muscle=.58,weight=.34)
        targets.update({'head/head-rectangular':.12,'head/head-oval':.20,'head/head-scale-vert-incr':.24,
                        'chin/chin-width-incr':.06,'chin/chin-bones-incr':.18,'chin/chin-prominent-incr':.16,
                        'eyebrows/eyebrows-trans-forward':.48,'eyebrows/eyebrows-trans-down':.12,
                        'nose/nose-greek-incr':.28,'nose/nose-scale-vert-incr':.15,
                        'nose/nose-width3-decr':.16,'mouth/mouth-scale-horiz-incr':.20,
                        'mouth/mouth-upperlip-volume-incr':.10})
        for side in ['l','r']:
            targets[f'eyes/{side}-eye-trans-out']=.28
            targets[f'eyes/{side}-eye-push2-in']=.26
            targets[f'eyes/{side}-eye-height2-decr']=.14
            targets[f'cheek/{side}-cheek-bones-incr']=.28
    if iteration>=3:
        targets.update({'nose/nose-scale-depth-decr':.20,'nose/nose-point-up':.08,
                        'head/head-fat-decr':.16,'mouth/mouth-scale-horiz-incr':.24,
                        'eyebrows/eyebrows-trans-forward':.38,'chin/chin-height-incr':.08})
        for side in ['l','r']:
            targets[f'eyes/{side}-eye-trans-out']=.52
            targets[f'eyes/{side}-eye-scale-incr']=.12
            targets[f'eyes/{side}-eye-height2-decr']=.06
            targets[f'cheek/{side}-cheek-inner-decr']=.14
    if iteration>=4:
        targets.update({'mouth/mouth-scale-horiz-incr':.60,'head/head-back-scale-depth-decr':.15,
                        'chin/chin-bones-incr':.30,'chin/chin-prominent-incr':.10,
                        'nose/nose-scale-depth-decr':.28})
        for side in ['l','r']:
            targets[f'eyes/{side}-eye-trans-out']=.80
            targets.pop(f'eyes/{side}-eye-height2-decr',None)
            targets[f'eyes/{side}-eye-height2-incr']=.50
            targets[f'eyes/{side}-eye-height1-incr']=.12
            targets[f'eyes/{side}-eye-height3-incr']=.12
    return macro,targets

def build(iteration):
    enable_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    macro,targets=recipe(iteration)
    human=HumanService.create_human(macro_detail_dict=macro)
    assert len(human.data.vertices)==19158
    human.name='MPFB anatomical source'
    for name,val in targets.items():
        TargetService.load_target(human,str(EXT/'mpfb/data/targets'/f'{name}.target.gz'),weight=val)
    bpy.context.view_layer.update()
    for mod in list(human.modifiers):human.modifiers.remove(mod)
    dg=bpy.context.evaluated_depsgraph_get();ev=human.evaluated_get(dg)
    me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
    coords=np.array([v.co[:] for v in me.vertices])
    groups={g.name:[v.index for v in human.data.vertices if any(x.group==g.index and x.weight>.5 for x in v.groups)] for g in human.vertex_groups if g.name in ['body','joint-head','joint-jaw','joint-neck','joint-l-eye','joint-r-eye','helper-l-eye','helper-r-eye']}
    # A uniform anatomical scale, crown and rig-neck placement; no procedural face sculpt.
    bodyids=groups['body'];top=coords[bodyids,2].max();scale=1.60
    neck=coords[groups['joint-neck']].mean(0)
    translation=np.array([0,-.195-neck[1]*scale,3.16-top*scale])
    for v in me.vertices:v.co=Vector(v.co)*scale+Vector(translation)
    h=bpy.data.objects.new('AstraChar2_Mpfb_Head',me);bpy.context.scene.collection.objects.link(h)
    # Remove MPFB helper cages using explicit body membership, then cut the lower neck.
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();keep=set(bodyids)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,2.61),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    cut=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-2.61)<1e-4 for v in e.verts)]
    if cut:bmesh.ops.holes_fill(bm,edges=cut,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    h.data.materials.clear();mat=bpy.data.materials.new('MPFB anatomical clay placeholder');mat.diffuse_color=(.4,.4,.4,1);h.data.materials.append(mat)
    for f in me.polygons:f.material_index=0;f.use_smooth=True
    sub=h.modifiers.new('Anatomical subdivision','SUBSURF');sub.levels=2;sub.render_levels=2
    human.hide_render=True;human.hide_set(True)
    joints={name:(coords[ids].mean(0)*scale+translation).tolist() for name,ids in groups.items() if name!='body' and ids}
    eyes={}
    for side,label in [('l','L'),('r','R')]:
        p=coords[groups['helper-'+side+'-eye']]*scale+translation
        # The MPFB eye helper is an anatomical sphere; least-squares sphere fit.
        a=np.column_stack([2*p,np.ones(len(p))]);sol=np.linalg.lstsq(a,(p*p).sum(1),rcond=None)[0]
        center=sol[:3];radius=float(np.sqrt(sol[3]+center@center))
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=radius,location=center)
        eye=bpy.context.object;eye.name='AstraChar2_Mpfb_Eye_'+label;eye.data.materials.append(mat)
        for f in eye.data.polygons:f.use_smooth=True
        eyes[label]={'center':center.tolist(),'radius':radius,'helper_bounds':[p.min(0).tolist(),p.max(0).tolist()]}
    h['mpfb_source_vertices']=19158;h['mpfb_iteration']=iteration;h['mpfb_targets']=json.dumps(targets)
    data={'iteration':iteration,'macro':macro,'targets':targets,'uniform_scale':scale,'translation':translation.tolist(),'joints':joints,'eyes':eyes,'head_vertices':len(me.vertices),'head_faces':len(me.polygons)}
    (O/f'mpfb_head_i{iteration:02}_parameters.json').write_text(json.dumps(data,indent=2))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(R/f'models/astra_character_mpfb_head_i{iteration:02}.blend'))
    render_views(f'mpfb_head_i{iteration:02}_clay')

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['1'];build(int(args[0]))
