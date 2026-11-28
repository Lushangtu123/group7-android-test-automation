import json, sys, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
import console_core
from console_core import RunManager


class DefinitionTests(unittest.TestCase):
    def test_definitions_built_once_and_sys_path_stable(self):
        m = RunManager(
            Path(tempfile.mkdtemp()), launcher=lambda *a: None, preflight=lambda: {"ready": True}
        )
        first = m.definitions()
        before = len(sys.path)
        for _ in range(5):
            self.assertEqual(m.definitions(), first)
        self.assertEqual(len(sys.path), before)
        first[0]["conversations"].clear()  # a caller changing its copy does not change the next one
        self.assertTrue(m.definitions()[0]["conversations"])


class StartLockTests(unittest.TestCase):
    def test_other_requests_proceed_while_readiness_runs(self):
        release = threading.Event()
        entered = threading.Event()

        def slow_preflight():
            entered.set()
            release.wait(5)
            return {"ready": True}

        with tempfile.TemporaryDirectory() as t:
            m = RunManager(Path(t), launcher=lambda *a: None, preflight=slow_preflight)
            starter = threading.Thread(target=m.start, args=({"profile": "quick"},))
            starter.start()
            self.assertTrue(entered.wait(5))
            done = []
            reader = threading.Thread(target=lambda: done.append(m.jobs()))
            reader.start()
            reader.join(1)
            release.set()
            starter.join(5)
            self.assertEqual(done, [[]], "jobs() waited for the readiness check")

    def test_concurrent_starts_create_one_run(self):
        gate = threading.Barrier(2)

        def preflight():
            gate.wait(5)
            return {"ready": True}

        with tempfile.TemporaryDirectory() as t:
            m = RunManager(Path(t), launcher=lambda *a: None, preflight=preflight)
            results = []

            def go():
                try:
                    results.append(m.start({"profile": "quick"})["id"])
                except RuntimeError as e:
                    results.append("busy")

            threads = [threading.Thread(target=go) for _ in range(2)]
            for x in threads:
                x.start()
            for x in threads:
                x.join(5)
            self.assertEqual(sorted(r == "busy" for r in results), [False, True])
            self.assertEqual(len(m.jobs()), 1)


class SnapshotCacheTests(unittest.TestCase):
    def test_unchanged_files_are_not_reparsed_and_changes_are_seen(self):
        with tempfile.TemporaryDirectory() as t:
            m = RunManager(Path(t), launcher=lambda *a: None, preflight=lambda: {"ready": True})
            job = m.start({"profile": "quick"})
            d = m.directory(job["id"])
            (d / "execution.log").write_text(json.dumps({"event": "STAGE_START"}) + "\n")
            calls = []
            real = console_core.events

            def counting(path):
                calls.append(path.name)
                return real(path)

            with patch.object(console_core, "events", counting):
                m.snapshot(job["id"])
                first = calls.count("execution.log")
                m.snapshot(job["id"])
                self.assertEqual(calls.count("execution.log"), first)
                time.sleep(0.01)
                with (d / "execution.log").open("a") as f:
                    f.write(json.dumps({"event": "STAGE_END"}) + "\n")
                snap = m.snapshot(job["id"])
            self.assertEqual([e["event"] for e in snap["events"]], ["STAGE_START", "STAGE_END"])
