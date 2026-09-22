"""Manager-side delivery verification render of the canonical char2 model."""
import bpy, sys
sys.dont_write_bytecode=True
s=bpy.context.scene
s.render.engine='CYCLES'
try: s.cycles.device='GPU'
except Exception: pass
s.cycles.samples=24
s.render.resolution_x=900; s.render.resolution_y=1200
s.view_settings.view_transform='AgX'; s.view_settings.exposure=-0.35
w=bpy.data.worlds.new('verify'); s.world=w; w.use_nodes=True
w.node_tree.nodes['Background'].inputs[0].default_value=(.05,.05,.05,1)
w.node_tree.nodes['Background'].inputs[1].default_value=.6
cam_d=bpy.data.cameras.new('vcam'); cam=bpy.data.objects.new('vcam',cam_d)
s.collection.objects.link(cam); s.camera=cam
cam_d.lens=85; cam.location=(0.35,-6.2,2.35); cam.rotation_euler=(1.4835,0,0.055)
l=bpy.data.lights.new('k','AREA'); l.energy=900; l.size=4
lo=bpy.data.objects.new('k',l); s.collection.objects.link(lo)
lo.location=(3,-5,5); lo.rotation_euler=(0.75,0,0.6)
s.render.filepath='//renders/astra/char2/manager_delivery_check.png'
bpy.ops.render.render(write_still=True)
print('VERIFY_RENDER_OK')
