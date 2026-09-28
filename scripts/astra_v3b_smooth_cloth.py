"""Smooth lower-robe skin weights over mesh adjacency; preserve every source coordinate/face."""
import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(R/sys.argv[sys.argv.index('--source')+1] if '--source' in sys.argv else O/'candidate_r3.blend'));ob=bpy.data.objects['char1'];p=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);_,representative,canonical=np.unique(np.round(p,6),axis=0,return_index=True,return_inverse=True);q=p[representative]
f=np.array([list(f.vertices) for f in ob.data.polygons]);ff=canonical[f];e=np.sort(np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]),axis=1);e=np.unique(e,axis=0);e=e[e[:,0]!=e[:,1]]
attr=ob.data.color_attributes['astra_v3_cloth_mask'];cloth=np.array([sum(attr.data[i].color[0] for i in f.loop_indices)>1.5 for f in ob.data.polygons]);core=np.zeros(len(q),bool);core[np.unique(ff[cloth])]=True;core&=q[:,2]<1.65
membership=core.astype(float);expanded=core.copy()
for step in range(1,5):
 new=expanded.copy();new[e[expanded[e[:,0]],1]]=True;new[e[expanded[e[:,1]],0]]=True;new&=q[:,2]<1.65;membership[new&~expanded]=(5-step)/5;expanded=new
membership*=np.clip((1.65-q[:,2])/.12,0,1)
w=np.zeros((len(q),len(ob.vertex_groups)),float)
for j,i in enumerate(representative):
 for g in ob.data.vertices[i].groups:w[j,g.group]=g.weight
original=w.copy();ed=e[(membership[e[:,0]]>0)|(membership[e[:,1]]>0)];dest=np.concatenate([ed[:,0],ed[:,1]]);src=np.concatenate([ed[:,1],ed[:,0]]);counts=np.bincount(dest,minlength=len(q));safe=np.maximum(counts,1);strength=.75*membership
for iteration in range(100):
 neighbor=np.zeros_like(w)
 for j in range(w.shape[1]):neighbor[:,j]=np.bincount(dest,weights=w[src,j],minlength=len(q))/safe
 w=w*(1-strength[:,None])+neighbor*strength[:,None];w/=np.maximum(w.sum(1),1e-15)[:,None]
 if iteration%25==0:print('V3B_CLOTH_SMOOTH',iteration,flush=True)
diff=np.max(np.abs(w-original),axis=1);changed=np.where(diff[canonical]>1e-6)[0]
for group in ob.vertex_groups:group.remove(changed.tolist())
for j in range(w.shape[1]):
 for i in changed:
  value=w[canonical[i],j]
  if value>1e-8:ob.vertex_groups[j].add([int(i)],float(value),'REPLACE')
rep={'method':'100 iterations of .75 Laplacian skin-weight smoothing over geometric mesh adjacency; blue lower-robe core plus four tapered adjacent rings; no coordinate, face, UV, bone, action or object-transform edits','selected_canonical_vertices':int((membership>0).sum()),'changed_mesh_vertices':len(changed),'maximum_weight_delta':float(diff.max()),'faces':len(f),'rest_positions_exact':bool(np.array_equal(p,np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices])))}
(O/'cloth_smooth.json').write_text(json.dumps(rep,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else O/'candidate_r4.blend'));print('V3B_CLOTH_RESULT',json.dumps(rep),flush=True)
