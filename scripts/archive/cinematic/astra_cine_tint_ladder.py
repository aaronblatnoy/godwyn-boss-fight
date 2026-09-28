"""Three authorized frame-41 tint renders; load canonical inputs once, no saves."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import argparse,json,time,bpy
import astra_cine_render as cine
import astra_cine_hero_render as hero
RUNG={'A':(.03,.05,.30),'B':(.02,.03,.23),'C':(.05,.07,.40)}
p=argparse.ArgumentParser()
p.add_argument('--blend',type=Path,default=hero.ROOT/'models/astra_xslash_v2_final_wip.blend')
p.add_argument('--character-blend',type=Path,default=hero.ROOT/'models/astra_character_v2.blend')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assert bpy.app.background
cine.enforce_local_hold([41,41,41]);cine.configure_device(bpy.context.scene,'METAL')
scene,inputs=hero.assemble_inputs(a.blend.resolve(),a.character_blend.resolve())
settings=argparse.Namespace(device='METAL',allow_cpu=False,width=1920,height=1080,samples=512,threshold=.01,haze=0,key=1,rim=1,fill=.6,rake=.6,azimuth=16,tint=RUNG['A'])
proof=cine.configure(scene,settings);scene.frame_set(41);bpy.context.view_layer.update()
state=hero.treatment_state(scene)
out=cine.OUT/'indigo_ladder';out.mkdir(parents=True,exist_ok=True)
report={'inputs':inputs,'settings':proof,'frames':[]}
for name,tint in RUNG.items():
    override=cine.apply_blue_override(scene,tint);bpy.context.view_layer.update()
    assert hero.treatment_state(scene)==state,'Only tint socket values may change'
    cine.assert_device(scene,'METAL')
    path=out/f'indigo_{name}_f041.png';scene.render.filepath=str(path)
    start=time.perf_counter();bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-start
    cine.assert_device(scene,'METAL')
    item={'rung':name,'tint':tint,'frame':41,'path':str(path),'wall_seconds':elapsed,'blue_override':override}
    report['frames'].append(item);(out/'ladder_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CINE_LADDER_FRAME '+json.dumps(item),flush=True)
print('CINE LADDER COMPLETE: exactly three frames; no model saves',flush=True)
