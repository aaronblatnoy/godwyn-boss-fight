"""
p0_vlm_probe_sheet.py — Build a labeled 4x4 grid sheet for VLM panel-count sanity probe.
Takes the front contact sheet, splits into individual panels, and rebuilds as a 4x4 grid
with each panel labeled "P1" through "P16". Uses PIL (pillow).
Ground truth: 16 panels.
"""
import sys
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

# Use the existing front contact sheet as source (it's already 1024x1024 with 4x4 panels)
src = "/tmp/godwyn_vlm_probe_front.jpg"
out = "/tmp/p0_vlm_panel_probe_4x4.jpg"

if not os.path.exists(src):
    # Fallback: just make 16 copies of the eevee assert
    src = "/tmp/p0_eevee_assert.png"
    if not os.path.exists(src):
        # Create a tiny black image as fallback
        img = Image.new("RGB", (64, 64), color=(30, 30, 30))
        img.save("/tmp/p0_fake_frame.png")
        src = "/tmp/p0_fake_frame.png"

# Open source
src_img = Image.open(src).convert("RGB")

# Build a fresh 4x4 labeled grid
panel_w, panel_h = 256, 256
grid_w, grid_h = 4 * panel_w, 4 * panel_h
grid = Image.new("RGB", (grid_w, grid_h), color=(10, 10, 10))
draw = ImageDraw.Draw(grid)

# Try to get a font, fall back to default
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except Exception:
    try:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

# Tile 16 panels with labels
panel_idx = 1
for row in range(4):
    for col in range(4):
        # Crop a panel from the source (tile from the source sheet)
        src_x = (col * src_img.width) // 4
        src_y = (row * src_img.height) // 4
        src_x2 = ((col + 1) * src_img.width) // 4
        src_y2 = ((row + 1) * src_img.height) // 4
        panel = src_img.crop((src_x, src_y, src_x2, src_y2)).resize((panel_w, panel_h))

        # Draw border
        panel_draw = ImageDraw.Draw(panel)
        panel_draw.rectangle([(0, 0), (panel_w-1, panel_h-1)], outline=(255, 200, 0), width=3)
        panel_draw.text((8, 8), f"P{panel_idx}", fill=(255, 255, 0), font=font)

        grid.paste(panel, (col * panel_w, row * panel_h))
        panel_idx += 1

grid.save(out, quality=92)
print(f"VLM_PROBE_SHEET:{out}")
print(f"Ground truth: 16 panels in a 4x4 grid")
