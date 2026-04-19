import subprocess
import os
import base64
import time

class CameraCapture:
    def __init__(self):
        self.latest_path = "/home/ubuntu/smart_pantry/static/latest_scan.jpg"

    def open(self):
        # We don't need to keep a 'stream' open with GStreamer for this setup
        print("[camera] GStreamer pipeline ready for Rubik Pi")
        return True

    def capture_frame(self):
        """Captures a frame using the verified 5-second soak pipeline."""
        cmd = f"timeout --signal=SIGINT 5s gst-launch-1.0 qtiqmmfsrc ! video/x-raw,format=NV12,width=1280,height=720 ! videoconvert ! jpegenc ! multifilesink location={self.latest_path} max-files=1"
        try:
            subprocess.run(cmd, shell=True, check=True)
            if os.path.exists(self.latest_path):
                with open(self.latest_path, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"[camera] Capture error: {e}")
        return ""

    def capture_to_file(self, path):
        # The file is already saved by capture_frame to the static folder
        return True

    def close(self):
        pass
