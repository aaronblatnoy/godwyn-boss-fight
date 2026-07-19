"""Phase 2 cloth — probe godwyn_mocap.blend structure.

Run: blender --background models/godwyn_mocap.blend --python scripts/p2cloth_probe.py
"""
import bpy
from mathutils import Vector

scene = bpy.context.scene
print(f"frames {scene.frame_start}-{scene.frame_end} fps={scene.render.fps}")

arm = next(o for o in scene.objects if o.type == "ARMATURE")
print(f"armature {arm.name} scale={tuple(round(c,4) for c in arm.scale)} "
      f"bones={len(arm.data.bones)}")
phys = [b.name for b in arm.data.bones if b.name.startswith("phys_")]
print(f"phys bones: {len(phys)}; sample: {sorted(phys)[:6]}")
# chain roots
roots = sorted({b.name for b in arm.data.bones
                if b.name.startswith("phys_")
                and (not b.parent or not b.parent.name.startswith("phys_"))})
print(f"phys chain roots ({len(roots)}): {roots}")

for o in scene.objects:
    if o.type != "MESH":
        print(f"OBJ {o.name} type={o.type} parent={o.parent and o.parent.name} "
              f"parent_bone={getattr(o,'parent_bone','')!r}")
        continue
    me = o.data
    mods = [(m.type, m.name) for m in o.modifiers]
    vgs = [g.name for g in o.vertex_groups]
    physvg = [g for g in vgs if g.startswith("phys_")]
    basevg = [g for g in vgs if not g.startswith("phys_")]
    mats = [m.name if m else None for m in me.materials]
    print(f"MESH {o.name}: verts={len(me.vertices)} polys={len(me.polygons)} "
          f"mods={mods} mats={mats}")
    print(f"   vgroups: base={len(basevg)} {basevg[:8]}... phys={len(physvg)}")
    print(f"   parent={o.parent and o.parent.name} parent_type={o.parent_type} "
          f"scale={tuple(round(c,4) for c in o.scale)}")
    # bbox world
    mw = o.matrix_world
    xs = [mw @ Vector(c) for c in o.bound_box]
    mn = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    mx = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    print(f"   bbox world min={tuple(round(c,2) for c in mn)} "
          f"max={tuple(round(c,2) for c in mx)}")

# which mesh(es) carry phys_ weights, and how are verts distributed?
for o in scene.objects:
    if o.type != "MESH":
        continue
    physidx = {g.index: g.name for g in o.vertex_groups if g.name.startswith("phys_")}
    if not physidx:
        continue
    n_phys_weighted = 0
    for v in o.data.vertices:
        if any(ge.group in physidx and ge.weight > 0.01 for ge in v.groups):
            n_phys_weighted += 1
    print(f"PHYS-WEIGHTED {o.name}: {n_phys_weighted}/{len(o.data.vertices)} verts")

# material list summary
for m in bpy.data.materials:
    if m.users:
        imgs = [n.image.name for n in (m.node_tree.nodes if m.node_tree else [])
                if n.type == 'TEX_IMAGE' and n.image]
        print(f"MAT {m.name}: images={imgs}")
print("PROBE DONE")
