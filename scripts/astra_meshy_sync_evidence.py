"""Copy only permitted lightweight Meshy evidence from black-sky to this repo."""
import io
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "renders/astra/char2/"
ALLOWED = {".png", ".json", ".log", ".md"}
remote = subprocess.run(
    ["ssh", "black-sky", "cd ~/godwyn-boss-fight && tar cf - " +
     "renders/astra/char2/meshy_*.png renders/astra/char2/meshy_*.json " +
     "renders/astra/char2/MESHY_GRAFT_REPORT.md renders/astra/char2/codex_meshy_graft.log"],
    check=True, stdout=subprocess.PIPE,
)
with tarfile.open(fileobj=io.BytesIO(remote.stdout), mode="r:") as archive:
    for member in archive.getmembers():
        path = Path(member.name)
        if not member.isfile() or not member.name.startswith(PREFIX) or path.suffix.lower() not in ALLOWED:
            continue
        target = (ROOT / path).resolve()
        if ROOT not in target.parents:
            raise RuntimeError(f"unsafe archive member: {member.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise RuntimeError(f"missing archive content: {member.name}")
        target.write_bytes(source.read())
        print(path)
