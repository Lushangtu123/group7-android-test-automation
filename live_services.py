"""Ephemeral current-device frames and bounded reads from real execution logs."""

import collections, os, re, subprocess, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from console_core import public_text, readjson, sdk_paths, preview_allowed


def appium_log_source(root):
    if os.environ.get("GROUP7_APPIUM_LOG"):
        return Path(os.environ["GROUP7_APPIUM_LOG"])
    candidates = [
        root / "runtime/services/appium.log",
        root.parent / "Group7_Demo_Console/runtime/services/appium.log",
        root.parents[1] / "work/logs/appium.log",
    ]
    return next((p for p in candidates if p.is_file()), candidates[0])


def screen_visibility(xml, prompt, context):
    return {
        "allowed": bool(
            context.get("attempt_id")
            and context.get("turn")
            and prompt
            and preview_allowed(xml, [prompt])
        ),
        "observed_epoch": time.time(),
        "attempt_id": context.get("attempt_id"),
        "turn": context.get("turn"),
    }


def job_guard(manager, run_id):
    try:
        folder = manager.directory(run_id)
        job = readjson(folder / "job.json", {})
        meta = readjson(folder / "execution_metadata.json", {})
        return {
            **readjson(folder / "screen_visibility.json", {}),
            "ended": job.get("state") in ("COMPLETED", "INTERRUPTED", "PROCESS_ERROR")
            or bool(meta.get("ended_utc")),
        }
    except (ValueError, OSError):
        return {"allowed": False, "ended": True}


def capture_device():
    _, adb = sdk_paths()
    from console_core import ROOT

    config = readjson(ROOT / "engine/data/android_appium_config.local.json", {})
    device = (
        config.get("apps", {})
        .get("chatgpt", {})
        .get("capabilities", {})
        .get("appium:udid", "emulator-5554")
    )
    p = subprocess.run(
        [str(adb), "-s", device, "exec-out", "screencap", "-p"], capture_output=True, timeout=2
    )
    if p.returncode or not p.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Current Android frame is unavailable")
    return p.stdout


