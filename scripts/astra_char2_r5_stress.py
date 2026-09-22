"""Shipped stress-pose check on rebuilt structure, clay stills only. No saves."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose,aim
from astra_char2_render import configure
from astra_xslash_v2_poses import apply_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r5_clay.blend'));reset_pose();s=configure();s.cycles.samples=32;s.render.resolution_x=1080;s.render.resolution_y=1080
for ob in list(bpy.data.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True)
m=bpy.data.materials.new('R5 stress plain diffuse');m.use_nodes=True;m.node_tree.nodes.clear();out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');d=m.node_tree.nodes.new('ShaderNodeBsdfDiffuse');d.inputs[0].default_value=(.4,.4,.4,1);m.node_tree.links.new(d.outputs[0],out.inputs[0]);s.view_layers[0].material_override=m
for label,loc,power,size in [('key',(-3,-4.5,5),650,2.6),('fill',(3,-3,4),150,3),('rim',(1,2,4.5),850,2)]:
 d=bpy.data.lights.new('R5 stress '+label,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;aim(o,(0,0,2.4))
arm=bpy.data.objects['Armature'];obs=[o for o in bpy.data.objects if o.name.startswith(('AstraChar2_R5_Head','AstraChar2_R5_Gorget','AstraChar2_R5_Pauldron_','AstraChar2_R5_Cuirass'))]
def vertices(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());a=np.empty(len(ev.data.vertices)*3,np.float32);ev.data.vertices.foreach_get('co',a);return a.reshape(-1,3)
rest={o.name:vertices(o) for o in obs};edges={o.name:np.array([e.vertices[:] for e in o.data.edges]) for o in obs};r={}
for label in ['windup','cross','follow']:
 reset_pose();apply_pose(arm,label);bpy.context.view_layer.update();r[label]={}
 for o in obs:
  e=edges[o.name];a=rest[o.name];b=vertices(o);before=np.linalg.norm(a[e[:,0]]-a[e[:,1]],axis=1);after=np.linalg.norm(b[e[:,0]]-b[e[:,1]],axis=1);ratio=after[before>.001]/before[before>.001];r[label][o.name]={'edge_stretch_max':float(ratio.max()),'edge_stretch_p99':float(np.quantile(ratio,.99))}
 target=arm.matrix_world@arm.pose.bones['Spine'].head;s.camera.location=target+Vector((.5,-4,.30));aim(s.camera,target);s.camera.data.type='ORTHO';s.camera.data.ortho_scale=1.35;s.render.filepath=str(O/('r5_clay_stress_'+label+'.png'));bpy.ops.render.render(write_still=True)
reset_pose();r['actions_after']=len(bpy.data.actions);r['neutral_restored']=all(np.allclose(np.array(b.matrix_basis),np.eye(4),atol=1e-6) for b in arm.pose.bones);assert r['actions_after']==0 and r['neutral_restored'];(O/'r5_stress.json').write_text(json.dumps(r,indent=2));print('STRUCTURAL STRESS COMPLETE',flush=True)
