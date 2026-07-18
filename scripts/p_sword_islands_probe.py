"""p_sword_islands_probe.py — round-2: map islands in the planted-sword region
(left side +X, front -Y) of godwyn_game.glb, and render the region so we can
SEE which shells are the sword."""
import bpy, bmesh, os, math
from collections import deque
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO, "models", "godwyn_game.glb")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = bpy.data.objects.get("Armature")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))
me = mesh_obj.data
mwm = mesh_obj.matrix_world
awm = arm.matrix_world
lh = awm @ arm.data.bones["LeftHand"].head_local
print(f"[probe] LeftHand={tuple(round(c,3) for c in lh)}")

world_co = [mwm @ v.co for v in me.vertices]
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
seen = set(); islands = []
for v0 in bm.verts:
    if v0.index in seen:
        continue
    comp = {v0.index}; dq = deque([v0])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index not in comp:
                comp.add(o.index); dq.append(o)
    seen |= comp; islands.append(comp)
bm.free()

# islands whose center lies in the left-front quadrant near/below LeftHand
cands = []
for comp in islands:
    if len(comp) < 10:
        continue
    pts = [world_co[i] for i in comp]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    if c.x > 0.20 and c.y < -0.05:
        cands.append((len(comp), lo, hi, c, comp))
cands.sort(key=lambda t: -(t[2].z - t[1].z))
for n, lo, hi, c, _ in cands[:40]:
    print(f"[cand] n={n:6d} zext={hi.z-lo.z:.2f} "
          f"lo=({lo.x:+.2f},{lo.y:+.2f},{lo.z:+.2f}) hi=({hi.x:+.2f},{hi.y:+.2f},{hi.z:+.2f})")

# render the left-front region: hide everything except islands with c.x>0.20, c.y<-0.05
keep = set()
for n, lo, hi, c, comp in cands:
    keep |= comp
print(f"[probe] region verts={len(keep)}")
# separate a temp copy for render clarity: hide body verts via mask modifier is
# complex — instead just render the whole char from a left-front low angle,
# plus a second shot with ONLY the candidate shells (delete others on a COPY).
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1280
w = scene.world or bpy.data.worlds.new("W"); scene.world = w
w.use_nodes = True
bgn = w.node_tree.nodes.get("Background")
if bgn:
    bgn.inputs[0].default_value = (0.25, 0.27, 0.33, 1.0); bgn.inputs[1].default_value = 1.2
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", 'SUN'))
sun.data.energy = 5.0; sun.rotation_euler = (math.radians(55), 0, math.radians(35))
scene.collection.objects.link(sun)
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
scene.collection.objects.link(cam); scene.camera = cam

def shot(frm, to, lens, path):
    cam.location = frm
    cam.rotation_euler = (Vector(to) - Vector(frm)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[probe] wrote {path}")

shot((2.6, -2.8, 1.3), (0.45, -0.3, 1.0), 40, "/tmp/probe_leftfront.png")
shot((1.8, -3.4, 1.1), (0.5, -0.45, 1.0), 50, "/tmp/probe_swordzone.png")

# candidate-only render: duplicate obj, delete non-candidate verts
dup = mesh_obj.copy(); dup.data = mesh_obj.data.copy()
scene.collection.objects.link(dup)
dbm = bmesh.new(); dbm.from_mesh(dup.data); dbm.verts.ensure_lookup_table()
kill = [dbm.verts[i] for i in range(len(dup.data.vertices)) if i not in keep]
bmesh.ops.delete(dbm, geom=kill, context='VERTS')
dbm.to_mesh(dup.data); dbm.free()
for m in list(dup.modifiers):
    dup.modifiers.remove(m)
mesh_obj.hide_render = True
shot((2.6, -2.8, 1.3), (0.45, -0.3, 1.0), 40, "/tmp/probe_cands_only.png")
shot((0.55, -3.2, 1.0), (0.55, -0.45, 1.0), 45, "/tmp/probe_cands_front.png")
print("[probe] DONE")
