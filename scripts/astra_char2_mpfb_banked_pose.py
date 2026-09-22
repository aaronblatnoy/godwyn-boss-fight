"""Same permitted synthetic stress pose on the immutable approved banked baseline."""
import bpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_validate import pose,draw
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_collar_banked.blend'))
pose(bpy.data.objects['Armature'],'combat_stress');draw('mpfb_banked_combat_stress')
