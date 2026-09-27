"""Package X-slash cloth render, full decode sheets, and comparison stills."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


args = sys.argv[1:]
root, output = Path(args[0]), Path(args[1])
frames_dir = output / "cloth_frames"
comparisons_dir = output / "cloth_compare_frames"
manifest = json.loads((output / "xslash_manifest.json").read_text())
ffmpeg = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
ffprobe = shutil.which("ffprobe") or "/usr/bin/ffprobe"


def run(command):
    subprocess.run(command, check=True)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


for frame in range(1, 91):
    assert (frames_dir / f"{frame:03d}.png").is_file()
video = output / "xslash_cloth.mp4"
run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
     "-framerate", "30", "-start_number", "1", "-i", str(frames_dir / "%03d.png"),
     "-frames:v", "90", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)])
run([ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-i", str(video),
     "-f", "null", "-"])
probe = json.loads(subprocess.check_output([
    ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format",
    "-of", "json", str(video)], text=True))
stream = probe["streams"][0]
assert stream["codec_name"] == "h264"
assert stream["pix_fmt"] == "yuv420p"
assert stream["r_frame_rate"] == "30/1"
assert int(stream["nb_read_frames"]) == 90
assert [int(stream["width"]), int(stream["height"])] == [768, 768]

with tempfile.TemporaryDirectory(prefix="astra_xslash_cloth_") as temporary_name:
    temporary = Path(temporary_name)
    decoded = temporary / "decoded"
    decoded.mkdir()
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
         "-vsync", "0", str(decoded / "%03d.png")])
    decoded_frames = sorted(decoded.glob("*.png"))
    assert len(decoded_frames) == 90

    # A master sheet plus six larger consecutive sheets prove every MP4 frame.
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
         "-vf", "scale=128:128,tile=10x9:nb_frames=90:padding=2:margin=4:color=0x171b22",
         "-frames:v", "1", str(output / "xslash_cloth_decoded_sheet.png")])
    for sheet in range(6):
        segment = temporary / f"segment_{sheet + 1:02d}"
        segment.mkdir()
        for local, source in enumerate(decoded_frames[sheet * 15:(sheet + 1) * 15], 1):
            shutil.copy2(source, segment / f"{local:03d}.png")
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
             "-framerate", "1", "-i", str(segment / "%03d.png"),
             "-vf", "scale=256:256,tile=5x3:nb_frames=15:padding=4:margin=8:color=0x171b22",
             "-frames:v", "1", str(output / f"xslash_cloth_decoded_{sheet + 1:02d}.png")])

    contact = temporary / "contact"
    contact.mkdir()
    for local, frame in enumerate(manifest["contact_frames"], 1):
        shutil.copy2(frames_dir / f"{frame:03d}.png", contact / f"{local:03d}.png")
    contact_count = len(manifest["contact_frames"])
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         "-framerate", "1", "-i", str(contact / "%03d.png"),
         "-vf", f"scale=256:256,tile=5x4:nb_frames={contact_count}:padding=4:margin=8:color=0x171b22",
         "-frames:v", "1", str(output / "xslash_cloth_contact_sheet.png")])

comparison_paths = []
comparison_meta = json.loads((comparisons_dir / "frames.json").read_text())
for index, frame in enumerate(comparison_meta["frames"], 1):
    destination = output / f"xslash_cloth_floor_before_after_{index:02d}.png"
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(comparisons_dir / f"{index:02d}_before.png"),
         "-i", str(comparisons_dir / f"{index:02d}_after.png"),
         "-filter_complex", "hstack=inputs=2", "-frames:v", "1", str(destination)])
    comparison_paths.append({"frame": frame, "path": str(destination),
                             "layout": "left=before, right=after"})

verification = {
    "execution_host": "black-sky",
    "video": str(video),
    "video_sha256": sha256(video),
    "source_frame_count": 90,
    "decoded_frame_count": 90,
    "decode_error_free": True,
    "decoded_master_sheet": str(output / "xslash_cloth_decoded_sheet.png"),
    "decoded_consecutive_sheets": [str(output / f"xslash_cloth_decoded_{index:02d}.png")
                                    for index in range(1, 7)],
    "contact_sheet": str(output / "xslash_cloth_contact_sheet.png"),
    "contact_frames": manifest["contact_frames"],
    "before_after_stills": comparison_paths,
    "before_after_render": comparison_meta["render"],
    "ffprobe": probe,
}
(output / "xslash_cloth_video_verification.json").write_text(
    json.dumps(verification, indent=2) + "\n")
print("XSLASH CLOTH PACKAGE COMPLETE", json.dumps({
    "video": str(video), "sha256": verification["video_sha256"],
    "decoded_frames": 90, "comparisons": comparison_paths,
}), flush=True)
