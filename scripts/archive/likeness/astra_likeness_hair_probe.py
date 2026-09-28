"""Report per-group stress stretch after likeness guide changes."""
import bpy
import sys
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
sys.path.insert(0, str(ROOT / 'scripts'))
import astra_char2_mpfb_validate as validation

validation.R = ROOT
validation.O = OUT
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'models/astra_character_v2_likeness_i05.blend'))
arm = bpy.data.objects['Armature']
report = validation.hair_check(arm)
(OUT / 'likeness_hair_probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v['segment_stretch_max'] for k, v in report.items()}, indent=2), flush=True)
