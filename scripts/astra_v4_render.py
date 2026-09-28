import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3m_render as v
assert R==Path('/home/aaron/godwyn-boss-fight')
O=R/'renders/astra/v4';mode=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v3.blend' if mode=='v3face' else O/('raw.blend' if mode=='raw' else 'roundtrip.blend' if mode=='roundtrip' else 'candidate.blend')))
s=bpy.context.scene;rig=next(o for o in s.objects if o.type=='ARMATURE');body=bpy.data.objects.get('V4_Body');assets=[o for o in s.objects if o.type=='MESH'];c=v.studio(s)
l=bpy.data.lights.new('V4_BackFill','AREA');l.energy=500;l.size=4;o=bpy.data.objects.new(l.name,l);s.collection.objects.link(o);o.location=(-3,5,4);v.aim(o,(0,0,1.7))
v.configure(s,1200,1800,48)
if mode=='raw':s.render.engine='BLENDER_EEVEE';s.render.resolution_percentage=66
if mode=='film':
 v.OUT=O/'film';rep=v.film(s,c,rig,assets,'Combat_Stance',20,1);(O/'film_settings.json').write_text(json.dumps(rep,indent=2));sys.exit(0)
poses=['rest'] if mode in ['raw','v3face'] else ['stance'] if mode=='roundtrip' else ['rest','stance'];report=[]
for pose in poses:
 if mode!='raw':v.assign_action(rig,bpy.data.actions['Combat_Stance'],1)
 rig.data.pose_position='REST' if pose=='rest' else 'POSE';bpy.context.view_layer.update()
 lo,hi=v.bounds(assets);target=Vector((lo+hi)/2)
 # Closeups follow the evaluated head bone; targets are measured in the raw full-body mesh.
 H=rig.matrix_world@(rig.data.bones['Head'].matrix_local if pose=='rest' else rig.pose.bones['Head'].matrix);head=H.translation;hc=head+Vector((0,-.045,.08));ct=head+Vector((0,-.025,-.135))
 if mode=='v3face':
  hl,hh=v.bounds([bpy.data.objects['AstraChar2_Meshy_HeadHair']]);hc=Vector((hl+hh)/2)
 views={'front':(Vector((0,-7,0)),target,3.8),'side':(Vector((7,0,0)),target,3.8),'three_quarter':(Vector((4.7,-6,0)),target,3.8),'back':(Vector((0,7,0)),target,3.8),'face':(Vector((0,-4,0)),hc,.65),'collar':(Vector((.8,-4,.2)),ct,.65),'collar_top45':(Vector((0,-3,3)),ct,.8)}
 names=['front','side','back','face'] if mode=='raw' else ['face'] if mode=='v3face' else ['front','collar_top45'] if mode=='roundtrip' else list(views)
 if '--views' in sys.argv:names=sys.argv[sys.argv.index('--views')+1].split(',')
 for name in names:
  offset,t,scale=views[name];loc=t+offset;v.set_camera(c,loc,t,scale)
  if name in ['front','side','three_quarter','back']:
   basis=np.array(c.rotation_euler.to_matrix());pts=[];dg=bpy.context.evaluated_depsgraph_get()
   for ob in assets:
    e=ob.evaluated_get(dg);m=e.to_mesh();pts.extend((e.matrix_world@x.co)[:] for x in m.vertices);e.to_mesh_clear()
   projected=np.array(pts)@basis;low=projected.min(0);high=projected.max(0);mid=(low+high)/2;old=np.array(t)@basis;delta=Vector(basis@np.array([mid[0]-old[0],mid[1]-old[1],0.]));loc+=delta;t=t+delta;scale=max((high[1]-low[1])*1.13,(high[0]-low[0])*1.13*1.5)
  v.set_camera(c,loc,t,scale);path=O/mode/f'{pose}_{name}.png';v.render(s,path);report.append({'file':str(path.relative_to(O)),'engine':s.render.engine,'pose':pose,'view':name})
(O/(mode+'_renders.json')).write_text(json.dumps(report,indent=2))
