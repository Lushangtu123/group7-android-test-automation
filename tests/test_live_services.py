import importlib.util, json, tempfile, time, threading, unittest
from pathlib import Path


class ServiceTests(unittest.TestCase):
    def services(self):
        self.assertIsNotNone(
            importlib.util.find_spec("live_services"),
            "Continuous live device service is not implemented",
        )
        import live_services

        return live_services

    def mirror(self, clock=None, guard=None, capture=None):
        return self.services().DeviceMirror(
            capture=capture or (lambda: b"\x89PNG\r\n\x1a\nframe"),
            guard=guard or (lambda _: {"allowed": True, "observed_epoch": 10}),
            clock=clock or (lambda: 10),
        )

    def test_old_frame_is_hidden_as_delayed(self):
        now = [10]
        m = self.mirror(clock=lambda: now[0])
        m.start("run", background=False)
        m.capture_once()
        self.assertEqual(m.status()["state"], "LIVE")
        now[0] = 13
        self.assertEqual(m.status()["state"], "DELAYED")
        self.assertIsNone(m.frame())

    def test_privacy_guard_is_checked_again_before_serving(self):
        safe = [True]
        m = self.mirror(guard=lambda _: {"allowed": safe[0], "observed_epoch": 10})
        m.start("run", background=False)
        m.capture_once()
        self.assertIsNotNone(m.frame())
        safe[0] = False
        self.assertEqual(m.status()["state"], "PRIVACY")
        self.assertIsNone(m.frame())

    def test_frame_from_previous_attempt_cannot_appear_in_new_attempt(self):
        identity = ["A"]
        m = self.mirror(
            guard=lambda _: {"allowed": True, "observed_epoch": 10, "attempt_id": identity[0]}
        )
        m.start("run", background=False)
        m.capture_once()
        identity[0] = "B"
        self.assertIsNone(m.frame())
        m.capture_once()
        self.assertEqual(m.frame()["attempt_id"], "B")

    def test_stop_and_completed_job_disable_live_frame(self):
        guard = {"allowed": True, "observed_epoch": 10}
        m = self.mirror(guard=lambda _: guard)
        m.start("run", background=False)
        m.capture_once()
        guard["ended"] = True
        m.capture_once()
        self.assertEqual(m.status()["state"], "ENDED")
        self.assertIsNone(m.frame())

    def test_capture_failure_never_reuses_previous_frame_as_live(self):
        m = self.mirror()
        m.start("run", background=False)
        m.capture_once()

        def failure():
            raise TimeoutError("device unavailable")

        m.capture = failure
        m.capture_once()
        self.assertEqual(m.status()["state"], "DISCONNECTED")
        self.assertIsNone(m.frame())

    def test_repeated_start_reuses_one_capture_thread(self):
        called = []
        m = self.mirror(
            clock=time.time,
            guard=lambda _: {"allowed": True, "observed_epoch": time.time()},
            capture=lambda: called.append(1) or b"\x89PNG\r\n\x1a\nframe",
        )
        m.start("run")
        first = m.thread
        m.start("run")
        self.assertIs(first, m.thread)
        time.sleep(0.25)
        m.stop()
        self.assertLessEqual(len(called), 3)
        self.assertEqual(m.status()["state"], "OFF")

    def test_old_loop_cannot_follow_the_next_stream_after_terminal_transition(self):
        s = self.services()
        captured = []
        m = None

        def capture():
            captured.append(1)
            return b"\x89PNG\r\n\x1a\nframe"

        def guard(id):
            return {
                "allowed": True,
                "observed_epoch": time.time(),
                "ended": id == "first" and bool(captured),
            }

        def ended(id, stats):
            if id == "first":
                m.start("next")

        m = s.DeviceMirror(capture=capture, guard=guard, on_end=ended)
        m.start("first")
        old = m.thread
        try:
            deadline = time.monotonic() + 1
            while m.run_id != "next" and time.monotonic() < deadline:
                time.sleep(0.01)
            old.join(timeout=0.1)
            self.assertFalse(old.is_alive(), "The prior capture loop joined the new stream")
        finally:
            m.stop()

    def test_log_cursor_preserves_partial_lines_and_raw_source(self):
        s = self.services()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            p = d / "execution.log"
            p.write_text("first actual line\nsecond partial")
            a = s.read_log(d, "python", 0)
            self.assertEqual(a["lines"], ["first actual line"])
            p.write_text(p.read_text() + " complete\n")
            b = s.read_log(d, "python", a["cursor"])
            self.assertEqual(b["lines"], ["second partial complete"])
            self.assertEqual(s.read_log(d, "python", b["cursor"])["lines"], [])

    def test_appium_log_is_available_before_final_archive_and_has_no_payload(self):
        s = self.services()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            p = d / "actual_appium.log"
            p.write_text("old unrelated\n")
            offset = p.stat().st_size
            (d / "execution_metadata.json").write_text(
                json.dumps({"appium_log_source": str(p), "appium_log_offset": offset})
            )
            with p.open("a") as f:
                f.write(
                    '[02:00][HTTP] --> POST /session/abc/execute/sync {"script":"mobile: getClipboard","value":"private"}\n[02:01][HTTP] <-- POST /session/abc/execute/sync 200 123 ms - 16\n{"value":"c2VjcmV0"}\n'
                )
            got = s.read_log(d, "appium", 0)
            self.assertEqual(len(got["lines"]), 2)
            text = "\n".join(got["lines"])
            self.assertIn("123 ms", text)
            for secret in ["old unrelated", "private", "c2VjcmV0", "getClipboard"]:
                self.assertNotIn(secret, text)

    def test_invalid_log_source_or_cursor_is_rejected(self):
        s = self.services()
        with tempfile.TemporaryDirectory() as t:
            for source, cursor in [("shell", 0), ("python", -1), ("python", True)]:
                with self.assertRaises(ValueError):
                    s.read_log(Path(t), source, cursor)

    def test_visibility_needs_current_prompt_and_current_identity(self):
        s = self.services()
        self.assertTrue(
            hasattr(s, "screen_visibility"), "Worker XML privacy observation is missing"
        )
        xml = '<hierarchy><node text="Translate"/></hierarchy>'
        self.assertTrue(
            s.screen_visibility(xml, "Translate", {"attempt_id": "a", "turn": "t"})["allowed"]
        )
        self.assertFalse(
            s.screen_visibility(xml, "Another", {"attempt_id": "a", "turn": "t"})["allowed"]
        )
        self.assertFalse(s.screen_visibility(xml, "Translate", {})["allowed"])

    def test_visibility_hides_account_page_even_with_prompt(self):
        s = self.services()
        self.assertTrue(
            hasattr(s, "screen_visibility"), "Worker XML privacy observation is missing"
        )
        xml = '<hierarchy><node text="Translate"/><node text="private@example.com"/></hierarchy>'
        self.assertFalse(
            s.screen_visibility(xml, "Translate", {"attempt_id": "a", "turn": "t"})["allowed"]
        )

    def test_existing_active_console_log_precedes_legacy_global_log(self):
        s = self.services()
        self.assertTrue(
            hasattr(s, "appium_log_source"), "Shared existing server log discovery is missing"
        )
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            new = root / "demo/new"
            new.mkdir(parents=True)
            legacy = root / "work/logs/appium.log"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("old")
            active = root / "demo/Group7_Demo_Console/runtime/services/appium.log"
            active.parent.mkdir(parents=True)
            active.write_text("current")
            self.assertEqual(s.appium_log_source(new), active)
