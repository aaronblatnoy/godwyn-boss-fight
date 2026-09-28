"""Compose the required God A concept versus body-i01 comparison."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "body-concepts/god_A.png"
CANDIDATE = ROOT / "renders/astra/char2/meshy_body_i01_front.png"
OUTPUT = ROOT / "renders/astra/char2/meshy_body_i01_comparison.png"
HEIGHT = 1800
HEADER = 84
GAP = 24


def fit_height(image):
    width = round(image.width * HEIGHT / image.height)
    return image.resize((width, HEIGHT), Image.Resampling.LANCZOS)


def main():
    reference = fit_height(Image.open(REFERENCE).convert("RGB"))
    candidate = fit_height(Image.open(CANDIDATE).convert("RGB"))
    canvas = Image.new("RGB", (reference.width + GAP + candidate.width, HEIGHT + HEADER), "#11141a")
    canvas.paste(reference, (0, HEADER))
    canvas.paste(candidate, (reference.width + GAP, HEADER))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    draw.text((24, 22), "TARGET: god_A", fill="#f1d58b", font=font)
    draw.text((reference.width + GAP + 24, 22), "CANDIDATE: meshy_body_i01", fill="#f1d58b", font=font)
    canvas.save(OUTPUT, compress_level=3)
    print("BODY_COMPARISON_PASS", OUTPUT, canvas.size, flush=True)


if __name__ == "__main__":
    main()
