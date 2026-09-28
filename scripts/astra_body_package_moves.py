"""Package and verify the two required body-i02 EEVEE move films."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/rehost_body_i02"
JOBS = {"rising_spin": 116, "xslash": 90}
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/usr/bin/ffprobe"


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run(command):
    subprocess.run(command, check=True)


def package(name, frame_count):
    folder = OUT / f"{name}_frames"
    for frame in range(1, frame_count + 1):
        assert (folder / f"{frame:03d}.png").is_file()
    video = OUT / f"{name}.mp4"
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-start_number", "1", "-i", str(folder / "%03d.png"),
        "-frames:v", str(frame_count), "-c:v", "libx264", "-crf", "17", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video),
    ])
    run([FFMPEG, "-hide_banner", "-loglevel", "error", "-xerror", "-i", str(video),
         "-f", "null", "-"])
    probe = json.loads(subprocess.check_output([
        FFPROBE, "-v", "error", "-count_frames", "-show_streams", "-show_format",
        "-of", "json", str(video),
    ], text=True))
    stream = next(item for item in probe["streams"] if item["codec_type"] == "video")
    assert stream["codec_name"] == "h264"
    assert stream["pix_fmt"] == "yuv420p"
    assert stream["r_frame_rate"] == "30/1"
    assert int(stream["nb_read_frames"]) == frame_count
    assert [int(stream["width"]), int(stream["height"])] == [768, 768]
    result = {
        "path": str(video.relative_to(ROOT)),
        "sha256": sha256(video),
        "source_frames": frame_count,
        "decoded_frames": int(stream["nb_read_frames"]),
        "decode_error_free": True,
        "codec": stream["codec_name"],
        "pixel_format": stream["pix_fmt"],
        "resolution": [int(stream["width"]), int(stream["height"])],
        "fps": stream["r_frame_rate"],
    }
    print("BODY_MOVE_VIDEO", name, json.dumps(result), flush=True)
    return result


def main():
    results = {name: package(name, frames) for name, frames in JOBS.items()}
    (OUT / "meshy_body_videos.json").write_text(json.dumps({
        "execution_host": "black-sky",
        "videos": results,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
