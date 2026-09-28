"""Authoritative recombination: approved banked collar body + isolated MPFB head 04.
Never runs the superseded armor rebuild. All banked armor meshes/weights are pinned.
"""
import bpy,bmesh,sys,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_geometry import bind,head_weights
from astra_char2_mpfb_graft import neck_extension
from astra_char2_mpfb_clay import render_views

def mesh_digest(o,faces=True):
    h=hashlib.sha256();a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a);h.update(a.tobytes())
    h.update(np.array(o.matrix_world,dtype=np.float64).tobytes())
    h.update(repr([(g.name,g.index) for g in o.vertex_groups]).encode())
    for v in o.data.vertices:h.update(repr([(g.group,g.weight) for g in v.groups]).encode())
    if faces:
        a=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',a);h.update(a.tobytes())
        a=np.empty(len(o.data.polygons),np.int32);o.data.polygons.foreach_get('material_index',a);h.update(a.tobytes())
    return h.hexdigest()

def main():
    src=R/'models/astra_character_v2.blend'
    expected='68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e'
    sha=hashlib.sha256(src.read_bytes()).hexdigest();assert sha==expected,('Unexpected canonical baseline',sha)
    bpy.ops.wm.open_mainfile(filepath=str(src));reset_pose();arm=bpy.data.objects['Armature'];char=bpy.data.objects['char1']
    original={o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if hasattr(o.data,'materials')}
    rests={b.name:np.array(b.matrix_local) for b in arm.data.bones}
    protected=[o for o in bpy.data.objects if o.type=='MESH' and (o.name.startswith('AstraChar2_R5_') or o.name in ['Astra_Undersleeves','Godwyn_Sword'])]
    hashes={o.name:mesh_digest(o) for o in protected};bodyhash=mesh_digest(char,False)
    # Keep every non-head body polygon and all body rest vertices / vertex weights.
    def replace(f):return f.material_index==2 and (char.matrix_world@f.center).z>2.60
    retained=[tuple(f.vertices) for f in char.data.polygons if not replace(f)]
    bm=bmesh.new();bm.from_mesh(char.data)
    kill=[f for f in bm.faces if f.material_index==2 and (char.matrix_world@f.calc_center_median()).z>2.60]
    removed=len(kill);bmesh.ops.delete(bm,geom=kill,context='FACES_ONLY');bm.to_mesh(char.data);bm.free();char.data.update()
    assert [tuple(f.vertices) for f in char.data.polygons]==retained
    assert mesh_digest(char,False)==bodyhash
    neck=bpy.data.objects.get('AstraChar2_R6_NeckGraft')
    if neck:neck.hide_render=True;neck.hide_set(True)  # Keep data/name; MPFB replaces this temporary neck surface.
    with bpy.data.libraries.load(str(R/'models/astra_character_mpfb_head_i04.blend'),link=False) as (source,dst):dst.objects=['AstraChar2_Mpfb_Head']
    head=dst.objects[0];bpy.context.scene.collection.objects.link(head)
    for m in list(head.modifiers):head.modifiers.remove(m)
    rings=neck_extension(head,True)
    head.data.materials.clear()
    for m in char.data.materials:head.data.materials.append(m)
    for f in head.data.polygons:f.material_index=2;f.use_smooth=True
    bpy.context.view_layer.objects.active=head;head.select_set(True)
    sub=head.modifiers.new('Anatomical final topology','SUBSURF');sub.levels=2;sub.render_levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
    bind(head,head_weights)
    info=json.loads((O/'mpfb_head_i04_parameters.json').read_text());eyes={}
    for label in ['L','R']:
        ob=bpy.data.objects['AstraChar2_Eyeball_'+label];p=np.array([ob.matrix_world@v.co for v in ob.data.vertices]);old=(p.min(0)+p.max(0))/2;radius=float((p.max(0)-p.min(0)).max()/2)
        which='L' if old[0]>0 else 'R';new=np.array(info['eyes'][which]['center']);scale=info['eyes'][which]['radius']/radius
        eyes[label]={'center':new.tolist(),'radius':info['eyes'][which]['radius']}
        for stem in ['Eyeball','Iris','Pupil','Cornea','TearCorner','Wetline','Lashes','Eyebrows']:
            ob=bpy.data.objects.get('AstraChar2_'+stem+'_'+label)
            if not ob:continue
            world=ob.matrix_world.copy();inv=world.inverted()
            for v in ob.data.vertices:v.co=inv@Vector(new+(np.array(world@v.co)-old)*scale)
            bind(ob,lambda p:{'Head':1});ob.hide_render=False;ob.hide_set(False)
        nostril=bpy.data.objects.get('AstraChar2_Nostril_'+label)
        if nostril:nostril.data.clear_geometry();nostril.hide_render=True
    bpy.context.view_layer.update();tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
    for label in ['L','R']:
        ob=bpy.data.objects['AstraChar2_Eyebrows_'+label];inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:
            p=ob.matrix_world@v.co;hit,n,_,_=tree.ray_cast(Vector((p.x,-1,p.z)),Vector((0,1,0)),2)
            if hit:v.co=inv@(hit+n*.00065)
    # Hold hair out for a directly comparable unobstructed clay gate; geometry untouched here.
    for ob in bpy.data.objects:
        if ob.name.startswith(('AstraChar2_R4_','AstraChar2_R2_Hair','AstraChar2_R3_Flow','AstraChar2_R3_Plait')):ob.hide_render=True
    reset_pose();error=max(float(np.abs(np.array(b.matrix_local)-rests[b.name]).max()) for b in arm.data.bones)
    assert error==0 and len(arm.data.bones)==121 and len(bpy.data.actions)==0
    assert all(mesh_digest(bpy.data.objects[n])==h for n,h in hashes.items())
    assert all([m.name if m else None for m in bpy.data.objects[n].data.materials]==s for n,s in original.items())
    report={'source':str(src),'source_sha256':sha,'head_source':'astra_character_mpfb_head_i04.blend','head_phenotype_unchanged':True,
            'banked_armor_mesh_and_weight_hashes':hashes,'banked_armor_geometry_weights_world_matrices_exact':True,
            'banked_body_all_rest_vertices_and_weights_exact':True,'banked_body_non_head_polygons_exact':True,
            'removed_obsolete_head_skin_faces':removed,'temporary_banked_neck':'Object and data retained hidden; replaced visibly by continuous MPFB neck extension.',
            'own_armor_rebuild_executed':False,'existing_object_names_and_material_slots_preserved':True,
            'neck_bridge_ring_vertices':rings,'rest_matrix_error':error,'bones':121,'actions':0,'eyes':eyes,'clay_gate':'PENDING'}
    (O/'mpfb_graft_i04.json').write_text(json.dumps(report,indent=2))
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_graft_i04.blend'))
    render_views('mpfb_graft_i04_clay',('front','side','three_quarter','collar','body'))

if __name__=='__main__':main()
