"""Run the proven MPFB native/round-trip validation with an asserted OptiX studio."""
import sys
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
sys.path.insert(0, str(ROOT / 'scripts'))

import astra_char2_mpfb_validate as validation
import astra_likeness_render as likeness_render

validation.R = ROOT
validation.O = OUT


def gpu_studio(clay=False, samples=32, width=900):
    scene, devices = likeness_render.studio()
    scene.cycles.samples = samples
    scene.render.resolution_x = width
    scene.render.resolution_y = round(width * 1.22)
    assert devices and all(d['type'] == 'OPTIX' for d in devices)
    return scene


validation.studio = gpu_studio
args = sys.argv[sys.argv.index('--') + 1:]
validation.main(args[0], args[1], len(args) > 2 and args[2] == 'roundtrip')
