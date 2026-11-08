"""Use the frontend console ticket protocol; serial ownership stays in ECW/RM."""

import json
import os
from pathlib import Path
import re
import sys
import time
import threading
import urllib.request
from urllib.parse import urlsplit
import uuid

from hil_csv import read_csv, sensor_profile
from run_demo import ARTIFACTS, command, read_member, save


def console_base():
    value = os.environ.get("ECW_CONSOLE_URL", "wss://plovdiv.edgebench.io").rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme != "wss" or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError("ECW_CONSOLE_URL must be a credential-free wss:// base URL")
    return value


class Console:
    def __init__(self, demo):
        self.demo = demo
        self.connection = None
        self.transcript = ""
        self.pending = ""

    def __enter__(self):
        from websockets.sync.client import connect
        base = console_base()
        ticket = self.demo.request(f"/console/{self.demo.booking_id}/ticket", method="POST")["ticket"]
        self.connection = connect(
            f"{base}/console/{self.demo.booking_id}",
            subprotocols=["console-ticket", f"console-ticket.{ticket}"],
            open_timeout=20, close_timeout=5, proxy=None,
        )
        try:
            if self.connection.subprotocol != "console-ticket":
                raise RuntimeError("Console did not negotiate ticket authentication")
            # The WebSocket opens before RM has finished claiming the serial device.
            self.wait(r"\[Connected to [^\r\n]+\]", timeout=30)
            return self
        except BaseException:
            self.connection.close()
            raise

    def __exit__(self, *_):
        try:
            if self.connection:
                self.connection.close()
        finally:
            ARTIFACTS.mkdir(exist_ok=True)
            (ARTIFACTS / "console.log").write_text(self.transcript, encoding="utf-8")

    def wait(self, pattern, timeout=10):
        deadline = time.monotonic() + timeout
        while True:
            match = re.search(pattern, self.pending)
            if match:
                self.pending = self.pending[match.end():]
                return match
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("No matching DUT response on the ECW console")
            frame = self.connection.recv(timeout=remaining)
            text = frame.decode("utf-8", errors="replace") if isinstance(frame, bytes) else frame
            self.transcript += text
            self.pending += text
            if len(self.transcript) > 4 * 1024 * 1024:
                raise RuntimeError("Console exceeded the demo's four-MiB output budget")

    def send(self, text):
        self.connection.send("\r\n" + text + "\r\n")


def verify_hil(readings, expected):
    """Require one complete 50-sample CSV cycle, allowing only its starting offset."""
    if len(expected) != 50 or len(readings) != 50:
        raise RuntimeError("Expected exactly 50 CSV samples and 50 DUT samples")
    for offset in range(50):
        if all(row == expected[(index + offset) % 50] for index, row in enumerate(readings)):
            return {"samples": 50, "csv_start_offset": offset, "verified": "DUT SPI words equal CSV encoding"}
    raise RuntimeError("DUT's 50 BME280 readings do not match a complete cycle of the frontend CSV")


class Camera:
    """Continuously consume one authenticated backend MJPEG stream, keeping its latest frame."""
    def __init__(self, demo):
        self.demo = demo
        self.latest = None
        self.sequence = 0
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.error = None
        self.response = None

    def __enter__(self):
        self.worker = threading.Thread(target=self.read, daemon=True, name="demo-camera")
        self.worker.start()
        if not self.ready.wait(15) or self.error or self.latest is None:
            self.__exit__()
            raise RuntimeError("No usable JPEG from the booking's video stream")
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.worker.join(timeout=1)
        if self.worker.is_alive() and self.response:
            self.response.close()
        self.worker.join(timeout=1)

    def read(self):
        try:
            request = urllib.request.Request(
                f"{self.demo.base}/video/{self.demo.booking_id}",
                headers={"X-API-Key": self.demo.key, "User-Agent": "ecw-ra6-ci-demo"})
            with urllib.request.urlopen(request, timeout=5) as response:
                self.response = response
                if "multipart/x-mixed-replace" not in response.headers.get("Content-Type", ""):
                    raise RuntimeError("The booking video endpoint did not return MJPEG")
                buffer = b""
                while not self.stop.is_set():
                    chunk = response.read1(65536)
                    if not chunk:
                        raise RuntimeError("The camera stream ended")
                    buffer += chunk
                    if len(buffer) > 10 * 1024 * 1024:
                        raise RuntimeError("Camera frame exceeded ten MiB")
                    while True:
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9", max(start, 0))
                        if start < 0 or end < 0:
                            break
                        frame, buffer = buffer[start:end + 2], buffer[end + 2:]
                        with self.lock:
                            self.sequence += 1
                            self.latest = (frame, self.sequence, time.monotonic())
                        self.ready.set()
        except Exception as error:
            self.error = type(error).__name__
            self.ready.set()


