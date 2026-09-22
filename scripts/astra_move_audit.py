"""Quaternion-log, joint-head anatomy, mesh-contact and COM audit for move scenes."""
import sys,math,json
from pathlib import Path
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
name=sys.argv[sys.argv.index('--')+1]
m=json.loads((OUT/f'{name}_manifest.json').read_text());N=m['samples_end']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'models/astra_move_{name}_wip.blend'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];AW=r.matrix_world
for o in s.objects:
    if o.type in ['MESH','CURVES']:o.hide_viewport=True
names=list(r.pose.bones.keys());rows=[]
for qf in range(4,4*N+1):
    f=qf/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    rows.append({'frame':f,'bones':{n:{'q':list(r.pose.bones[n].rotation_quaternion),'wq':list((AW@r.pose.bones[n].matrix).to_quaternion()),'h':list((AW@r.pose.bones[n].matrix).translation)} for n in names}})
ints=rows[::4]
def ang(a,b):return math.degrees(math.acos(np.clip(np.dot(a,b)/max(1e-12,np.linalg.norm(a)*np.linalg.norm(b)),-1,1)))
def angular(rs,n,key='q',dt=1):
    v=[]
    for a,b in zip(rs,rs[1:]):
        q=Quaternion(b['bones'][n][key])@Quaternion(a['bones'][n][key]).inverted();q.normalize()
        if q.w<0:q.negate()
        xyz=np.array([q.x,q.y,q.z]);l=np.linalg.norm(xyz);v.append(xyz*(math.degrees(2*math.atan2(l,q.w))/l if l>1e-10 else 0)/dt)
    return np.array(v)
