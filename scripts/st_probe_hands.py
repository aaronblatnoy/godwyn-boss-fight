"""
st_probe_hands.py — Phase 1 (sword) pre-work probe.
Import godwyn_game.glb, report exact parenting/transform state of
Godwyn_Sword + Godwyn_Gauntlet, hand bone world matrices, then EEVEE-render
close-ups of both hands + full body so we can SEE the current grip state.

Headless:  blender --background --python ~/godwyn-boss-fight/scripts/st_probe_hands.py
Outputs:   /tmp/st_probe/*.png
"""
import bpy, os, math
from mathutils import Vector, Matrix

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO, "models", "godwyn_game.glb")
OUT = "/tmp/st_probe"
os.makedirs(OUT, exist_ok=True)

# fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print("\n[PARENTING DETAIL]")
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    print(f"  {o.name}: parent={o.parent.name if o.parent else None} "
          f"parent_type={o.parent_type} parent_bone='{o.parent_bone}'")
    print(f"    loc={tuple(round(x,4) for x in o.location)} "
          f"rot_euler={tuple(round(math.degrees(a),1) for a in o.rotation_euler)} "
          f"scale={tuple(round(x,4) for x in o.scale)}")
    mw = o.matrix_world
    print(f"    matrix_world translation={tuple(round(x,4) for x in mw.translation)}")
    # world bbox from evaluated mesh
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    if len(me.vertices):
        ws = [ev.matrix_world @ v.co for v in me.vertices]
        for ax, nm in enumerate("XYZ"):
            vals = [w[ax] for w in ws]
            print(f"    world {nm}: [{min(vals):.3f}, {max(vals):.3f}]")
    ev.to_mesh_clear()

print("\n[ARMATURE OBJECT]")
print(f"  loc={tuple(arm.location)} scale={tuple(arm.scale)} "
      f"rot={tuple(round(math.degrees(a),1) for a in arm.rotation_euler)}")

print("\n[HAND BONES WORLD]")
for bn in ("RightHand", "RightForeArm", "RightArm", "LeftHand", "LeftForeArm", "LeftArm"):
    pb = arm.pose.bones.get(bn)
    if not pb:
        print(f"  {bn}: MISSING"); continue
    hw = arm.matrix_world @ pb.head
    tw = arm.matrix_world @ pb.tail
    print(f"  {bn}: head_world={tuple(round(x,4) for x in hw)} tail_world={tuple(round(x,4) for x in tw)}")
    M = arm.matrix_world @ pb.matrix
    for i, axnm in enumerate(("X", "Y", "Z")):
        axv = M.col[i].to_3d().normalized()
        print(f"    axis {axnm} = {tuple(round(x,3) for x in axv)}")

# check char1 for leftover sword-ish verts near the sword bbox / far from body
char1 = bpy.data.objects.get("char1")
print("\n[CHAR1 HAND-REGION VERT COUNT] (verts weighted mainly to RightHand)")
if char1:
    vgi = char1.vertex_groups.find("RightHand")
    n = 0
    pts = []
    for v in char1.data.vertices:
        for g in v.groups:
            if g.group == vgi and g.weight > 0.5:
                n += 1
                pts.append(char1.matrix_world @ v.co)
    print(f"  RightHand-weighted verts (w>0.5): {n}")
    if pts:
        for ax, nm in enumerate("XYZ"):
            vals = [p[ax] for p in pts]
            print(f"    {nm}: [{min(vals):.3f}, {max(vals):.3f}]")

# ── RENDERS (EEVEE) ────────────────────────────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Filmic'

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
scene.collection.objects.link(fill)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam

def shoot(name, target, dist, elev_deg, azim_deg, lens=50):
    cam.data.lens = lens
    el, az = math.radians(elev_deg), math.radians(azim_deg)
    off = Vector((dist * math.cos(el) * math.sin(az),
                  -dist * math.cos(el) * math.cos(az),
                  dist * math.sin(el)))
    cam.location = target + off
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")

rh = arm.matrix_world @ arm.pose.bones["RightHand"].head
lh = arm.matrix_world @ arm.pose.bones["LeftHand"].head
body_c = Vector((0, 0, 1.6))

print("\n[RENDERS]")
shoot("full_front.png", body_c, 7.0, 5, 0, 35)
shoot("rhand_front.png", rh, 1.2, 10, -30, 60)
shoot("rhand_side.png", rh, 1.2, 10, -100, 60)
shoot("lhand_front.png", lh, 1.2, 10, 30, 60)
print("\nPROBE DONE")
