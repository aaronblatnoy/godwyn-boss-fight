"""Second-angle recovery clearance evidence; never saves the blend."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_move_lunge_thrust_wip.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=512;s.render.resolution_percentage=100;s.eevee.taa_render_samples=32;s.render.use_motion_blur=False
s.camera.animation_data_clear();s.camera.location=(3,-10,3.8);s.camera.rotation_euler=(Vector((0,-2.15,1.5))-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=5.8
s.render.use_stamp=True;s.render.use_stamp_frame=True;s.render.use_stamp_filename=False;s.render.use_stamp_date=False;s.render.use_stamp_time=False;s.render.use_stamp_camera=False;s.render.use_stamp_scene=False;s.render.use_stamp_render_time=False;s.render.stamp_font_size=18
out=ROOT/'renders/astra/moves/lunge_thrust/l01_clearance';out.mkdir(parents=True,exist_ok=True)
for i,f in enumerate([37,39,41,43,45,47,49,57,64]):
    s.frame_set(f);s.render.filepath=str(out/f'{i:03d}.png');bpy.ops.render.render(write_still=True)
