import bpy,json,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'raw.blend'));ob=bpy.data.objects['V4_Body'];u=np.unique(np.array([x.uv[:] for x in ob.data.uv_layers.active.data]),axis=0);before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'models/meshy_godwyn_full.glb'));src=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');v=np.unique(np.array([x.uv[:] for x in src.data.uv_layers.active.data]),axis=0);tree=KDTree(len(v))
for i,p in enumerate(v):tree.insert((p[0],p[1],0),i)
tree.balance();dist=np.array([tree.find((p[0],p[1],0))[2] for p in u]);rep={'rigged_uv_to_nearest_source_uv_distance_pixels_2048':{'max':float(dist.max()*2048),'p99':float(np.percentile(dist,99)*2048),'median':float(np.median(dist)*2048)},'interpretation':'Near-coincident atlas coordinates support by-UV map transfer; this does not certify tangent-normal compatibility after rigging.'};(O/'uv_distance.json').write_text(json.dumps(rep,indent=2));print('V4_UV_DISTANCE',json.dumps(rep),flush=True)
