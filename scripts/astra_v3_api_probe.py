"""Print Blender 5.2 glTF animation export controls used by v3."""

import bpy


rna = bpy.ops.export_scene.gltf.get_rna_type()
for prop in rna.properties:
    if "anim" in prop.identifier.lower() or "nla" in prop.identifier.lower() or "action" in prop.identifier.lower():
        enums = [(item.identifier, item.name) for item in getattr(prop, "enum_items", [])]
        print("V3_GLTF_PROP", prop.identifier, "default=", getattr(prop, "default", None), "enum=", enums, flush=True)
