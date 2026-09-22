import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_sword import place_sword
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/godwyn_game.glb'));reset_pose();setup();place_sword(bpy.data.objects['Godwyn_Sword'],False)
for name in VIEWS:render_view('before',name)
