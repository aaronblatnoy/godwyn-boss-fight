# export_game_glb.py — Phase 3: Export godwyn_game.glb + verify + turnaround renders.
#
# 1. Opens models/godwyn_gameasset.blend (produced by bake_gameasset.py —
#    contains the rigged, skinned, bake-PBR'd character).
# 2. Exports models/godwyn_game.glb via glTF 2.0:
#      - includes armature + skinning weights
#      - includes baked baseColor / metallic / roughness textures
#      - +Y up, rest pose, apply modifiers where safe (NOT the armature modifier)
# 3. VERIFIES the export by re-importing models/godwyn_game.glb headlessly and
#    reporting: bone count, mesh count, material/texture count, skinning present.
# 4. Renders a 3-shot EEVEE turnaround of the re-imported glb (front, 3/4, side)
#    to renders/game/ and writes previews.
#
# Headless:
#   blender --background --python ~/godwyn-boss-fight/scripts/export_game_glb.py

import bpy, sys, os, math
from mathutils import Vector

HOME = os.path.expanduser("~")
BLEND    = f"{HOME}/godwyn-boss-fight/models/godwyn_gameasset.blend"
OUT_GLB  = f"{HOME}/godwyn-boss-fight/models/godwyn_game.glb"
OUTDIR   = f"{HOME}/godwyn-boss-fight/renders/game"
os.makedirs(OUTDIR, exist_ok=True)

# ---------------------------------------------------------------- helpers
def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[export] preview engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine id worked")

# ================================================================ STAGE 1: OPEN BLEND + EXPORT GLB
print(f"[export] opening {BLEND}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
assert arm is not None, "FATAL: no armature in gameasset.blend"
char = next((o for o in scn.objects if o.type == "MESH" and len(o.vertex_groups) > 0), None)
assert char is not None, "FATAL: no skinned mesh in gameasset.blend"

print(f"[export] armature={arm.name}  bones={len(arm.data.bones)}")
print(f"[export] char={char.name}  verts={len(char.data.vertices)}  vgroups={len(char.vertex_groups)}")
print(f"[export] materials: {[m.name for m in char.data.materials]}")

# Show what textures are linked into the materials
for mat in char.data.materials:
    if mat and mat.use_nodes:
        tex_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
        for t in tex_nodes:
            print(f"[export]   mat={mat.name}  tex={t.image.name}  path={t.image.filepath}")

# Deselect all, select armature + char mesh only
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
char.select_set(True)
bpy.context.view_layer.objects.active = arm

# Verify armature modifier exists (skinning)
armmods = [m for m in char.modifiers if m.type == "ARMATURE"]
assert len(armmods) >= 1, "FATAL: char mesh has no armature modifier — skinning will be lost"
print(f"[export] armature modifiers on char: {[m.name for m in armmods]}")

print(f"[export] exporting {OUT_GLB} ...")
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    use_selection=True,             # only armature + char mesh
    export_format="GLB",
    export_image_format="AUTO",     # embed baked PNGs
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_skins=True,              # include skinning
    export_armature_object_remove=False,
    export_rest_position_armature=True,  # export in rest pose
    export_yup=True,                # +Y up (glTF 2.0)
    export_apply=True,              # apply modifiers — but not armature (Blender 4+)
    export_animations=False,        # no animations in this export (game asset rest pose)
    export_lights=False,
    export_cameras=False,
)
print(f"[export] wrote {OUT_GLB}  ({os.path.getsize(OUT_GLB):,} bytes)")

# ================================================================ STAGE 2: VERIFY
print(f"\n[verify] re-importing {OUT_GLB} ...")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)

vscn = bpy.context.scene
v_arm = next((o for o in vscn.objects if o.type == "ARMATURE"), None)
v_meshes = [o for o in vscn.objects if o.type == "MESH"]
v_skinned = [o for o in v_meshes if len(o.vertex_groups) > 0]

assert v_arm is not None, "VERIFY FAIL: no armature in re-imported GLB"
n_bones = len(v_arm.data.bones)
n_meshes = len(v_meshes)

# count materials and textures
mats_seen = set()
tex_count = 0
for o in v_meshes:
    for mat in o.data.materials:
        if mat and mat.name not in mats_seen:
            mats_seen.add(mat.name)
            if mat.use_nodes:
                for n in mat.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image:
                        tex_count += 1

n_mats = len(mats_seen)
n_skinned = len(v_skinned)