def sample_camera(camera, *, clock=time.monotonic, sleep=time.sleep):
    """67 scheduled screenshots: 0,30,...,1980 ms, over a two-second window."""
    from PIL import Image
    import hashlib
    import io
    frames = ARTIFACTS / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    started = clock()
    records = []
    for index, target_ms in enumerate(range(0, 2000, 30)):
        sleep(max(0, started + target_ms / 1000 - clock()))
        with camera.lock:
            frame, sequence, received_at = camera.latest
        captured_at = clock()
        filename = f"frame-{index:03d}.jpg"
        (frames / filename).write_bytes(frame)
        records.append({"file": filename, "target_ms": target_ms,
                        "captured_ms": round((captured_at - started) * 1000, 3),
                        "source_sequence": sequence,
                        "frame_age_ms": round((captured_at - received_at) * 1000, 3),
                        "sha256": hashlib.sha256(frame).hexdigest()})
    sleep(max(0, started + 2 - clock()))
    unique = len({r["source_sequence"] for r in records})
    evidence = {"duration_ms": 2000, "screenshot_interval_ms": 30, "led_toggle_ms": 50,
                "screenshots": len(records), "distinct_source_frames": unique,
                "fresh_frame_every_slot": unique == len(records), "frames": records,
                "validation": "Scheduled screenshots; repeated source frames explicitly recorded. Visual LED review."}
    save("verification.json", evidence)
    gallery = "\n".join(
        f'<figure><img loading="lazy" src="frames/{r["file"]}" alt="Screenshot at {r["target_ms"]} ms">'
        f'<figcaption>{r["target_ms"]} ms · source frame {r["source_sequence"]} · '
        f'age {r["frame_age_ms"]} ms</figcaption></figure>' for r in records
    )
    (ARTIFACTS / "camera.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>RA6 camera evidence</title>'
        '<style>body{background:#0b1220;color:#eef3ff;font:16px system-ui;margin:24px}'
        'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}'
        'figure{margin:0}img{width:100%}figcaption{padding:8px}</style>'
        f'<h1>RA6 · LED toggle 50 ms · screenshots every 30 ms for 2 s</h1>'
        f'<p>{len(records)} saved screenshots; {unique} distinct source frames. '
        'Repeated source frames indicate the camera or network supplied fewer frames than the save schedule. '
        'Review the LED visually; optical state is not automatically inferred.</p>'
        f'<main>{gallery}</main></html>', encoding="utf-8")
    for filename in {r["file"] for r in records}:
        with Image.open(frames / filename) as image:
            image.verify()
    if camera.error or unique < 2:
        raise RuntimeError("Camera stalled during the two-second capture")
    return evidence


def test_blinky(demo):
    with Camera(demo) as camera, Console(demo) as console:
        try:
            nonce = uuid.uuid4().hex
            console.send(f"led blink {nonce}")
            console.wait(rf"ECW_LED BLINK 50 {nonce}\r?\n")
            sample_camera(camera)
        finally:
            had_error = sys.exc_info()[0] is not None
            try:
                stop_nonce = uuid.uuid4().hex
                console.send(f"led off {stop_nonce}")
                console.wait(rf"ECW_LED OFF {stop_nonce}\r?\n", timeout=5)
            except Exception:
                if not had_error:
                    raise


def test_hil(demo):
    words, samples = read_csv(Path(".github/user/hil/bme280.csv"), sensor_profile("BME280"))
    if samples != 50:
        raise RuntimeError("The demo CSV must contain exactly 50 samples")
    expected = [tuple(words[i:i + 3]) for i in range(0, len(words), 3)]
    readings = []
    with Console(demo) as console:
        nonce = uuid.uuid4().hex
        console.send(f"hil info {nonce}")
        console.wait(rf"ECW_HIL_ID 60 {nonce}\r?\n")
        for index in range(50):
            nonce = uuid.uuid4().hex
            console.send(f"hil read {nonce}")
            match = console.wait(rf"ECW_HIL_SAMPLE ([0-9A-F]{{4}}) ([0-9A-F]{{4}}) ([0-9A-F]{{4}}) {nonce}\r?\n")
            readings.append(tuple(int(value, 16) for value in match.groups()))
            # Save partial evidence before validation so failed runs remain inspectable.
            save("hil-readings.json", {"readings": readings, "count": index + 1})
            time.sleep(0.1)
    save("verification.json", verify_hil(readings, expected))
