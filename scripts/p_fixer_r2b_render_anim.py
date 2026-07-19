"""p_fixer_r2b_render_anim.py — render all 64 frames of the baked X-slash
(godwyn_xslash.blend, body + cape keys) with EEVEE for the preview mp4."""
import bpy, os

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_xslash.blend"))
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 640, 820
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.use_stamp = False
ANIMDIR = os.path.join(REPO, "renders", "xslash", "anim_cape")
os.makedirs(ANIMDIR, exist_ok=True)
sc.render.filepath = os.path.join(ANIMDIR, "f")
sc.frame_start, sc.frame_end = 1, 64
bpy.ops.render.render(animation=True)
print("[render] DONE", ANIMDIR)