print(f"\n[verify] ===== GLB VERIFICATION REPORT =====")
print(f"[verify]   bones       : {n_bones}")
print(f"[verify]   meshes      : {n_meshes}")
print(f"[verify]   materials   : {n_mats}")
print(f"[verify]   textures    : {tex_count}")
print(f"[verify]   skinned mesh: {n_skinned} (vgroups present)")
print(f"[verify]   armature OK : {v_arm.name}")
print(f"[verify] ==========================================")

assert n_bones >= 24,   f"VERIFY FAIL: only {n_bones} bones — expected >=24"
assert n_meshes >= 1,   f"VERIFY FAIL: {n_meshes} meshes"
assert n_mats >= 1,     f"VERIFY FAIL: {n_mats} materials"
assert tex_count >= 1,  f"VERIFY FAIL: {tex_count} textures embedded"
assert n_skinned >= 1,  f"VERIFY FAIL: {n_skinned} skinned meshes — skinning lost"
print("[verify] ALL CHECKS PASSED — rigged + textured game asset confirmed")

# ================================================================ STAGE 3: EEVEE TURNAROUND RENDERS
print(f"\n[render] rendering EEVEE turnaround of {OUT_GLB} ...")
scn2 = bpy.context.scene
char2 = next((o for o in scn2.objects if o.type == "MESH"), None)
assert char2 is not None

pick_eevee(scn2)
scn2.render.resolution_x, scn2.render.resolution_y = 1024, 1365
scn2.render.image_settings.file_format = "PNG"
scn2.view_settings.view_transform = "AgX"
scn2.view_settings.look = "AgX - Punchy"

# bbox from all mesh objects
pts = []
for o in v_meshes:
    pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
Hgt = bb_max.z - bb_min.z
print(f"[render] bbox H={Hgt:.3f}  center={tuple(round(v,3) for v in center)}")

# world
w = bpy.data.worlds.get("GameRenderWorld") or bpy.data.worlds.new("GameRenderWorld")
scn2.world = w
w.use_nodes = True
wbg = w.node_tree.nodes.get("Background")
if wbg:
    wbg.inputs["Color"].default_value = (0.008, 0.010, 0.018, 1.0)
    wbg.inputs["Strength"].default_value = 0.5

# lights
def area(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size = size; d.color = color; d.energy = power
    o = bpy.data.objects.new(name, d)
    scn2.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

tgt = (center.x, center.y, center.z + 0.05 * Hgt)
Hs = Hgt
area("TKey",  (center.x - 1.0*Hs, center.y - 1.2*Hs, bb_max.z + 0.5*Hs), tgt,
     1.2*Hs, (1.0, 0.72, 0.42), 180.0*Hs*Hs)
area("TFill", (center.x + 1.3*Hs, center.y - 1.0*Hs, center.z), tgt,
     1.6*Hs, (0.35, 0.50, 0.95),  30.0*Hs*Hs)
area("TRim1", (center.x - 0.9*Hs, center.y + 1.1*Hs, bb_max.z + 0.2*Hs), tgt,
     0.8*Hs, (1.0, 0.65, 0.28), 140.0*Hs*Hs)
area("TRim2", (center.x + 1.0*Hs, center.y + 1.0*Hs, center.z + 0.4*Hs), tgt,
     0.8*Hs, (0.55, 0.65, 1.0),  75.0*Hs*Hs)

# cameras: front (0°), 3/4 (-45°), side (-90°)
shots = [
    ("game_front",   0.0,   50),
    ("game_3q",    -45.0,   50),
    ("game_side",  -90.0,   50),
]

def shoot(name, yaw_deg, focal):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36.0
    cam = bpy.data.objects.new(name, cd)
    scn2.collection.objects.link(cam)
    look = Vector((center.x, center.y, center.z))
    fov = 2 * math.atan(36.0 / (2 * focal))
    dist = (Hgt / 2 * 1.20) / math.tan(fov / 2)
    yaw = math.radians(yaw_deg)
    off = Vector((math.sin(yaw), -math.cos(yaw), 0.0)) * dist
    cam.location = look + off + Vector((0, 0, 0.05 * Hgt))
    direc = (look - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn2.camera = cam
    path = f"{OUTDIR}/{name}.png"
    scn2.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sz = os.path.getsize(path)
    print(f"[render] wrote {path}  ({sz:,} bytes)")
    return path

rendered = []
for shot_name, yaw, focal in shots:
    p = shoot(shot_name, yaw, focal)
    rendered.append(p)

print(f"\n[export] DONE. GLB: {OUT_GLB}")
print(f"[export] Renders: {rendered}")
print("[export] Phase 3 COMPLETE — rigged + textured game asset exported and verified.")
