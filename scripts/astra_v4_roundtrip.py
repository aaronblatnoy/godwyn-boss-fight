"""Candidate-only export and independent round-trip. Never publishes models."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3m_publish as pub
import astra_v3m_render as v
O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));s=bpy.context.scene;rig=bpy.data.objects['Astra_V4_Rig'];assets=[o for o in s.objects if o.type=='MESH'];action=bpy.data.actions['Combat_Stance'];baseline=pub.rest_snapshot(rig);native_weights=pub.weight_audit(assets,rig)
# Sample actual deformed geometry, so orientation changes in importer bone display
# cannot hide an animation or skinning regression.
samples={};native={};rig.data.pose_position='REST';bpy.context.view_layer.update()
for ob in assets:
 ids=np.linspace(0,len(ob.data.vertices)-1,min(160,len(ob.data.vertices)),dtype=int);samples[ob.name]={'ids':ids,'rest':np.array([(ob.matrix_world@ob.data.vertices[int(i)].co)[:] for i in ids])};native[ob.name]=[]
rig.data.pose_position='POSE'
for frame in range(1,52):
 v.assign_action(rig,action,frame);dg=bpy.context.evaluated_depsgraph_get()
 for ob in assets:
  e=ob.evaluated_get(dg);m=e.to_mesh();native[ob.name].append(np.array([(e.matrix_world@m.vertices[int(i)].co)[:] for i in samples[ob.name]['ids']]));e.to_mesh_clear()
rig.data.pose_position='REST';bpy.context.view_layer.update();v.enable_optix(s);s.cycles.samples=1;s.render.bake.margin=12;s.render.bake.use_selected_to_active=False
bakes=[]
for objname,channel in [('V4_Body','Base Color'),('V4_Body','Roughness')]:
 ob=bpy.data.objects[objname];mat=ob.data.materials[0];nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);source=bs.inputs[channel];assert source.is_linked
 oldsocket=out.inputs['Surface'].links[0].from_socket;feed=source.links[0].from_socket;em=nt.nodes.new('ShaderNodeEmission');nt.links.new(feed,em.inputs['Color']);nt.links.new(em.outputs[0],out.inputs['Surface'])
 img=bpy.data.images.new('V4 export '+objname+' '+channel,2048,2048,alpha=False);img.colorspace_settings.name='sRGB' if channel=='Base Color' else 'Non-Color';tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img;nt.nodes.active=tex
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.bake(type='EMIT');nt.links.new(oldsocket,out.inputs['Surface']);nt.nodes.remove(em);nt.links.new(tex.outputs['Color'],source)
 path=O/('bake_'+objname+'_'+channel.replace(' ','_')+'.png');img.filepath_raw=str(path);img.file_format='PNG';img.save();img.pack();bakes.append(str(path.relative_to(O)));print('V4_BAKE',path,flush=True)
rig.data.pose_position='POSE';v.assign_action(rig,action,1);s.render.fps=30;s.frame_start=1;s.frame_end=51
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate_export.blend'))
bpy.ops.object.select_all(action='DESELECT')
for ob in assets+[rig]:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig
opts=dict(filepath=str(O/'candidate.glb'),export_format='GLB',use_selection=True,export_apply=True,export_skins=True,export_def_bones=False,export_leaf_bone=False,export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=True,export_force_sampling=True,export_bake_animation=True,export_optimize_animation_size=False,export_all_influences=True,export_influence_nb=12)
valid=set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys());bpy.ops.export_scene.gltf(**{k:x for k,x in opts.items() if k in valid})
doc=pub.glb_json(O/'candidate.glb');jointcounts=[len(x['joints']) for x in doc['skins']];assert all(x==24 for x in jointcounts);assert [x['name'] for x in doc['animations']]==['Combat_Stance']
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'candidate.glb'));rigs=[o for o in s.objects if o.type=='ARMATURE'];assert len(rigs)==1;rig=rigs[0];rig.name='Astra_V4_Rig';action=bpy.data.actions['Combat_Stance'];assert set(rig.data.bones.keys())==set(baseline)
hierarchy=all((b.parent.name if b.parent else None)==baseline[b.name]['parent'] for b in rig.data.bones);resterror=max(float(np.max(np.abs(np.array(rig.matrix_world@b.head_local)-baseline[b.name]['head_world_m']))) for b in rig.data.bones)
rig.data.pose_position='REST';bpy.context.view_layer.update();mapping={};mappingerror=0
for name,info in samples.items():
 ob=bpy.data.objects[name];tree=KDTree(len(ob.data.vertices))
 for vert in ob.data.vertices:tree.insert(ob.matrix_world@vert.co,vert.index)
 tree.balance();found=[tree.find(Vector(x)) for x in info['rest']];mapping[name]=[x[1] for x in found];mappingerror=max(mappingerror,max(x[2] for x in found))
rig.data.pose_position='POSE';errors={n:0. for n in samples}
for frame in range(1,52):
 v.assign_action(rig,action,frame);dg=bpy.context.evaluated_depsgraph_get()
 for name,ids in mapping.items():
  ob=bpy.data.objects[name];e=ob.evaluated_get(dg);m=e.to_mesh();pts=np.array([(e.matrix_world@m.vertices[i].co)[:] for i in ids]);e.to_mesh_clear();errors[name]=max(errors[name],float(np.linalg.norm(pts-native[name][frame-1],axis=1).max()))
weights=pub.weight_audit(list(s.objects),rig);counts=pub.action_counts();rep={'candidate_only':True,'bones':len(rig.data.bones),'hierarchy_preserved':hierarchy,'joint_rest_error_m':resterror,'animation_frames':counts,'fps':30,'gltf_skin_joint_counts':jointcounts,'native_weights':native_weights,'imported_weights':weights,'export_all_influences_requested':True,'rest_sample_matching_error_m':mappingerror,'sampled_deformation_max_error_m':errors,'deformation_samples_per_mesh':160,'frames_compared':51,'material_bakes':bakes,'material_limit':'Native skin_i01 subsurface scattering has no exact core glTF equivalent; GLB skin is an approximation.','export_sha256':pub.sha256(O/'candidate.glb')}
rep['mechanical_pass']=hierarchy and resterror<.00005 and mappingerror<.00005 and max(errors.values())<.0001 and weights['unweighted_or_bad_sum_vertices']==0 and counts=={'Combat_Stance':51}
(O/'roundtrip.json').write_text(json.dumps(rep,indent=2));v.assign_action(rig,action,1);bpy.ops.wm.save_as_mainfile(filepath=str(O/'roundtrip.blend'));print('V4_ROUNDTRIP',json.dumps(rep),flush=True)
