"""Create the mandated approved-reference/candidate comparison on black-sky."""
import sys
from pathlib import Path
from PIL import Image

root = Path.cwd()
out = root / 'renders/astra/char2'
iteration = int(sys.argv[1])
old = Image.open(out / 'mpfb_approved_comparison.png').convert('RGB')
reference = old.crop((0, 0, old.width // 2, old.height))
candidate = Image.open(out / f'likeness_i{iteration:02}_front.png').convert('RGB')
if candidate.size != reference.size:
    candidate = candidate.resize(reference.size, Image.Resampling.LANCZOS)
comparison = Image.new('RGB', (reference.width * 2, reference.height), (20, 20, 20))
comparison.paste(reference, (0, 0))
comparison.paste(candidate, (reference.width, 0))
comparison.save(out / f'likeness_i{iteration:02}_approved_comparison.png', quality=96)
print('LIKENESS_COMPARISON_PASS', iteration)
