"""Webcam capture — returns base64 JPEG frames for vision analysis."""

import cv2
import base64
import time
import threading
from config import CAMERA_INDEX, CAPTURE_RESOLUTION


class CameraCapture:
    def __init__(self):
        self.cap:   cv2.VideoCapture | None = None
        self._lock  = threading.Lock()

    def open(self):
        """Open camera and warm up sensor (auto-exposure settles)."""
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAPTURE_RESOLUTION[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_RESOLUTION[1])
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera at index {CAMERA_INDEX}")
        # Discard first few frames — auto-exposure / auto-white-balance warmup
        for _ in range(8):
            self.cap.read()
            time.sleep(0.05)
        print(f"Camera ready at {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}×"
              f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    def capture_frame(self) -> str:
        """Capture one frame and return as base64-encoded JPEG string."""
        with self._lock:
            if self.cap is None or not self.cap.isOpened():
                raise RuntimeError("Camera not open")
            ret, frame = self.cap.read()
            if not ret:
                raise RuntimeError("Failed to read frame from camera")
            # Encode as JPEG (quality 85 — good balance for API upload)
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buf).decode("utf-8")

    def capture_to_file(self, path: str = "static/latest_scan.jpg") -> str:
        """Save the latest frame to disk; returns file path."""
        with self._lock:
            if self.cap is None:
                raise RuntimeError("Camera not open")
            ret, frame = self.cap.read()
            if ret:
                cv2.imwrite(path, frame)
                return path
        raise RuntimeError("Capture failed")

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
