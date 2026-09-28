"""Export two clips and independently check geometry deformation after fresh GLB import."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'))
import astra_v3m_publish as pub
import astra_v3_build as b
import astra_v3m_render as v
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));s=bpy.context.scene;rig=bpy.data.objects['Astra_V4_Rig'];assets=[o for o in s.objects if o.type=='MESH'];clips=['Combat_Stance','sword_slash_r'];baseline=pub.rest_snapshot(rig);native_weights=pub.weight_audit(assets,rig);samples={};native={clip:{} for clip in clips};counts={}
rig.data.pose_position='REST';bpy.context.view_layer.update()
for ob in assets:
 ids=np.linspace(0,len(ob.data.vertices)-1,min(300,len(ob.data.vertices)),dtype=int);samples[ob.name]={'ids':ids,'weights':[{ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[int(i)].groups} for i in ids],'rest':np.array([(ob.matrix_world@ob.data.vertices[int(i)].co)[:] for i in ids])}
rig.data.pose_position='POSE'
for clip in clips:
 act=bpy.data.actions[clip];counts[clip]=int(act.frame_range[1]);native[clip]={ob.name:[] for ob in assets}
 for frame in range(1,counts[clip]+1):
  v.assign_action(rig,act,frame);dg=bpy.context.evaluated_depsgraph_get()
  for ob in assets:
   e=ob.evaluated_get(dg);m=e.to_mesh();native[clip][ob.name].append(np.array([(e.matrix_world@m.vertices[int(i)].co)[:] for i in samples[ob.name]['ids']]));e.to_mesh_clear()
rig.data.pose_position='REST';bpy.context.view_layer.update();v.enable_optix(s);s.cycles.samples=1;s.render.bake.margin=16;s.render.bake.use_selected_to_active=False
# Flatten the body's masked native color/roughness. Face already has baked maps.
bakes=[];ob=bpy.data.objects['V4_Body'];ob.data.uv_layers.active_index=0
for channel in ['Base Color','Roughness']:
 mat=ob.data.materials[0];nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);source=bs.inputs[channel];oldsocket=out.inputs['Surface'].links[0].from_socket;feed=source.links[0].from_socket;em=nt.nodes.new('ShaderNodeEmission');nt.links.new(feed,em.inputs['Color']);nt.links.new(em.outputs[0],out.inputs['Surface']);img=bpy.data.images.new('V4P export body '+channel,2048,2048,alpha=False);img.colorspace_settings.name='sRGB' if channel=='Base Color' else 'Non-Color'
 for material in ob.data.materials:
  tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;material.node_tree.nodes.active=tex
  if material==mat:target=tex
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.bake(type='EMIT');nt.links.new(oldsocket,out.inputs['Surface']);nt.nodes.remove(em);nt.links.new(target.outputs['Color'],source);uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map=ob.data.uv_layers[0].name;nt.links.new(uv.outputs[0],target.inputs['Vector']);path=O/('body_'+channel.replace(' ','_')+'.png');img.filepath_raw=str(path);img.file_format='PNG';img.save();img.pack();bakes.append(str(path.relative_to(O)))
# Pack the body and sword into one 4096x2048 PBR atlas, preserving the dedicated face atlas.
# This gives exactly two materials in the delivered blend and GLB.
body=bpy.data.objects['V4_Body'];sword=bpy.data.objects['Godwyn_Sword'];bm=body.data.materials[0];sm=sword.data.materials[0];bi=b.pbr_images(bm);si=b.pbr_images(sm)
def px(im):
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);return a.reshape(im.size[1],im.size[0],4)
B={k:px(im) for k,im in bi.items() if im};S={k:px(im) for k,im in si.items() if im};maps={}
for kind in ['base','orm','normal','emission','sss']:
 arr=np.ones((2048,4096,4),np.float32)
 if kind=='base':arr[:,:2048]=B['base'];arr[:,2048:]=S['base']
 elif kind=='normal':arr[:,:2048]=B['normal'];arr[:,2048:]=S['normal']
 elif kind=='orm':
  arr[:,:,:3]=1;arr[:,:2048,1]=B['roughness'][:,:,0];arr[:,:2048,2]=B['metallic'][:,:,2];arr[:,2048:,1]=S['roughness'][:,:,1];arr[:,2048:,2]=S['metallic'][:,:,2]
 elif kind=='emission':arr[:,:,:3]=0;arr[:,:2048,:3]=B['emission'][:,:,:3]
 else:arr[:,:,:3]=0;arr[:,:2048,:3]=px(bpy.data.images['V4 skin_mask'])[:,:,:3]*.32
 im=bpy.data.images.new('V4P_BodySword_'+kind,4096,2048,alpha=False);im.colorspace_settings.name='sRGB' if kind in ['base','emission'] else 'Non-Color';im.pixels.foreach_set(arr.ravel());im.filepath_raw=str(O/(im.name+'.png'));im.file_format='PNG';im.save();im.pack();maps[kind]=im
mat=bpy.data.materials.new('V4_BodySword');mat.use_nodes=True;nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='UVMap';nodes={}
for kind,im in maps.items():
 n=nt.nodes.new('ShaderNodeTexImage');n.image=im;nt.links.new(uv.outputs[0],n.inputs['Vector']);nodes[kind]=n
nt.links.new(nodes['base'].outputs['Color'],bs.inputs['Base Color']);split=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(nodes['orm'].outputs['Color'],split.inputs[0]);nt.links.new(split.outputs['Green'],bs.inputs['Roughness']);nt.links.new(split.outputs['Blue'],bs.inputs['Metallic']);nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='UVMap';nt.links.new(nodes['normal'].outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal']);nt.links.new(nodes['emission'].outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=next(n for n in bm.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Emission Strength'].default_value;nt.links.new(nodes['sss'].outputs['Color'],bs.inputs['Subsurface Weight']);bs.inputs['Subsurface Radius'].default_value=(1,.35,.2);bs.inputs['Subsurface Scale'].default_value=.008
body.data.materials[0]=mat;sword.data.materials.clear();sword.data.materials.append(mat)
for obj,offset in [(body,0),(sword,.5)]:
 obj.data.uv_layers[0].name='UVMap'
 for d in obj.data.uv_layers[0].data:d.uv.x=d.uv.x*.5+offset
# Atlas preserves pixel density: original 2048-wide maps occupy 2048 pixels each.
rig.data.pose_position='POSE';v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);s.render.fps=30;s.frame_start=1;s.frame_end=51;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate_export.blend'));bpy.ops.object.select_all(action='DESELECT')
for ob in assets+[rig]:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=rig
opts=dict(filepath=str(O/'candidate.glb'),export_format='GLB',use_selection=True,export_apply=True,export_skins=True,export_def_bones=False,export_leaf_bone=False,export_texcoords=True,export_normals=True,export_tangents=True,export_materials='EXPORT',export_cameras=False,export_lights=False,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_bake_animation=True,export_optimize_animation_size=False,export_all_influences=True,export_influence_nb=12)
# Blender 5.2 drops weights <= 1e-4 even with all-influence export. Retain them
# for this export only; never modify the installed exporter or native skin weights.
import inspect,textwrap
from io_scene_gltf2.blender.exp import primitive_extract as pe
original_get=pe.PrimitiveCreator._PrimitiveCreator__get_bone_data
code=textwrap.dedent(inspect.getsource(original_get));assert 'min_influence = 0.0001' in code
code=code.replace('def __get_bone_data(self):','def v4p_get_bone_data(self):').replace('min_influence = 0.0001','min_influence = 0.0');exec(compile(code,'<V4P preserve tiny skin weights>','exec'),pe.__dict__);pe.PrimitiveCreator._PrimitiveCreator__get_bone_data=pe.v4p_get_bone_data
valid=set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
try:bpy.ops.export_scene.gltf(**{k:x for k,x in opts.items() if k in valid})
finally:pe.PrimitiveCreator._PrimitiveCreator__get_bone_data=original_get
doc=pub.glb_json(O/'candidate.glb');jointcounts=[len(x['joints']) for x in doc['skins']];assert all(x==24 for x in jointcounts);assert set(x['name'] for x in doc['animations'])==set(clips)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'candidate.glb'));rigs=[o for o in s.objects if o.type=='ARMATURE'];assert len(rigs)==1;rig=rigs[0];rig.name='Astra_V4_Rig';assert set(rig.data.bones.keys())==set(baseline);hierarchy=all((b.parent.name if b.parent else None)==baseline[b.name]['parent'] for b in rig.data.bones);resterror=max(float(np.max(np.abs(np.array(rig.matrix_world@b.head_local)-baseline[b.name]['head_world_m']))) for b in rig.data.bones);rig.data.pose_position='REST';bpy.context.view_layer.update();mapping={};mappingerror=0
for name,info in samples.items():
 ob=bpy.data.objects[name];tree=KDTree(len(ob.data.vertices))
 for vert in ob.data.vertices:tree.insert(ob.matrix_world@vert.co,vert.index)
 tree.balance();found=[]
 for x,expected_weights in zip(info['rest'],info['weights']):
  choices=tree.find_range(Vector(x),.00002) or [tree.find(Vector(x))]
  def score(hit):
   weights={ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[hit[1]].groups};return sum((weights.get(n,0)-expected_weights.get(n,0))**2 for n in set(weights)|set(expected_weights)),hit[2]
  found.append(min(choices,key=score))
 mapping[name]=[x[1] for x in found];mappingerror=max(mappingerror,max(x[2] for x in found))
rig.data.pose_position='POSE';errors={clip:{name:0. for name in samples} for clip in clips}
for clip in clips:
 for frame in range(1,counts[clip]+1):
  v.assign_action(rig,bpy.data.actions[clip],frame);dg=bpy.context.evaluated_depsgraph_get()
  for name,ids in mapping.items():
   ob=bpy.data.objects[name];e=ob.evaluated_get(dg);m=e.to_mesh();pts=np.array([(e.matrix_world@m.vertices[i].co)[:] for i in ids]);e.to_mesh_clear();errors[clip][name]=max(errors[clip][name],float(np.linalg.norm(pts-native[clip][name][frame-1],axis=1).max()))
weights=pub.weight_audit(list(s.objects),rig);actualcounts=pub.action_counts();rep={'exporter_tiny_weight_threshold':0.0,'mapping':'nearest rest position within 20 micrometers, then closest bone-weight vector to disambiguate coincident split vertices','bones':len(rig.data.bones),'hierarchy_preserved':hierarchy,'joint_rest_error_m':resterror,'animation_frames':actualcounts,'fps':30,'gltf_skin_joint_counts':jointcounts,'native_weights':native_weights,'imported_weights':weights,'rest_sample_matching_error_m':mappingerror,'sampled_deformation_max_error_m':errors,'deformation_samples_per_mesh':300,'frames_compared':sum(counts.values()),'material_bakes':bakes,'gltf_materials':[x.get('name') for x in doc['materials']],'body_materials':[m.name for m in bpy.data.objects['V4_Body'].data.materials],'material_limit':'Native skin_i01 subsurface has no exact core glTF equivalent. Exactly two materials: V4_BodySword (4096x2048 body/sword atlas) and V4_Face (2048x2048).' ,'export_sha256':pub.sha256(O/'candidate.glb')};rep['mechanical_pass']=hierarchy and resterror<.00005 and mappingerror<.00005 and max(x for e in errors.values() for x in e.values())<.0001 and weights['unweighted_or_bad_sum_vertices']==0 and actualcounts==counts and len(rep['body_materials'])==2 and len(rep['gltf_materials'])==2
(O/'roundtrip.json').write_text(json.dumps(rep,indent=2));v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);bpy.ops.wm.save_as_mainfile(filepath=str(O/'roundtrip.blend'));print('V4P_ROUNDTRIP',json.dumps(rep),flush=True)
