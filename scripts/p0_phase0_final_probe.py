"""
Phase 0 — Combined GPU gate + GLB probe for godwyn_full_final.glb.
Reports:
  - Blender version
  - Cycles + OptiX device table with GPU count
  - Tiny 1x1 GPU smoke-test render
  - Mesh count + names/vert/face counts
  - Material count + names
  - Texture channels per material (baseColor, normal, metallic, roughness, emission, etc.)
"""

import sys
import bpy

GLB_PATH = "/home/aaron/godwyn-boss-fight/models/godwyn_full_final.glb"

print("=" * 60)
print("PHASE 0 — GPU GATE")
print("=" * 60)

# ── Blender version ────────────────────────────────────────────
v = bpy.app.version
ver_str = ".".join(str(x) for x in v)
print(f"Blender version : {ver_str}")
if v < (5, 1, 0):
    print("FAIL: need >= 5.1.0")
    sys.exit(1)
print("OK: Blender version")

# ── Cycles OptiX device enum ───────────────────────────────────
prefs = bpy.context.preferences
cprefs = prefs.addons["cycles"].preferences

cprefs.get_devices()
cprefs.compute_device_type = "OPTIX"
cprefs.get_devices()

print("\nDevice table (OptiX):")
gpu_count = 0
for dev in cprefs.devices:
    tag = "[GPU]" if dev.type in ("OPTIX", "CUDA") else "[CPU]"
    use = "USE" if dev.use else "---"
    print(f"  {use}  {tag}  {dev.name}")
    if dev.type in ("OPTIX", "CUDA"):
        dev.use = True
        gpu_count += 1

print(f"\nGPU devices found: {gpu_count}")
if gpu_count == 0:
    print("FAIL: no GPU devices detected")
    sys.exit(1)
print(f"OK: {gpu_count} GPU(s) enabled")

# ── Tiny GPU render (1×1, 1 sample) ───────────────────────────
print("\nRunning 1x1 GPU smoke test ...")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.render.resolution_x = 1
scene.render.resolution_y = 1
scene.cycles.samples = 1
scene.render.filepath = "/tmp/p0_gpu_smoketest.png"
scene.render.image_settings.file_format = "PNG"

try:
    bpy.ops.render.render(write_still=True)
    print("OK: GPU smoke-test render completed")
except Exception as e:
    print(f"FAIL: GPU render error — {e}")
    sys.exit(1)

print("\n=== PHASE 0 GPU GATE: PASS ===")

# ── GLB Probe ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"PHASE 0 — GLB PROBE: godwyn_full_final.glb")
print("=" * 60)

# Clear scene before import
bpy.ops.wm.read_factory_settings(use_empty=True)

print(f"\nImporting: {GLB_PATH}")
try:
    result = bpy.ops.import_scene.gltf(
        filepath=GLB_PATH,
        filter_glob="*.glb;*.gltf",
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"operator returned {result}")
except Exception as e:
    print(f"FAIL: import error — {e}")
    sys.exit(1)
print("OK: import succeeded")

# ── Mesh inventory ────────────────────────────────────────────
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
print(f"\nMesh count: {len(meshes)}")
for i, m in enumerate(meshes):
    verts = len(m.data.vertices) if m.data else "?"
    faces = len(m.data.polygons) if m.data else "?"
    print(f"  [{i}] {m.name!r:40s}  verts={verts}  faces={faces}")

if not meshes:
    print("FAIL: no mesh objects found after import")
    sys.exit(1)

# ── Material inventory ────────────────────────────────────────
mats = list(bpy.data.materials)
print(f"\nMaterial count: {len(mats)}")

SOCKET_MAP = {
    "Base Color": "baseColor",
    "Metallic": "metallic",
    "Roughness": "roughness",
    "Normal": "normal",
    "Emission": "emission",
    "Emission Color": "emission",
    "Alpha": "alpha",
    "Specular IOR Level": "specular",
    "Subsurface Weight": "subsurface",
}


def probe_material(mat):
    """Return dict of channel -> texture name or node type string."""
    channels = {}
    if not mat.use_nodes or mat.node_tree is None:
        return channels
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if principled is None:
        bsdf = next((n for n in nodes if "BSDF" in n.type), None)
        if bsdf is None:
            return channels
        principled = bsdf

    for link in links:
        to_node = link.to_node
        to_socket = link.to_socket
        from_node = link.from_node

        if to_node != principled:
            continue

        socket_name = to_socket.name
        chan = SOCKET_MAP.get(socket_name, socket_name)

        source = from_node
        if source.type == "NORMAL_MAP":
            for lk2 in links:
                if lk2.to_node == source and lk2.to_socket.name == "Color":
                    source = lk2.from_node
                    break

        if source.type == "TEX_IMAGE":
            img = source.image
            tex_name = img.name if img else "(no image)"
            channels[chan] = tex_name
        else:
            channels[chan] = f"[{source.type}]"

    return channels


print("\nTexture channel report per material:")
print("-" * 60)
for mat in mats:
    print(f"\n  Material: {mat.name!r}")
    if not mat.use_nodes:
        print("    (no node tree)")
        continue
    ch = probe_material(mat)
    if not ch:
        print("    (no texture links found — may use vertex color or defaults)")
        if mat.node_tree:
            img_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]
            for n in img_nodes:
                img_name = n.image.name if n.image else "(no image)"
                print(f"    TEX_IMAGE node: {n.name!r} -> {img_name}")
    else:
        for chan, tex in sorted(ch.items()):
            print(f"    {chan:20s}: {tex}")

# ── All-material channel summary ──────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Meshes    : {len(meshes)}")
print(f"  Materials : {len(mats)}")

all_channels = set()
for mat in mats:
    ch = probe_material(mat)
    all_channels.update(ch.keys())

print(f"  Channels found across all materials:")
for c in sorted(all_channels):
    print(f"    - {c}")

# Also dump all image texture nodes found in all materials (failsafe)
print("\n  All TEX_IMAGE nodes across all materials:")
for mat in mats:
    if not mat.use_nodes or mat.node_tree is None:
        continue
    img_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]
    for n in img_nodes:
        img_name = n.image.name if n.image else "(no image)"
        colorspace = n.image.colorspace_settings.name if n.image else "?"
        print(f"    {mat.name!r:30s}  {n.name!r:30s}  -> {img_name}  [{colorspace}]")

print("\n=== PHASE 0 COMPLETE: GPU OK + GLB PROBED ===")
