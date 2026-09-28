import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
for im in bpy.data.images:
 path=Path(bpy.path.abspath(im.filepath_raw))
 if path.parent==OUT/'textures' and (path.name.startswith('astra_character_char1_') or path.name.startswith('astra_character_Astra_Undersleeves_')):
  if im.packed_file:im.unpack(method='REMOVE')
  im.reload();im.pack();print('RELOADED',im.name,flush=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
