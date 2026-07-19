"""P1 probe: bone names, rest orientations, mesh dims, shape keys, weight stats."""
import bpy, os, math
from mathutils import Vector

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")

print("=== ARMATURE:", arm.name, "===")
for b in arm.data.bones:
    h = arm.matrix_world @ b.head_local
    t = arm.matrix_world @ b.tail_local
    # local Y axis direction in world (bone points along +Y)
    yaxis = (t - h).normalized() if (t - h).length > 1e-8 else Vector((0, 0, 0))
    print(f"  {b.name:20s} parent={b.parent.name if b.parent else None!s:16s} "
          f"head=({h.x:+.3f},{h.y:+.3f},{h.z:+.3f}) dir=({yaxis.x:+.2f},{yaxis.y:+.2f},{yaxis.z:+.2f}) len={(t-h).length:.3f}")

print("\n=== MESH:", mesh.name, "===")
print("  verts:", len(mesh.data.vertices))
bb = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
mn = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
mx = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
print(f"  bbox min=({mn.x:.2f},{mn.y:.2f},{mn.z:.2f}) max=({mx.x:.2f},{mx.y:.2f},{mx.z:.2f}) height={mx.z-mn.z:.2f}")
sk = mesh.data.shape_keys
print("  shape keys:", [k.name for k in sk.key_blocks] if sk else None)
print("  materials:", [m.name for m in mesh.data.materials if m])
print("  images:", [(i.name, tuple(i.size), i.packed_file is not None) for i in bpy.data.images if i.size[0]])

# weight influence stats
counts = {}
maxw_over1 = 0
for v in mesh.data.vertices:
    n = len([g for g in v.groups if g.weight > 1e-4])
    counts[n] = counts.get(n, 0) + 1
    s = sum(g.weight for g in v.groups)
    if abs(s - 1.0) > 0.01:
        maxw_over1 += 1
print("\n=== WEIGHTS ===")
print("  influences-per-vert histogram:", dict(sorted(counts.items())))
print("  verts with weight-sum off by >0.01:", maxw_over1)
print("PROBE DONE")
