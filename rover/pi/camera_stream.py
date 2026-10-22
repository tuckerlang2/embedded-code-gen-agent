"""
camera_stream.py
Live MJPEG stream from the Pi Camera Module 3 (IMX708, CSI) for FPV-style
phone viewing while driving with the gamepad. This is view-only -- it does
NOT send drive commands and has no interaction with drive_controller.py,
protocol.py, or the ESP32 link. Losing this stream does not affect the
drive-safety path (the ESP32's own watchdog, per PROTOCOL.md).

Usage:
    python3 camera_stream.py [--port 8080] [--width 640] [--height 480]

Then on your phone (same WiFi network as the Pi):
    http://<pi-ip>:8080/

Requires `picamera2` (installed via apt, not pip -- it's tied to the
system libcamera stack). See rover/README.md for setup.

Adapted from the standard Picamera2 MJPEG streaming example pattern
(threaded capture into a shared buffer, multipart HTTP response).
"""
import argparse
import io
import socketserver
import sys
import time
from http import server
from threading import Condition, Lock

try:
    from picamera2 import Picamera2
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput
except ImportError:
    print("picamera2 not found. Install it with:", file=sys.stderr)
    print("  sudo apt install -y python3-picamera2", file=sys.stderr)
    print("(Must be installed via apt, not pip -- it's tied to the "
          "system libcamera stack.)", file=sys.stderr)
    sys.exit(1)


class StreamingOutput(io.BufferedIOBase):
    """
    Receives JPEG frames from the encoder and hands the latest one to any
    number of waiting HTTP client threads. Only the most recent frame is
    kept -- a slow/disconnected phone should never cause frames to queue
    up and the stream to fall behind in time.
    """

    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            page = (
                b"<!DOCTYPE html><html><head><title>Rover camera</title>"
                b"<style>body{margin:0;background:#111}"
                b"img{width:100%;height:auto;display:block}</style>"
                b"</head><body><img src='/stream.mjpg'></body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=FRAME",
            )
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                # Phone closed the tab / lost WiFi -- not an error, just
                # one fewer viewer. The capture loop keeps running for
                # whoever else is (or isn't) connected.
                pass
        else:
            self.send_error(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # suppress per-request console spam; errors still print via send_error


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


output = None  # set in main() so StreamingHandler can reach it


def main():
    global output

    parser = argparse.ArgumentParser(description="Live MJPEG stream from the Pi Camera Module 3")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--width", type=int, default=640,
                         help="Lower resolution = lower latency over WiFi. "
                              "640x480 is a reasonable FPV starting point; "
                              "raise only after confirming latency is acceptable.")
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--bitrate", type=int, default=4_000_000,
                         help="MJPEG target bitrate in bits/sec. Lower this "
                              "if the Pi Zero 2 W's WiFi can't keep up "
                              "(stream will stutter/lag instead of erroring).")
    args = parser.parse_args()

    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(
        main={"size": (args.width, args.height)}
    )
    picam2.configure(video_config)

    output = StreamingOutput()
    encoder = MJPEGEncoder(bitrate=args.bitrate)
    picam2.start_recording(encoder, FileOutput(output))

    try:
        address = ("", args.port)
        server_instance = StreamingServer(address, StreamingHandler)
        print(f"Streaming at http://<pi-ip>:{args.port}/  "
              f"({args.width}x{args.height}, target {args.bitrate/1e6:.1f} Mbps)")
        server_instance.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down camera stream.")
    finally:
        picam2.stop_recording()


if __name__ == "__main__":
    main()
