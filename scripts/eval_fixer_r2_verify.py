"""eval_fixer_r2_verify.py — round-2 fixer verification renders (EEVEE).
Loads models/godwyn_face.blend (final round-2 output) and renders:
  /tmp/eval2_full_front.png     full body, front
  /tmp/eval2_full_34.png        full body, 3/4
  /tmp/eval2_grip_pommel.png    left palm on pommel of the planted sword
  /tmp/eval2_sword_only.png     Godwyn_Sword alone, framed on its bbox
  /tmp/eval2_face_front.png     face crop, front
  /tmp/eval2_face_34.png        face crop, 3/4
  /tmp/eval2_deform_twist.png   spine-twist + arm-raise pose (deform test)
Prints sword bbox + deform stretch stats.
"""
import bpy, os, math
from mathutils import Vector

HOME = os.path.expanduser("~")
bpy.ops.wm.open_mainfile(filepath=f"{HOME}/godwyn-boss-fight/models/godwyn_face.blend")
scn = bpy.context.scene
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]

for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scn.render.engine = e
        break
    except Exception:
        pass
if hasattr(scn, "eevee") and hasattr(scn.eevee, "taa_render_samples"):
    scn.eevee.taa_render_samples = 64
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"

w = bpy.data.worlds.new("EvalW"); scn.world = w; w.use_nodes = True
nt = w.node_tree; nt.nodes.clear()
bg = nt.nodes.new("ShaderNodeBackground"); ou = nt.nodes.new("ShaderNodeOutputWorld")
bg.inputs["Color"].default_value = (0.015, 0.016, 0.022, 1)
bg.inputs["Strength"].default_value = 0.5
nt.links.new(bg.outputs["Background"], ou.inputs["Surface"])

def area(n, loc, tg, sz, col, pw):
    d = bpy.data.lights.new(n, "AREA"); d.size = sz; d.color = col; d.energy = pw
    ob = bpy.data.objects.new(n, d); scn.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(tg) - Vector(loc)).normalized().to_track_quat("-Z", "Y").to_euler()

area("K", (-1.8, -2.6, 2.6), (0, 0, 1.4), 2.4, (1.0, 0.85, 0.55), 900)
area("F", (2.2, -2.2, 1.2), (0, 0, 1.2), 3.2, (0.45, 0.55, 0.95), 260)
area("R", (1.6, 2.6, 2.4), (0, 0, 1.5), 1.6, (0.5, 0.65, 1.0), 700)

cam = bpy.data.objects.new("EvalCam", bpy.data.cameras.new("EvalCam"))
scn.collection.objects.link(cam); scn.camera = cam

def shot(path, frm, to, lens, res=(1080, 1350)):
    scn.render.resolution_x, scn.render.resolution_y = res
    cam.data.lens = lens
    cam.location = Vector(frm)
    cam.rotation_euler = (Vector(to) - Vector(frm)).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[eval2] wrote", path)

lh = arm.matrix_world @ arm.data.bones["LeftHand"].head_local
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
slo = Vector((min(c.x for c in sw_pts), min(c.y for c in sw_pts), min(c.z for c in sw_pts)))
shi = Vector((max(c.x for c in sw_pts), max(c.y for c in sw_pts), max(c.z for c in sw_pts)))
sc = (slo + shi) / 2
print(f"[eval2] sword bbox lo={tuple(round(c,3) for c in slo)} "
      f"hi={tuple(round(c,3) for c in shi)} zext={shi.z-slo.z:.2f}")

shot("/tmp/eval2_full_front.png", (0, -4.6, 1.55), (0, 0, 1.45), 42)
shot("/tmp/eval2_full_34.png", (2.9, -3.6, 1.7), (0.1, 0, 1.35), 40)
shot("/tmp/eval2_grip_pommel.png", (lh.x + 0.35, lh.y - 0.85, lh.z + 0.25),
     (lh.x, lh.y, lh.z - 0.1), 60, res=(1200, 1200))
body.hide_render = True
shot("/tmp/eval2_sword_only.png", (sc.x + 1.5, sc.y - 2.3, sc.z), sc, 40, res=(900, 1400))
body.hide_render = False

face_c = Vector((0.0, -0.40, 2.99))
shot("/tmp/eval2_face_front.png", tuple(face_c + Vector((0, -1.0, 0.02))), tuple(face_c), 80, res=(1100, 1100))
shot("/tmp/eval2_face_34.png", tuple(face_c + Vector((-0.62, -0.78, 0.05))), tuple(face_c), 80, res=(1100, 1100))

# ── posed deform test: spine twist + right-arm raise ──
def eval_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ob = body.evaluated_get(dg)
    m = ob.matrix_world
    return [m @ v.co for v in ob.data.vertices]

edges = [tuple(e.vertices) for e in list(body.data.edges)[::5]]
rest = eval_coords()
rlen = [(rest[a] - rest[b]).length for a, b in edges]
for bn, eul in (("Spine", (0, 30, 0)), ("Spine01", (0, 15, 0)), ("RightArm", (0, 0, -45))):
    pb = arm.pose.bones[bn]
    pb.rotation_mode = 'XYZ'
    pb.rotation_euler = tuple(math.radians(a) for a in eul)
bpy.context.view_layer.update()
co = eval_coords()
ratios = sorted((co[a] - co[b]).length / rl for (a, b), rl in zip(edges, rlen) if rl > 1e-6)
print(f"[eval2] deform stretch: p99={ratios[int(len(ratios)*0.99)]:.3f} max={ratios[-1]:.3f}")
shot("/tmp/eval2_deform_twist.png", (2.4, -3.9, 1.7), (0.1, 0, 1.3), 42)
print("[eval2] DONE")