class DeviceMirror:
    def __init__(
        self, capture=capture_device, guard=None, clock=time.time, target_fps=5, on_end=None
    ):
        self.capture = capture
        self.guard = guard or (lambda _: {"allowed": False})
        self.clock = clock
        self.period = 1 / target_fps
        self.on_end = on_end
        self.lock = threading.RLock()
        self.thread = None
        self.signal = threading.Event()
        self.running = False
        self.run_id = None
        self.latest = None
        self.state = "OFF"
        self.seq = 0
        self.error = ""
        self.times = collections.deque(maxlen=30)
        self.latencies = []
        self.finished = False

    def start(self, run_id, background=True):
        with self.lock:
            if self.running:
                if self.run_id != run_id:
                    raise RuntimeError("A different device mirror is active")
                return self.status()
            self.run_id = run_id
            self.stream_id = uuid.uuid4().hex[:10]
            self.running = True
            self.finished = False
            self.signal = threading.Event()
            self.latest = None
            self.seq = 0
            self.state = "STARTING"
            self.error = ""
            self.times.clear()
            self.latencies = []
            self.began = self.clock()
            if background:
                self.thread = threading.Thread(
                    target=self._loop, args=(self.signal, self.stream_id), daemon=True
                )
                self.thread.start()
            return self.status()

    def _loop(self, signal, stream_id):
        try:
            while not signal.is_set():
                began = time.monotonic()
                self.capture_once()
                signal.wait(max(0, self.period - (time.monotonic() - began)))
        finally:
            self._finish(stream_id)

    def capture_once(self):
        with self.lock:
            if not self.running:
                return
            guard = self.guard(self.run_id)
            if guard.get("ended"):
                self.running = False
                self.state = "ENDED"
                self.signal.set()
                self._finish()
                return
            if not guard.get("allowed") or self.clock() - guard.get("observed_epoch", 0) > 3:
                self.state = "PRIVACY"
                self.latest = None
                return
            identity = guard.get("attempt_id")
            turn = guard.get("turn")
        start = self.clock()
        try:
            data = self.capture()
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("Invalid live PNG frame")
            end = self.clock()
            with self.lock:
                now_guard = self.guard(self.run_id)
                if (
                    not self.running
                    or not now_guard.get("allowed")
                    or now_guard.get("attempt_id") != identity
                    or now_guard.get("turn") != turn
                ):
                    self.latest = None
                    self.state = "PRIVACY"
                    return
                self.seq += 1
                self.times.append(end)
                self.latencies.append(max(0, end - start))
                self.state = "LIVE"
                self.error = ""
                self.latest = {
                    "bytes": data,
                    "sequence": self.seq,
                    "captured_epoch": start,
                    "captured_utc": datetime.fromtimestamp(start, timezone.utc).isoformat(),
                    "available_epoch": end,
                    "attempt_id": identity,
                    "turn": turn,
                    "stream_id": self.stream_id,
                }
        except Exception as e:
            with self.lock:
                self.latest = None
                self.state = "DISCONNECTED"
                self.error = public_text(str(e))

    def status(self):
        with self.lock:
            state = self.state
            guard = self.guard(self.run_id) if self.run_id and self.running else {}
            if self.running:
                if guard.get("ended"):
                    state = "ENDED"
                elif not guard.get("allowed"):
                    state = "PRIVACY"
                elif self.latest and self.clock() - self.latest["captured_epoch"] > 2:
                    state = "DELAYED"
                elif self.latest and (
                    guard.get("attempt_id") != self.latest["attempt_id"]
                    or guard.get("turn") != self.latest["turn"]
                ):
                    state = "PRIVACY"
                elif self.clock() - guard.get("observed_epoch", 0) > 3:
                    state = "PRIVACY"
            fps = (
                (len(self.times) - 1) / (self.times[-1] - self.times[0])
                if len(self.times) > 1 and self.times[-1] > self.times[0]
                else 0
            )
            return {
                "state": state,
                "run_id": self.run_id,
                "sequence": self.seq,
                "fps": round(fps, 2),
                "target_fps": round(1 / self.period),
                "captured_utc": self.latest["captured_utc"] if self.latest else None,
                "frame_age_seconds": (
                    round(self.clock() - self.latest["captured_epoch"], 3) if self.latest else None
                ),
                "error": self.error,
                "stream_id": getattr(self, "stream_id", None),
            }

    def frame(self):
        with self.lock:
            return dict(self.latest) if self.status()["state"] == "LIVE" and self.latest else None

    def stop(self):
        with self.lock:
            self.running = False
            self.state = "OFF"
            self.signal.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2.5)
        self._finish()
        return self.status()

    def _finish(self, expected_stream=None):
        with self.lock:
            if (
                self.finished
                or not self.run_id
                or (expected_stream and expected_stream != self.stream_id)
            ):
                return
            self.finished = True
            if self.on_end:
                self.on_end(self.run_id, self.statistics())

    def statistics(self):
        with self.lock:
            lat = sorted(self.latencies)
            return {
                "stream_id": getattr(self, "stream_id", None),
                "run_id": self.run_id,
                "frames_captured": self.seq,
                "target_fps": round(1 / self.period),
                "capture_latency_mean_seconds": round(sum(lat) / len(lat), 4) if lat else None,
                "capture_latency_p95_seconds": (
                    round(lat[min(len(lat) - 1, int(len(lat) * 0.95))], 4) if lat else None
                ),
                "finished_state": self.state,
                "wall_seconds": round(self.clock() - getattr(self, "began", self.clock()), 3),
                "frames_saved_to_disk": 0,
                "test_retries_triggered": 0,
            }


def read_log(directory, source, cursor):
    if source not in ("python", "appium") or type(cursor) is not int or cursor < 0:
        raise ValueError("Choose a valid log source and byte cursor")
    directory = Path(directory)
    base = 0
    if source == "python":
        path = directory / "execution.log"
    else:
        meta = readjson(directory / "execution_metadata.json", {})
        name = meta.get("appium_log_source")
        if not name:
            return {"source": source, "lines": [], "cursor": cursor, "waiting": True}
        path = Path(name)
        base = meta.get("appium_log_offset") or 0
    if not path.exists():
        return {"source": source, "lines": [], "cursor": cursor, "waiting": True}
    size = path.stat().st_size
    reset = base + cursor > size
    if reset:
        base = cursor = 0
    with path.open("rb") as f:
        f.seek(base + cursor)
        data = f.read(65536)
    end = data.rfind(b"\n") + 1
    if not end:
        return {"source": source, "lines": [], "cursor": cursor, "waiting": True}
    lines = data[:end].decode("utf-8", errors="replace").splitlines()
    result = []
    for line in lines:
        if source == "appium":
            m = re.match(
                r"(.*?\[HTTP\]\s+)(-->|<--) (GET|POST|DELETE|PUT|PATCH) (/[^\s?]+)(.*)", line
            )
            if not m:
                continue
            suffix = (
                re.match(r"\s+\d{3}(?:\s+[\d.]+\s+ms)?(?:\s+-\s+\d+)?", m[5])
                if m[2] == "<--"
                else None
            )
            line = "".join([m[1], m[2], " ", m[3], " ", m[4], suffix[0] if suffix else ""])
        result.append(public_text(line))
    return {
        "source": source,
        "lines": result,
        "cursor": cursor + end,
        "reset": reset,
        "waiting": False,
    }
