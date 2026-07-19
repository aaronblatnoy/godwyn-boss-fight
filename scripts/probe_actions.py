"""Check which glbs have animation actions."""
import bpy, sys

glbs = [
    "/home/aaron/godwyn-boss-fight/models/godwyn_xslash.glb",
    "/home/aaron/godwyn-boss-fight/models/godwyn_mocap_combo.glb",
]

for glb in glbs:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    actions = list(bpy.data.actions)
    if actions:
        for a in actions:
            fr = a.frame_range
            print(f"ANIMATED_GLB:{glb} action={a.name} frames={fr[0]:.0f}-{fr[1]:.0f}")
    else:
        print(f"NO_ACTIONS:{glb}")
