import bpy,json,struct,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'renders/astra/v3b';blob=(O/'candidate.glb').read_bytes();n=struct.unpack_from('<I',blob,12)[0];d=json.loads(blob[20:20+n]);binary=blob[28+n:]
def accessor(i):
 a=d['accessors'][i];bv=d['bufferViews'][a['bufferView']];dtype={5126:'<f4',5121:'u1',5123:'<u2'}[a['componentType']];cols={'VEC4':4,'VEC3':3,'SCALAR':1}[a['type']];offset=bv.get('byteOffset',0)+a.get('byteOffset',0);stride=bv.get('byteStride',np.dtype(dtype).itemsize*cols);arr=np.ndarray((a['count'],cols),dtype=dtype,buffer=binary,offset=offset,strides=(stride,np.dtype(dtype).itemsize)).astype(float)
 if a.get('normalized'):arr/=255 if a['componentType']==5121 else 65535
 return arr
rows=[]
for m in d['meshes']:
 for p in m['primitives']:
  attrs=p['attributes'];ks=sorted(k for k in attrs if k.startswith('WEIGHTS_'))
  if not ks:continue
  w=np.concatenate([accessor(attrs[k]) for k in ks],axis=1);rows.append({'mesh':m['name'],'vertices':len(w),'weight_attributes':ks,'maximum_positive_influences':int((w>0).sum(1).max()),'max_sum_error':float(np.abs(w.sum(1)-1).max())})
bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_final.blend'));native={}
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 weights=[np.array([g.weight for g in v.groups]) for v in ob.data.vertices];native[ob.name]={'max_positive':max(int((w>0).sum()) for w in weights),'max_above_1e_4':max(int((w>1e-4).sum()) for w in weights),'vertices_above_8_positive':sum(int((w>0).sum()>8) for w in weights),'ninth_largest_weight_max':max((float(np.sort(w)[-9]) for w in weights if len(w)>8),default=0)}
rep={'requested_export_all_influences':True,'serialized':rows,'native':native};(O/'export_weights.json').write_text(json.dumps(rep,indent=2));print('V3B_EXPORT_WEIGHTS',json.dumps(rep),flush=True)
