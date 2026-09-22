import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(ROOT/'scripts'))
import astra_character_common as c
OUT=ROOT/'renders/astra/char2'
def configure():
 s=bpy.context.scene
 if not s.camera:c.setup()
 c.OUT=OUT
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.cycles.max_bounces=6;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3;s.cycles.transmission_bounces=4
 s.view_settings.view_transform='AgX';s.view_settings.exposure=-.35
 s.render.resolution_x=s.render.resolution_y=960;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG';s.render.threads_mode='FIXED';s.render.threads=8
 pref=bpy.context.preferences.addons['cycles'].preferences
 try:
  pref.compute_device_type='METAL';pref.get_devices();ds=[d for d in pref.devices if d.type=='METAL']
  for d in pref.devices:d.use=d.type=='METAL'
  s.cycles.device='GPU' if ds else 'CPU'
 except Exception:s.cycles.device='CPU';ds=[]
 print('LOCAL CYCLES',s.cycles.device,[d.name for d in ds],flush=True)
 c.VIEWS['face_three_quarter']=((2.9,-5,3.15),(0,-.25,2.99),.59)
 return s
def render(stage,views):
 configure()
 for v in views:c.render_view(stage,v)
if __name__=='__main__':
 args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['before','face','front']
 stage=args[0];src=ROOT/('models/astra_character_v2_prechar2.blend' if stage=='before' else 'models/astra_character_v2.blend')
 bpy.ops.wm.open_mainfile(filepath=str(src));render(stage,args[1:])
