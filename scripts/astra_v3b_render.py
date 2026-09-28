import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3m_render as v
O=R/'renders/astra/v3b'
blend=R/sys.argv[sys.argv.index('--blend')+1] if '--blend' in sys.argv else (O/'strict_candidate.blend' if '--strict' in sys.argv else R/'models/astra_character_v3b.blend')
folder=sys.argv[sys.argv.index('--folder')+1] if '--folder' in sys.argv else ('strict' if '--strict' in sys.argv else 'final')
bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene;rig=bpy.data.objects['Astra_V3_Rig'];head=bpy.data.objects['AstraChar2_Meshy_HeadHair'];c=v.studio(s)
# A second broad neutral back light keeps the preservation evidence readable.
l=bpy.data.lights.new('V3B_BackFill','AREA');l.energy=500;l.size=4;o=bpy.data.objects.new(l.name,l);s.collection.objects.link(o);o.location=(-3,5,4);v.aim(o,(0,0,1.7))
v.configure(s,1200,1800,64);assets=[o for o in s.objects if o.type=='MESH' and not o.name.startswith('V3M_Render')]
report=[]
for pose in (sys.argv[sys.argv.index('--poses')+1].split(',') if '--poses' in sys.argv else ['rest','stance']):
 rig.data.pose_position='REST' if pose=='rest' else 'POSE';v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);bpy.context.view_layer.update()
 low,high=v.bounds(assets);target=Vector(((low[0]+high[0])/2,(low[1]+high[1])/2,(low[2]+high[2])/2));scale=max(3.65,(high[2]-low[2])*1.13,(high[0]-low[0])*1.6)
 hl,hh=v.bounds([head]);hc=Vector((hl+hh)/2);ct=hc+Vector((0,0,-.23))
 views={'front':(target+Vector((0,-7,0)),target,scale),'side':(target+Vector((7,0,0)),target,scale),'three_quarter':(target+Vector((4.7,-6,0)),target,scale),'back':(target+Vector((0,7,0)),target,scale),'collar':(ct+Vector((1,-4,.25)),ct,.8),'collar_top45':(ct+Vector((0,-3,3)),ct,.9),'face':(hc+Vector((0,-4,0)),hc,.67)}
 if '--strict' in sys.argv or '--preview' in sys.argv:views={k:views[k] for k in ['front','back','collar_top45']}
 if '--views' in sys.argv:views={k:views[k] for k in sys.argv[sys.argv.index('--views')+1].split(',')}
 for name,(loc,t,sc) in views.items():
  path=O/folder/f'{pose}_{name}.png'
  if '--fit' in sys.argv and name in ['front','side','three_quarter','back']:
   v.set_camera(c,loc,t,sc);basis=np.array(c.rotation_euler.to_matrix());pts=[];dg=bpy.context.evaluated_depsgraph_get()
   for ob in assets:
    e=ob.evaluated_get(dg);m=e.to_mesh();pts.extend((e.matrix_world@x.co)[:] for x in m.vertices);e.to_mesh_clear()
   projected=np.array(pts)@basis;lo=projected.min(0);hi=projected.max(0);mid=(lo+hi)/2;old=np.array(t)@basis;delta=Vector(basis@np.array([mid[0]-old[0],mid[1]-old[1],0.]));loc=loc+delta;t=t+delta;sc=max(3.65,(hi[1]-lo[1])*1.13,(hi[0]-lo[0])*1.13*1.5)
  v.set_camera(c,loc,t,sc);v.render(s,path);report.append({'file':str(path.relative_to(O)),'pose':pose,'view':name,'location':list(loc),'target':list(t),'scale':float(sc)})
(O/(folder+'_render.json')).write_text(json.dumps(report,indent=2))
