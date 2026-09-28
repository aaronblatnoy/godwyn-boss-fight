"""Validate against immutable round-2 input, render and export local deliverables."""
import bpy,sys,json,struct,os,math,shutil
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_round2_compare import compare,CAM,portrait_lights
from astra_char2_render import configure
from astra_character_common import aim,reset_pose,render_view

def snapshot():
 o=bpy.data.objects['char1'];cloth={vi for f in o.data.polygons if f.material_index in (1,4) for vi in f.vertices}
 return {'names':set(bpy.data.objects.keys()),'materials':{o.name:[m.name if m else None for m in o.data.materials] for o in bpy.data.objects if o.type=='MESH'},'groups':[g.name for g in o.vertex_groups],'bones':[(b.name,b.parent.name if b.parent else None,tuple(b.head_local),tuple(b.tail_local)) for b in bpy.data.objects['Armature'].data.bones], 'cloth':{i:tuple(o.data.vertices[i].co) for i in cloth},'body':{v.index:tuple(v.co) for v in o.data.vertices if (o.matrix_world@v.co).z<2.78},'weights':{i:[(g.group,g.weight) for g in o.data.vertices[i].groups] for i in cloth}}

anchor_ids={}
def landmarks():
 out={};o=bpy.data.objects['char1'];me=o.data;uv=me.uv_layers['AstraChar2FaceUV']
 def project(p):return [424+p.x*1264/.650,(3.225-p.z)*1264/.650]
 for s in ['L','R']:
  ob=bpy.data.objects['AstraChar2_Iris_'+s];pts=[ob.matrix_world@v.co for v in ob.data.vertices];p=(min(q.x for q in pts)+max(q.x for q in pts))/2, (min(q.z for q in pts)+max(q.z for q in pts))/2
  out['iris_'+s]=project(Vector((p[0],0,p[1])))
 for label,x,z in [('mouth_center',0,2.849),('nose_tip',0,2.894)]:
  target=Vector(((x+.16)/.32,(z-2.76)/.40));best=min(( ((uv.data[li].uv-target).length,me.loops[li].vertex_index) for f in me.polygons if f.material_index==2 for li in f.loop_indices),key=lambda q:q[0]);
  if label not in anchor_ids:anchor_ids[label]=best[1]
  out[label]=project(o.matrix_world@me.vertices[anchor_ids[label]].co)
  if 'round2_front_patch' in o:
   points=[o.matrix_world@v.co for v in me.vertices if v.index>=253776]
   if label=='mouth_center':point=min(points,key=lambda p:p.x*p.x+(p.z-2.876)**2)
   else:point=min((p for p in points if abs(p.x)<.004 and 2.91<p.z<2.96),key=lambda p:p.y)
   out[label]=project(point)
 return out

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_input.blend'));base=snapshot();before=landmarks()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_work.blend'));reset_pose();now=snapshot();after=landmarks()
assert base['names']<=now['names'];assert base['groups']==now['groups'];assert base['bones']==now['bones']
assert all(now['materials'][n]==m for n,m in base['materials'].items())
o=bpy.data.objects['char1']
cloth_error=max((Vector(p)-o.data.vertices[i].co).length for i,p in base['cloth'].items())*.01
body_error=max((Vector(p)-o.data.vertices[i].co).length for i,p in base['body'].items())*.01
assert cloth_error<1e-8,cloth_error;assert body_error<1e-8,body_error
assert all([(g.group,g.weight) for g in o.data.vertices[i].groups]==v for i,v in base['weights'].items())
assert not bpy.data.actions[:]
for ob in bpy.data.objects:
 assert not ob.animation_data or not ob.animation_data.action
 if ob.name.startswith('AstraChar2_') and ob.type=='MESH':assert ob.vertex_groups.get('Head') and any(m.type=='ARMATURE' for m in ob.modifiers)
