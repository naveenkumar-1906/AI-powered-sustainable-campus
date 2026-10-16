
from pathlib import Path

import cv2
from ultralytics import YOLO


class CampusVision:
    """CPU-friendly object detection for CleanO Campus."""

    def __init__(
        self,
        model_path="yolo11n.pt",
        confidence=0.35,
        image_size=416,
    ):
        print("Loading YOLO model...")
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.image_size = image_size
        print("YOLO model loaded successfully.")

    def scan_video(self, video_path, frame_stride=5, max_frames=None):
        """
        Analyze a video.

        frame_stride=5 means analyze every fifth frame.
        max_frames limits the number of frames analyzed.
        """

        path = Path(video_path).expanduser()

        if not path.is_file():
            raise FileNotFoundError(
                f"Video not found: {path}\n"
                "Check the filename and location."
            )

        if frame_stride < 1:
            raise ValueError("frame_stride must be at least 1.")

        cap = cv2.VideoCapture(str(path))

        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {path}")

        detections = []
        frame_number = 0
        frames_processed = 0
        people_detected = 0

        try:
            while True:
                ok, frame = cap.read()

                if not ok:
                    break

                frame_number += 1

                if frame_number % frame_stride != 0:
                    continue

                results = self.model.predict(
                    source=frame,
                    imgsz=self.image_size,
                    conf=self.confidence,
                    device="cpu",
                    verbose=False,
                )

                result = results[0]
                frames_processed += 1

                if result.boxes is None:
                    continue

                for box in result.boxes:
                    class_id = int(box.cls.item())
                    confidence = float(box.conf.item())
                    label = result.names[class_id]

                    if label == "person":
                        people_detected += 1

                    x1, y1, x2, y2 = (
                        int(value)
                        for value in box.xyxy[0].tolist()
                    )

                    detections.append(
                        {
                            "frame": frame_number,
                            "label": label,
                            "confidence": round(confidence, 3),
                            "bbox": [x1, y1, x2, y2],
                        }
                    )

                if (
                    max_frames is not None
                    and frames_processed >= max_frames
                ):
                    break

        finally:
            cap.release()

        return {
            "video": path.name,
            "frames_processed": frames_processed,
            "people_detected": people_detected,
            "detections_count": len(detections),
            "detections": detections,
        }
