"""Read-only action/rig audit. Writes only the scoped naturalness evidence."""
import bpy, sys, math, json, hashlib, re
from pathlib import Path
from collections import Counter
from mathutils import Vector, Quaternion
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
source = Path(args[0]) if args else ROOT/'models/astra_xslash_v2_final_wip.blend'
label = args[1] if len(args)>1 else 'before'
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
r = next(o for o in s.objects if o.type=='ARMATURE')
act = r.animation_data.action
fcs = [fc for la in act.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves]
AW = r.matrix_world.copy()
def arr(v): return [float(x) for x in v]
def allprops(obj):
    d={}
    for prop in obj.bl_rna.properties:
        if prop.identifier in ['rna_type'] or prop.type in ['POINTER','COLLECTION']:continue
        try:
            v=getattr(obj,prop.identifier)
            d[prop.identifier]=list(v) if getattr(prop,'is_array',False) else v
        except Exception:pass
    return d

def invariants():
    h=hashlib.sha256()
    for o in sorted(s.objects,key=lambda o:o.name):
        if o.type=='MESH':
            h.update(o.name.encode())
            for v in o.data.vertices: h.update(str((tuple(v.co),[(g.group,g.weight) for g in v.groups])).encode())
            for p in o.data.polygons:h.update(str(tuple(p.vertices)).encode())
    return {'mesh_vertices_topology_weights_sha256':h.hexdigest(),
       'objects':{o.name:{'type':o.type,'matrix':list(map(list,o.matrix_world)),'parent':o.parent.name if o.parent else None,'constraints':[str(c) for c in o.constraints]} for o in s.objects},
       'cameras':{o.name:allprops(o.data) for o in s.objects if o.type=='CAMERA'},
       'lights':{o.name:allprops(o.data) for o in s.objects if o.type=='LIGHT'},
       'render':allprops(s.render),'eevee':allprops(s.eevee),'image_settings':allprops(s.render.image_settings),
       'view_settings':allprops(s.view_settings),'world':allprops(s.world),
       'materials':{m.name:{'props':allprops(m),'nodes':[(n.name,allprops(n),[(i.identifier,repr(i.default_value)) for i in n.inputs if hasattr(i,'default_value')]) for n in m.node_tree.nodes] if m.node_tree else [],'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in m.node_tree.links] if m.node_tree else []} for m in bpy.data.materials},
       'rest':{b.name:{'matrix':list(map(list,b.matrix_local)),'parent':b.parent.name if b.parent else None} for b in r.data.bones}}
s.frame_set(1)
bpy.context.view_layer.update()
inv=invariants()
rest={b.name:{'head':arr(AW@b.head_local),'tail':arr(AW@b.tail_local),'parent':b.parent.name if b.parent else None,'matrix':list(map(list,AW@b.matrix_local))} for b in r.data.bones}
# Hide meshes for the bone-only sampling. Never save this state.
for o in s.objects:
    if o.type=='MESH':o.hide_viewport=True
rows=[]
for qf in range(4,361):
    f=qf/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    rows.append({'f':f,'bones':{p.name:{'q':arr(p.rotation_quaternion),'loc':arr(p.location),'head':arr(AW@p.matrix.translation),'world_q':arr((AW@p.matrix).to_quaternion())} for p in r.pose.bones}})
curves=[]
for fc in fcs:
    curves.append({'path':fc.data_path,'index':fc.array_index,'keys':len(fc.keyframe_points),
       'interpolation':dict(Counter(k.interpolation for k in fc.keyframe_points)),
       'max_gap':max((b.co.x-a.co.x for a,b in zip(fc.keyframe_points, list(fc.keyframe_points)[1:])),default=0),
       'values':[fc.evaluate(f) for f in range(1,91)],
       'derivatives':[(fc.evaluate(f+.01)-fc.evaluate(f-.01))/.02 for f in range(1,91)]})
report={'source':str(source),'version':bpy.app.version_string,'action':act.name,'bone_count':len(r.pose.bones),'curves':curves,'rest':rest,'rows':rows,'invariants':inv}
out=ROOT/f'renders/astra/naturalness_{label}.json'
out.write_text(json.dumps(report,separators=(',',':')))
print('AUDIT',out, 'bones',len(rest),'curves',len(fcs),'samples',len(rows),flush=True)
print('SETTINGS',json.dumps({k:inv[k] for k in ['cameras','render','eevee']}),flush=True)
print('BONES',json.dumps({n:rest[n] for n in rest if not n.startswith('phys_')}),flush=True)
