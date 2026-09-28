"""Read-only inventory. No blend is ever saved."""
import bpy, json, sys, hashlib, os
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'renders/astra/armaudit'
OUT.mkdir(parents=True, exist_ok=True)
targets = {'xslash':'astra_xslash_v2_final_wip.blend', **{n:f'astra_move_{n}_wip.blend' for n in ['idle_guard','lunge_thrust','walk_stalk']}}
result = {'session_id':os.environ.get('CODEX_THREAD_ID'), 'targets':{}, 'missing':[]}
for name, filename in targets.items():
    path = ROOT/'models'/filename
    if not path.exists():
        result['missing'].append(str(path)); continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    s = bpy.context.scene
    r = next(o for o in s.objects if o.type=='ARMATURE')
    a = r.animation_data.action
    s.frame_set(s.frame_start)
    d = {'path':str(path), 'sha256':digest, 'size':path.stat().st_size, 'mtime_ns':path.stat().st_mtime_ns, 'blender':bpy.app.version_string, 'scene_range':[s.frame_start,s.frame_end], 'action_range':list(a.frame_range), 'fps':s.render.fps/s.render.fps_base, 'action':a.name, 'armature':r.name, 'engine':s.render.engine,
         'bones':{b.name:{'parent':b.parent.name if b.parent else None,'head':list(r.matrix_world@b.head_local),'tail':list(r.matrix_world@b.tail_local),'matrix':list(map(list,r.matrix_world@b.matrix_local)),'constraints':[str(c) for c in r.pose.bones[b.name].constraints]} for b in r.data.bones},
         'objects':{o.name:{'type':o.type,'parent':o.parent.name if o.parent else None,'parent_type':o.parent_type,'parent_bone':o.parent_bone,'dimensions':list(o.dimensions),'location':list(o.matrix_world.translation),'vertices':len(o.data.vertices) if o.type=='MESH' else None,'modifiers':[(m.name,m.type) for m in o.modifiers], 'constraints':[str(c) for c in o.constraints]} for o in s.objects}}
    result['targets'][name]=d
    print('INVENTORY',name,json.dumps({k:v for k,v in d.items() if k!='bones'}),flush=True)
    print('ARM BONES',json.dumps({k:v for k,v in d['bones'].items() if any(x in k for x in ['RightShoulder','RightArm','RightForeArm','RightHand','RightHandIndex1','RightHandPinky1'])}),flush=True)
(OUT/'inventory.json').write_text(json.dumps(result,indent=2))