def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cr(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for p in pts:
        while len(lo)>1 and cr(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in pts[::-1]:
        while len(hi)>1 and cr(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]
def margin(p,poly):
    return min(((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))/max(1e-9,np.linalg.norm(np.array(b)-a)) for a,b in zip(poly,poly[1:]+poly[:1]))
peaks={};flags=[]
for n in names:
    v=angular(ints,n);speed=np.linalg.norm(v,axis=1);ac=np.linalg.norm(np.diff(v,axis=0),axis=1);sub=np.linalg.norm(angular(rows,n,dt=.25),axis=1)
    peaks[n]={'max_deg_frame':float(max(speed)),'max_deg_frame2':float(max(ac)),'quarter_max_deg_frame':float(max(sub)),'peak_frame':int(np.argmax(speed)+2)}
    for i in range(1,len(v)):
        sa,sb=speed[i-1:i+1];cos=float(np.dot(v[i-1],v[i])/(sa*sb)) if min(sa,sb)>.001 else 1
        kinds=[]
        if cos<-.5 and min(sa,sb)>.5:kinds.append('reversal')
        if sb>max(4,2.8*np.median(speed[max(0,i-3):i+4])):kinds.append('spike')
        if ac[i-1]>12:kinds.append('acceleration')
        if kinds:flags.append({'bone':n,'frame':i+2,'kinds':kinds,'speed':float(sb),'acceleration':float(ac[i-1])})
segments=[('Hips','neck',.497,.5),('Head','head_end',.081,.5)]
for side in ['Left','Right']:
    segments += [(side+'UpLeg',side+'Leg',.10,.433),(side+'Leg',side+'Foot',.0465,.433),(side+'Foot',side+'ToeBase',.0145,.5),(side+'Arm',side+'ForeArm',.028,.436),(side+'ForeArm',side+'Hand',.016,.43),(side+'Hand',side+'Hand',.006,0)]
contacts=json.loads((OUT/f'{name}_contacts.json').read_text())
anatomy=[];balance=[];length_error=0
rest={n:np.array((AW@r.data.bones[n].matrix_local).translation) for n in names}
for i,row in enumerate(ints):
    h={n:np.array(v['h']) for n,v in row['bones'].items()};j={'frame':i+1}
    for side in ['Left','Right']:
        a=h[side+'ForeArm']-h[side+'Arm'];b=h[side+'Hand']-h[side+'ForeArm'];hand=np.array(Quaternion(row['bones'][side+'Hand']['wq'])@Vector((0,1,0)))
        j[side+'_elbow']=ang(a,b);j[side+'_wrist']=ang(b,hand)
        j[side+'_knee']=ang(h[side+'Leg']-h[side+'UpLeg'],h[side+'Foot']-h[side+'Leg'])
        j[side+'_shoulder_elevation']=ang(a,h['Hips']-h['neck'])
        for a,b in [(side+'Arm',side+'ForeArm'),(side+'ForeArm',side+'Hand'),(side+'UpLeg',side+'Leg'),(side+'Leg',side+'Foot')]:length_error=max(length_error,abs(np.linalg.norm(h[b]-h[a])-np.linalg.norm(rest[b]-rest[a])))
    anatomy.append(j);com=sum((h[a]*(1-t)+h[b]*t)*w for a,b,w,t in segments)
    support=[];feet=[]
    for side in ['Left','Right']:
        if contacts['after'][i]['sole'][side]<.015 and m.get('planted',{}).get(side,[True]*N)[i]:
            feet.append(side);a=h[side+'Foot'][:2];b=h[side+'ToeBase'][:2];axis=(b-a)/np.linalg.norm(b-a);lat=np.array([-axis[1],axis[0]])
            support.extend([a-axis*.12+lat*.10,a-axis*.12-lat*.10,b+axis*.09+lat*.10,b+axis*.09-lat*.10])
    poly=hull(support) if support else []
    balance.append({'frame':i+1,'com':list(com),'feet':feet,'margin_m':margin(com[:2],poly)-.02 if poly else None})
asym={}
for part in ['Shoulder','Arm','ForeArm','Hand','UpLeg']:
    a=np.linalg.norm(angular(ints,'Left'+part),axis=1);b=np.linalg.norm(angular(ints,'Right'+part),axis=1)
    asym[part]=float(np.corrcoef(a,b)[0,1]) if min(np.std(a),np.std(b))>1e-7 else None
loop={}
if m['loop']:
    travel=np.array(m['travel']);loop['max_joint_position_error_m']=max(float(np.linalg.norm(np.array(rows[-1]['bones'][n]['h'])-rows[0]['bones'][n]['h']-travel)) for n in names)
    loop['max_local_rotation_error_deg']=max(math.degrees(Quaternion(rows[0]['bones'][n]['q']).rotation_difference(Quaternion(rows[-1]['bones'][n]['q'])).angle) for n in names)
    # Sample equal-sided finite differences on either side of the duplicate endpoint.
    loop['max_position_velocity_mismatch_m_s']=max(float(np.linalg.norm((np.array(rows[1]['bones'][n]['h'])-rows[0]['bones'][n]['h'])-(np.array(rows[-1]['bones'][n]['h'])-rows[-2]['bones'][n]['h']))*120) for n in names)
    loop['max_rotation_velocity_mismatch_deg_s']=max(float(np.linalg.norm(angular(rows,n,dt=.25)[0]-angular(rows,n,dt=.25)[-1]))*30 for n in names)
# Actual sword landmarks by rigid bind.
sw=bpy.data.objects['Godwyn_Sword'];src=np.array([p.vector[:] for p in sw.data.attributes['astra_sword_source'].data]);loc=np.array([v.co[:] for v in sw.data.vertices]);fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),loc,rcond=None)[0]
tip=sw.data.vertices[int(src[:,2].argmin())].co.copy();grip=Vector(np.array([61.2,-66.3,167,1])@fit)
blade=[]
for i in range(N):
    s.frame_set(i+1);bpy.context.view_layer.update();deform=AW@r.pose.bones['RightHand'].matrix@r.data.bones['RightHand'].matrix_local.inverted()@AW.inverted()@sw.matrix_world
    blade.append({'frame':i+1,'tip':list(deform@tip),'grip':list(deform@grip)})
tips=np.array([x['tip'] for x in blade]);sp=np.linalg.norm(np.diff(tips,axis=0),axis=1)*30
ranges={k:[min(j[k] for j in anatomy),max(j[k] for j in anatomy)] for k in anatomy[0] if k!='frame'}
cloth={n:peaks[n] for n in names if n.startswith('phys_')};cloth['moving_bones']=sum(v['max_deg_frame']>.001 for n,v in cloth.items())
cloth_lag={}
hip=angular(ints,'Hips','wq')[:,2]
for n in ['phys_robe_front_C_06','phys_cape_C_06']:
    if n not in names:continue
    v=angular(ints,n,'wq')[:,2];corr={}
    for lag in range(-10,21):
        a=hip[max(0,-lag):min(len(hip),len(hip)-lag)];b=v[max(0,lag):min(len(v),len(v)+lag)]
        if min(np.std(a),np.std(b))>1e-8:corr[str(lag)]=float(np.corrcoef(a,b)[0,1])
    cloth_lag[n]={'best_delay_frames':int(max(corr,key=corr.get)) if corr else None,'correlations':corr}
