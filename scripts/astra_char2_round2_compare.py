"""Locked approved-reference camera and local ffmpeg side-by-side test."""
import bpy,sys,json,subprocess,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_render import configure
from astra_character_common import aim,reset_pose
CAM={'location':(0,-5,2.900),'target':(0,-.30,2.900),'scale':.650,'resolution':(848,1264)}
def portrait_lights():
 # Reference-matched diagnostic portrait rig, held fixed across all comparisons.
 # Gameplay lighting and the standard full-body review remain untouched on disk.
 for name,loc,power,color,size in [
  ('Astra key',(-1.7,-2.8,3.8),240,(1,.88,.73),1.5),
  ('Astra fill',(1.7,-2.5,3.1),22,(.87,.91,1),1.8),
  ('Astra rim',(1,1.2,3.5),90,(1,.82,.58),1.4),
  ('Astra face',(0,-3.0,3.3),6,(1,.92,.84),1.2)]:
  o=bpy.data.objects[name];o.location=loc;o.data.energy=power;o.data.color=color;o.data.size=size;aim(o,(0,-.3,2.98))
 bg=bpy.context.scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.012,.014,.017,1);bg.inputs[1].default_value=.12
 bpy.data.objects['Astra evaluation ground'].hide_render=True

def compare(stage):
 s=configure();reset_pose();portrait_lights();s.render.resolution_x=848;s.render.resolution_y=1264;s.cycles.samples=48
 s.camera.location=CAM['location'];aim(s.camera,CAM['target']);s.camera.data.type='ORTHO';s.camera.data.ortho_scale=CAM['scale']
 s.render.filepath=str(OUT/(stage+'_face.png'));bpy.ops.render.render(write_still=True)
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(ROOT/'face-concepts/godwyn_face_APPROVED.png'),'-i',s.render.filepath,'-filter_complex','[0:v][1:v]hstack=inputs=2[out]','-map','[out]','-frames:v','1','-y',str(OUT/'sidebyside_face.png')],check=True)
 shutil.copy2(OUT/'sidebyside_face.png',OUT/(stage+'_sidebyside.png'))
 (OUT/'round2_camera.json').write_text(json.dumps({'camera':CAM,'source':'Only godwyn_face_APPROVED.png','comparison':'unwarped 848x1264 reference left, actual 848x1264 Blender render right','lighting':'fixed reference portrait lighting; AgX -0.35; local Cycles METAL 48 samples'},indent=2))
 print('COMPARISON',stage,flush=True)
if __name__=='__main__':
 stage=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'r2_baseline'
 src=ROOT/'models/astra_character_v2_round2_input.blend'
 if not src.exists():
  shutil.copy2(ROOT/'models/astra_character_v2.blend',src);shutil.copy2(ROOT/'models/astra_character_v2.glb',ROOT/'models/astra_character_v2_round2_input.glb')
 bpy.ops.wm.open_mainfile(filepath=str(src));compare(stage)
