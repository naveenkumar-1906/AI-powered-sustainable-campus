
from pathlib import Path
import json

from services.vision import CampusVision


BACKEND_DIR = Path(__file__).resolve().parent
VIDEO_DIR = BACKEND_DIR / "data" / "videos"


def main():
    videos = sorted(VIDEO_DIR.glob("*.mp4"))

    if not videos:
        print(f"No MP4 video found in: {VIDEO_DIR}")
        print("Place an .mp4 file in that folder and try again.")
        return

    video_path = videos[0]
    print(f"Testing video: {video_path.name}")

    vision = CampusVision()

    report = vision.scan_video(
        video_path=video_path,
        frame_stride=5,
        max_frames=30,
    )

    print("\nDetection summary:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