# World yaw speed is measured from quaternion logs; no antipodal artefacts.
hipvel=angular(rows,'Hips','wq',dt=.25)[:,2]*30
windows={}
for start,end in m['active']:
    path=tips[start-1:end];length=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum());chord=float(np.linalg.norm(path[-1]-path[0]));window_sp=sp[start-1:end-1]
    windows[f'{start}-{end}']={'tip_path_m':length,'chord_m':chord,'path_chord_ratio':length/max(chord,1e-9),'peak_speed_m_s':float(max(window_sp))}
support_summary={'outside_frames':[x['frame'] for x in balance if x['margin_m'] is not None and x['margin_m']<0],'airborne_frames':[x['frame'] for x in balance if x['margin_m'] is None],'minimum_margin_m':min((x['margin_m'] for x in balance if x['margin_m'] is not None),default=None)}
slip={}
for side in ['Left','Right']:
    planted=m.get('planted',{}).get(side,[True]*N);steps=[]
    for i in range(1,N):
        if planted[i-1] and planted[i]:steps.append(float(np.linalg.norm(np.array(ints[i]['bones'][side+'Foot']['h'])[:2]-ints[i-1]['bones'][side+'Foot']['h'][:2])))
    slip[side]=max(steps,default=0)
cascade={}
for n in ['Hips','Spine02','Spine01','Spine','RightShoulder','RightArm','RightForeArm','RightHand']:
    speeds=np.linalg.norm(angular(rows,n,'wq',dt=.25),axis=1);local=np.linalg.norm(angular(rows,n,dt=.25),axis=1)
    start,end=m.get('cascade_window',[1,N]);ids=[i for i in range(len(speeds)) if start<=rows[i+1]['frame']<=end]
    best=max(ids,key=lambda i:speeds[i]);lb=max(ids,key=lambda i:local[i]);cascade[n]={'world_peak_frame':rows[best+1]['frame'],'local_peak_frame':rows[lb+1]['frame']}
lean=[]
for row,bl in zip(ints,blade):
    axis=np.array(bl['tip'])-bl['grip'];axis[2]=0;axis/=max(1e-9,np.linalg.norm(axis));torso=np.array(row['bones']['neck']['h'])-row['bones']['Hips']['h'];lean.append({'frame':row['frame'],'toward_horizontal_blade_deg':math.degrees(math.atan2(float(torso@axis),torso[2]))})
result={'support_summary':support_summary,'planted_ankle_max_planar_step_m':slip,'cascade':cascade,'counterlean':lean,'cloth_yaw_lag':cloth_lag,'active_windows':windows,'name':name,'quarter_samples':len(rows),'bone_count':len(names),'peaks':peaks,'flags':flags,'joint_ranges_deg':ranges,'anatomy':anatomy,'balance':balance,'asymmetry_speed_correlation':asym,'loop':loop,'max_limb_length_error_m':length_error,'blade_peak_speed_m_s':float(max(sp)),'blade_min_z_m':float(tips[:,2].min()),'blade':blade,'cloth':cloth,'peak_hips_yaw_deg_s':float(max(abs(hipvel))),'source_sha256':m['source_sha256']}
(OUT/f'{name}_metrics.json').write_text(json.dumps(result,indent=2))
(OUT/f'{name}_samples.json').write_text(json.dumps(rows,separators=(',',':')))
print(json.dumps({k:v for k,v in result.items() if k not in ['peaks','flags','anatomy','balance','blade','cloth','counterlean']},indent=2));print('FLAGS',flags)
print('CONTACT', {stage:{side:[min(r['sole'][side] for r in contacts[stage]),max(r['sole'][side] for r in contacts[stage])] for side in ['Left','Right']} for stage in ['before','after']})
print('HEM',min(v for r in contacts['after'] for v in r['hem'].values()))
