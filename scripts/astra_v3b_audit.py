import bpy,sys,json,numpy as np
from pathlib import Path
from collections import defaultdict
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3m_audit as a
import astra_v3m_publish as pub
O=R/'renders/astra/v3b';strict='--strict' in sys.argv
blend=R/sys.argv[sys.argv.index('--blend')+1] if '--blend' in sys.argv else (O/'strict_candidate.blend' if strict else R/'models/astra_character_v3b.blend')
bpy.ops.wm.open_mainfile(filepath=str(blend))
rig=bpy.data.objects['Astra_V3_Rig'];body=bpy.data.objects['char1'];head=bpy.data.objects['AstraChar2_Meshy_HeadHair'];sword=bpy.data.objects['Godwyn_Sword'];act=bpy.data.actions['Combat_Stance']
rest,exterior,skin,hair,bladeids,blade=a.face_sets(body,head,sword);edges,lengths,valid=a.body_edge_data(body,rest);soles=a.sole_ids(body)
# Wider collar/shoulder population also reported, so inherited central-interior exclusion cannot hide a failed graft.
collar=[]
for f in body.data.polygons:
 c=rest[list(f.vertices)].mean(0)
 if 2.43<c[2]<2.87 and abs(c[0])<.82 and -.65<c[1]<.28:collar.append(tuple(f.vertices))
coincident=defaultdict(list)
for i,p in enumerate(rest):coincident[tuple(np.round(p,6))].append(i)
pairs=np.array([(ids[0],i) for ids in coincident.values() for i in ids[1:]],dtype=int)
rows=[]
for frame in range(1,52):
 a.assign(rig,act,frame);bp,_=a.evaluated(body);hp,_=a.evaluated(head)
 ratios=np.linalg.norm(bp[edges[:,0]]-bp[edges[:,1]],axis=1)[valid]/lengths[valid]
 foot={side:float(bp[ids,2].min()) for side,ids in soles.items()}
 ht=a.tree(hp,skin+hair);allpairs=a.tree(bp,collar).overlap(ht);extpairs=a.tree(bp,exterior).overlap(ht) if exterior else []
 seam=np.linalg.norm(bp[pairs[:,0]]-bp[pairs[:,1]],axis=1) if len(pairs) else np.zeros(1)
 rows.append({'frame':frame,'p99':float(np.percentile(ratios,99)),'sole':foot,'full_collar_head_pairs':len(allpairs),'exterior_head_pairs':len(extpairs),'duplicate_seam_max_m':float(seam.max()),'duplicate_seams_over_1mm':int((seam>.001).sum())})
 if frame%10==0:print('V3B_AUDIT_FRAME',frame,rows[-1],flush=True)
rep={'rows':rows,'stretch_p99_max':max(x['p99'] for x in rows),'stretch_gate':2.2,'sole_min_m':min(min(x['sole'].values()) for x in rows),'closest_sole_max_m':max(min(x['sole'].values()) for x in rows),'frames_within_5mm':sum(abs(min(x['sole'].values()))<=.005 for x in rows),'full_collar_head_pairs_max':max(x['full_collar_head_pairs'] for x in rows),'inherited_exterior_head_pairs_max':max(x['exterior_head_pairs'] for x in rows),'full_collar_population':len(collar),'inherited_exterior_population':len(exterior),'coincident_rest_pairs':len(pairs),'posed_seam_max_m':max(x['duplicate_seam_max_m'] for x in rows),'weights':pub.weight_audit([x for x in bpy.context.scene.objects if x.type=='MESH'],rig),'note':'Full population includes intentional buried neck contact and any surviving old head. Exterior uses inherited Round-2 exclusion; visual review is mandatory.'}
(O/(sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else ('strict_audit.json' if strict else 'audit.json'))).write_text(json.dumps(rep,indent=2));print('V3B_AUDIT',json.dumps({k:v for k,v in rep.items() if k!='rows'}),flush=True)
