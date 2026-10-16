from pathlib import Path
import tempfile

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from ultralytics import YOLO

router = APIRouter(prefix="/api/camera", tags=["CCTV Analysis"])

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BACKEND_DIR / "yolo11n.pt"

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm", ".mkv"}

# COCO model classes useful for a basic first-pass campus prototype.
# This model cannot reliably identify water leakage, electricity wastage,
# streetlight faults, or overflowing bins.
TRASH_RELATED_CLASSES = {
    "bottle",
    "cup",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
}

model = None


def get_model():
    global model

    if model is None:
        if not MODEL_PATH.is_file():
            raise HTTPException(
                status_code=500,
                detail=f"YOLO model file not found: {MODEL_PATH}",
            )

        try:
            model = YOLO(str(MODEL_PATH))
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Could not load YOLO model: {exc}",
            ) from exc

    return model


@router.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    block: str = Form(default="Block A"),
):
    filename = file.filename or "uploaded_video.mp4"
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload an MP4, MOV, AVI, WEBM or MKV video.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded video is empty.")

    if len(contents) > 200 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Video must be smaller than 200 MB.",
        )

    temp_path = None
    cap = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as temp_file:
            temp_file.write(contents)
            temp_path = temp_file.name

        cap = cv2.VideoCapture(temp_path)

        if not cap.isOpened():
            raise HTTPException(
                status_code=400,
                detail="Could not open this video. Try another video file.",
            )

        detector = get_model()

        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 25.0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        # Keep one latest record per tracker ID, instead of counting
        # the same tracked object again on every frame.
        tracked_objects = {}
        frames_processed = 0
        frame_number = 0
        frame_step = 3

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame_number += 1

            if frame_number % frame_step != 0:
                continue

            results = detector.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                imgsz=416,
                device="cpu",
                conf=0.30,
                verbose=False,
            )

            frames_processed += 1
            result = results[0]
            boxes = result.boxes

            if boxes is None or len(boxes) == 0:
                continue

            # Tracking IDs may be unavailable for a frame; skip it
            # rather than counting frame detections as unique objects.
            if boxes.id is None:
                continue

            track_ids = boxes.id.int().cpu().tolist()
            class_ids = boxes.cls.int().cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            coordinates = boxes.xyxy.cpu().tolist()

            for track_id, class_id, confidence, bbox in zip(
                track_ids, class_ids, confidences, coordinates
            ):
                label = result.names[int(class_id)]

                # No vehicle detections are included in our results.
                if label != "person" and label not in TRASH_RELATED_CLASSES:
                    continue

                key = f"{label}_{int(track_id)}"

                tracked_objects[key] = {
                    "track_id": int(track_id),
                    "label": label,
                    "confidence": round(float(confidence), 3),
                    "bbox": [round(float(value), 1) for value in bbox],
                    "last_seen_frame": frame_number,
                    "last_seen_seconds": round(frame_number / fps, 2),
                }

        findings = list(tracked_objects.values())

        people_count = sum(
            1 for item in findings if item["label"] == "person"
        )
        possible_trash_objects = sum(
            1 for item in findings if item["label"] in TRASH_RELATED_CLASSES
        )

        # These issues cannot be reliably confirmed by the generic
        # COCO model, so never invent detection counts for them.
        sustainability_counts = {
            "water_leakage": None,
            "electricity_wastage": None,
            "overflowing_trash": None,
        }

        recommendations = []

        if possible_trash_objects:
            recommendations.append({
                "category": "possible_trash",
                "suggestion": (
                    "Review the detected objects in the footage. If litter "
                    "or an overflowing bin is confirmed, arrange a cleanup "
                    "and inspect nearby waste bins."
                ),
            })

        if not recommendations:
            recommendations.append({
                "category": "manual_review",
                "suggestion": (
                    "Review the footage for leaks, lights left on, and "
                    "overflowing bins. The current general-purpose model "
                    "cannot confirm those problems automatically."
                ),
            })

        return {
            "message": "Video analysis completed.",
            "filename": filename,
            "block": block,
            "frames_processed": frames_processed,
            "total_frames": total_frames,
            "unique_objects": len(findings),
            "counts": {
                "person": people_count,
                "possible_trash_objects": possible_trash_objects,
            },
            "sustainability_counts": sustainability_counts,
            "findings": findings,
            "recommendations": recommendations,
            "limitations": [
                "Tracking can occasionally assign a new ID to the same object.",
                "Detected food containers or bottles do not automatically prove litter.",
                "Water leakage and electricity wastage require suitable specialist detection.",
                "Streetlight faults and overflowing bins are not reliably confirmed by this model.",
                "Review footage before creating an official campus issue.",
            ],
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Video analysis failed: {exc}",
        ) from exc
    finally:
        if cap is not None:
            cap.release()

        if temp_path:
            Path(temp_path).unlink(missing_ok=True)