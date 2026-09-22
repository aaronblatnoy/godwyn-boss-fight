"""One-frame sampled groom-clearance search for rising-spin correction."""
import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/astra_move_rising_spin_v2_wip.blend"
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
s = bpy.context.scene
r = bpy.data.objects["Armature"]
sw = bpy.data.objects["Godwyn_Sword"]
AW = r.matrix_world.copy(); AI = AW.inverted()
controls = [o for o in s.objects if o.name.startswith("AstraChar2_R5_Control_MPFB_")]
samples = []
for obj in controls:
    names = {g.index: g.name for g in obj.vertex_groups}
    stride = max(1, len(obj.data.vertices) // 2500)
    for index in range(0, len(obj.data.vertices), stride):
        v = obj.data.vertices[index]
        samples.append((obj, v.co.copy(), [(names[g.group], g.weight) for g in v.groups
                                           if names[g.group] in r.pose.bones and g.weight > 1e-6]))
src = np.array([p.vector[:] for p in sw.data.attributes["astra_sword_source"].data])
loc = np.array([v.co[:] for v in sw.data.vertices])
fit = np.linalg.lstsq(np.column_stack((src, np.ones(len(src)))), loc, rcond=None)[0]
tip = sw.data.vertices[int(src[:, 2].argmin())].co.copy()
grip = Vector(np.array([61.2, -66.3, 167, 1]) @ fit)
bind = r.data.bones["RightHand"].matrix_local.inverted() @ AI @ sw.matrix_world

def points():
    out=[]
    for obj, co, influences in samples:
        p=np.zeros(3);total=0
        for n,w in influences:
            M=AW@r.pose.bones[n].matrix@r.data.bones[n].matrix_local.inverted()@AI@obj.matrix_world
            p += w*np.array(M@co);total+=w
        out.append(p/total)
    return np.array(out)

blade_ids=set(int(i) for i in np.where(src[:,2]<150)[0])
def clearance():
    deform=AW@r.pose.bones["RightHand"].matrix@bind
    a=np.array(deform@grip);b=np.array(deform@tip);axis=b-a;co=points();rel=co-a
    u=np.clip(rel@axis/(axis@axis),0,1)
    proxy=float(np.linalg.norm(rel-u[:,None]*axis,axis=1).min()-.14284110069274902-.002)
    ev=sw.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();verts=[ev.matrix_world@v.co for v in me.vertices];poly=[tuple(p.vertices) for p in me.polygons if all(i in blade_ids for i in p.vertices)];ev.to_mesh_clear();bvh=BVHTree.FromPolygons(verts,poly)
    exact=min(bvh.find_nearest(Vector(p))[3] for p in co)-.002
    return proxy,float(exact)

s.frame_set(42);bpy.context.view_layer.update();base=r.pose.bones['neck'].matrix_basis.copy();results=[]
for delta in [-60,-45,-30,-20,-15,-10,0,10,15,20,30,45,60,90]:
    r.pose.bones['neck'].matrix_basis=base.copy();bpy.context.view_layer.update()
    p=r.pose.bones['neck'];world=AW@p.matrix;world=world@Quaternion(Vector((0,0,1)),math.radians(delta)).to_matrix().to_4x4();p.matrix=AI@world;bpy.context.view_layer.update()
    proxy,exact=clearance();results.append({'additional_world_z_deg':delta,'clearance_proxy_m':proxy,'sampled_exact_surface_clearance_m':exact})
Path(ROOT/'renders/astra/rehost/rising_spin/hair_avoidance_probe.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2),flush=True)