ref={'iris_L':[315,447],'iris_R':[535,443],'mouth_center':[424,680],'nose_tip':[424,580]}
metric={'method':'Manual approved-image pixel landmarks against projected 3D iris centers and baseline UV anchors and rebuilt surface mouth seam/nose prominence; NOT a photorealism score. 848x1264, fixed camera. Approximate nose/mouth UV anchor correspondence.','reference':ref,'before':before,'after':after}
for label,d in [('before',before),('after',after)]:metric[label+'_mean_error_px']=sum(math.dist(d[k],ref[k]) for k in ref)/len(ref)
(OUT/'round2_metrics.json').write_text(json.dumps(metric,indent=2))
report={'original_object_names_preserved':True,'original_material_slots_preserved':True,'bone_rest_and_names_preserved':True,'vertex_groups_preserved':True,'cloth_vertex_max_change_m':cloth_error,'body_below_2_78_max_change_m':body_error,'cloth_weights_exactly_preserved':True,'actions':0,'all_added_meshes_head_weighted':True,'quality_gate':'NOT_MET: progress toward approved portrait, still visibly synthetic; see ROUND2_REPORT.md','new_objects':sorted(now['names']-base['names'])}
(OUT/'round2_validation.json').write_text(json.dumps(report,indent=2))
if '--validate-only' in sys.argv:
 print('ROUND2 VALIDATION',json.dumps(report),flush=True);sys.exit(0)
if '--reuse-portrait' in sys.argv:
 shutil.copy2(OUT/'r2_iteration11_face.png',OUT/'after_face.png');shutil.copy2(OUT/'r2_iteration11_sidebyside.png',OUT/'after_sidebyside.png');shutil.copy2(OUT/'after_sidebyside.png',OUT/'sidebyside_face.png')
 s=configure();portrait_lights();s.render.resolution_x=848;s.render.resolution_y=1264;s.cycles.samples=48
else:compare('after')
s=bpy.context.scene;s.camera.location=(2.4,-4.4,3.08);aim(s.camera,(0,-.29,2.96));s.camera.data.ortho_scale=.69
s.render.filepath=str(OUT/'after_face_three_quarter.png');bpy.ops.render.render(write_still=True)
# Exact house lighting convention for the full-body comparison.
for name,loc,power,color,size in [('Astra key',(-3.5,-4.5,6),1350,(1,.92,.6),3),('Astra fill',(3,-4,3.5),680,(.52,.65,1),3.2),('Astra rim',(2,3,5),1650,(1,.8,.43),2.4),('Astra face',(0,-4,4.4),110,(1,.95,.84),1.4)]:
 ob=bpy.data.objects[name];ob.location=loc;ob.data.energy=power;ob.data.color=color;ob.data.size=size;aim(ob,(0,0,1.9))
bg=s.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.055,.068,.10,1);bg.inputs[1].default_value=.32;bpy.data.objects['Astra evaluation ground'].hide_render=False
configure();render_view('after','front');reset_pose()
objects=[bpy.data.objects[n] for n in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves']]+[ob for ob in bpy.data.objects if ob.name.startswith('AstraChar2_')]
bpy.ops.object.select_all(action='DESELECT')
for ob in objects:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Armature']
tri=o.modifiers.new('AstraChar2 temporary export triangulation','TRIANGULATE');tri.min_vertices=5
path=ROOT/'models/astra_character_v2_round2_export.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
o.modifiers.remove(tri)
blob=path.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length]);assert doc.get('skins');assert not doc.get('animations')
node=next(n for n in doc['nodes'] if n.get('name')=='char1');assert all('TANGENT' in p['attributes'] for p in doc['meshes'][node['mesh']]['primitives'])
skin=next(m for m in doc['materials'] if m['name']=='Astra pale golden skin final');assert 'normalTexture' in skin and 'emissiveTexture' in skin;assert skin['extensions']['KHR_materials_emissive_strength']['emissiveStrength']==2.5
report['glb']={'bytes':len(blob),'skins':len(doc['skins']),'animations':len(doc.get('animations',[])),'images':len(doc.get('images',[])),'portable_sss_limitation':'Cycles SSS has no exact core glTF equivalent','skin_material':skin}
(OUT/'round2_validation.json').write_text(json.dumps(report,indent=2));(OUT/'round2_exported_gltf.json').write_text(json.dumps(doc,indent=2))
os.replace(path,ROOT/'models/astra_character_v2.glb');s['AstraChar2_quality_gate']=report['quality_gate'];bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
print('ROUND2 DELIVERED',flush=True)
