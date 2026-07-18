"""
Phase 0 — GLB inspection probe for godwyn_full_A.glb.
Reports:
  - Mesh count + names
  - Material count + names
  - Texture channels present on each material node tree
    (baseColor/albedo, normal, metallic, roughness, emission, etc.)
"""

import sys
import bpy

GLB_PATH = "/home/aaron/godwyn-boss-fight/models/godwyn_full_A.glb"

print("=" * 60)
print("PHASE 0 — GLB PROBE: godwyn_full_A.glb")
print("=" * 60)

# ── Clear scene ───────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)

# ── Import GLB ────────────────────────────────────────────────
print(f"\nImporting: {GLB_PATH}")
try:
    # Blender 5.x: use keyword args explicitly
    result = bpy.ops.import_scene.gltf(
        filepath=GLB_PATH,
        filter_glob="*.glb;*.gltf",
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"operator returned {result}")
except Exception as e:
    # Fallback: try the newer IO handler if available
    try:
        import bpy.ops as ops
        # Try alternate operator name used in some builds
        result2 = ops.wm.gltf2_import(filepath=GLB_PATH)
        if "FINISHED" not in result2:
            raise RuntimeError(f"wm.gltf2_import returned {result2}")
    except Exception as e2:
        print(f"FAIL: import error — primary: {e}  fallback: {e2}")
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

# Map from principled socket label to a readable channel name
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
    """Return dict of channel -> (has_texture, texture_name or None)."""
    channels = {}
    if not mat.use_nodes or mat.node_tree is None:
        return channels
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find Principled BSDF
    principled = next(
        (n for n in nodes if n.type == "BSDF_PRINCIPLED"), None
    )
    if principled is None:
        # Try to find any BSDF-like node
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

        # Walk back through Normal Map nodes
        source = from_node
        if source.type == "NORMAL_MAP":
            # follow its input
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
        # dump all image texture nodes as fallback
        if mat.node_tree:
            img_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"]
            for n in img_nodes:
                img_name = n.image.name if n.image else "(no image)"
                print(f"    TEX_IMAGE node: {n.name!r} -> {img_name}")
    else:
        for chan, tex in sorted(ch.items()):
            print(f"    {chan:20s}: {tex}")

# ── Summary ───────────────────────────────────────────────────
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

print("\n=== PHASE 0 GLB PROBE: COMPLETE ===")
