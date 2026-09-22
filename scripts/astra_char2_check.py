import bpy,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_audit import audit
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_char2_work.blend'));audit()
