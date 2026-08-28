from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


MAX_README_CHARS = 1000
MAX_VIDEO_BYTES = 200 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and package assignment submission files.")
    parser.add_argument("--video", type=Path, help="Path to the MP4 demo video recorded by the student.")
    parser.add_argument("--name", default="submission", help="Output zip base name. Use the required real name at final submission time.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    readme = root / "README.txt"
    if not readme.is_file():
        raise SystemExit("README.txt is missing")
    readme_text = readme.read_text(encoding="utf-8")
    if len(readme_text) > MAX_README_CHARS:
        raise SystemExit(f"README.txt is {len(readme_text)} characters; keep it within {MAX_README_CHARS}")

    print(f"OK README.txt: {len(readme_text)} characters")
    if args.video is None:
        print("No video provided. Record an MP4 under 2 minutes and rerun with --video path\\to\\demo.mp4")
        return 0

    video = args.video.resolve()
    if not video.is_file():
        raise SystemExit(f"video file not found: {video}")
    if video.suffix.lower() != ".mp4":
        raise SystemExit("video must be an .mp4 file")
    size = video.stat().st_size
    if size > MAX_VIDEO_BYTES:
        raise SystemExit(f"video is {size} bytes; keep it under {MAX_VIDEO_BYTES} bytes")

    output_dir = root / "submission"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f"{args.name}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(readme, "README.txt")
        archive.write(video, video.name)
    print(f"OK video: {size / (1024 * 1024):.1f} MB")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
