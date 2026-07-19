"""Diagnose: where are the PINNED proxy verts, armature-only vs with cloth?"""
import bpy

scene = bpy.context.scene
proxy = bpy.data.objects["CapeProxy"]
arm = next(o for o in scene.objects if o.type == "ARMATURE")
cl = proxy.modifiers["Cloth"]
pi = proxy.vertex_groups["pin"].index
pinned = set()
for v in proxy.data.vertices:
    for ge in v.groups:
        if ge.group == pi and ge.weight > 0.5:
            pinned.add(v.index)
print(f"pinned verts: {len(pinned)}/{len(proxy.data.vertices)}")
print("proxy stack:", [(m.name, m.type, m.show_viewport) for m in proxy.modifiers])
print("scene gravity:", tuple(scene.gravity), "use:", scene.use_gravity)

def stats(tag, frame):
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = proxy.evaluated_get(dg)
    if len(ev.data.vertices) != len(proxy.data.vertices):
        print(f"{tag} f{frame}: EVAL VERTCOUNT {len(ev.data.vertices)} != "
              f"{len(proxy.data.vertices)}")
        return
    zs_p = [ev.data.vertices[i].co.z for i in pinned]
    zs_a = [v.co.z for v in ev.data.vertices]
    print(f"{tag} f{frame}: pinned z=[{min(zs_p):.2f},{max(zs_p):.2f}] "
          f"all z=[{min(zs_a):.2f},{max(zs_a):.2f}]")

# rest mesh (no modifiers)
zs = [v.co.z for i, v in enumerate(proxy.data.vertices) if i in pinned]
za = [v.co.z for v in proxy.data.vertices]
print(f"REST mesh: pinned z=[{min(zs):.2f},{max(zs):.2f}] all z=[{min(za):.2f},{max(za):.2f}]")

# armature bone check
scene.frame_set(1)
ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
s = arm.scale.x
for bn in ("Hips", "Spine02", "Head", "phys_cape_C_00", "phys_robe_back_C_00"):
    pb = ae.pose.bones.get(bn)
    if pb:
        print(f"bone {bn}: world z={pb.head.z * s:.2f}")

cl.show_viewport = False
stats("ARMATURE-ONLY", -20)
stats("ARMATURE-ONLY", 1)
stats("ARMATURE-ONLY", 40)
cl.show_viewport = True
stats("WITH-CLOTH", -20)
stats("WITH-CLOTH", 1)
stats("WITH-CLOTH", 40)
print("DIAG DONE")
