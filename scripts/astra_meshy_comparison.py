"""Build the approved-reference/final-graft side-by-side without ffmpeg."""
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "face-concepts/godwyn_face_APPROVED.png"
FINAL = ROOT / "renders/astra/char2/meshy_graft_front.png"
OUT = ROOT / "renders/astra/char2/meshy_graft_approved_comparison.png"


def main():
    size = (850, 1266)
    reference = ImageOps.fit(Image.open(REF).convert("RGB"), size, Image.Resampling.LANCZOS)
    final = ImageOps.fit(Image.open(FINAL).convert("RGB"), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1700, 1266), (0, 0, 0))
    canvas.paste(reference, (0, 0))
    canvas.paste(final, (850, 0))
    canvas.save(OUT, quality=95)
    print("MESHY_COMPARISON_PASS", OUT)


if __name__ == "__main__":
    main()
