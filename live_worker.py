"""One isolated Appium subprocess. Every new outcome stays outside formal114."""

import argparse, hashlib, json, os, shutil, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from console_core import sdk_paths, atomic, utc, readjson, command, appium_server_url
from live_services import screen_visibility, appium_log_source

p = argparse.ArgumentParser()
p.add_argument("--directory", type=Path, required=True)
a = p.parse_args()
out = a.directory.resolve()
job = readjson(out / "job.json")
plan = job["plan"]
snap = out / "source_snapshot"
shutil.copytree(ROOT / "engine", snap, ignore=shutil.ignore_patterns("__pycache__", "reports"))
sdk, adb = sdk_paths()
config_path = snap / "data/android_appium_config.local.json"
config = json.loads(config_path.read_text())
config["adb_path"] = str(adb)
config_path.write_text(json.dumps(config, indent=2))
device = config["apps"]["chatgpt"]["capabilities"]["appium:udid"]
shutil.copy2(__file__, out / "worker_snapshot.py")
atomic(
    out / "source_sha256.json",
    {
        str(f.relative_to(snap)): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in snap.rglob("*")
        if f.is_file()
    },
)
sys.path.insert(0, str(snap))
from group7_auto.appium_adapter import LiveAdapter
from group7_auto.live_runner import run_live
from group7_auto.android_network import check_android_network

log = (out / "execution.log").open("x", buffering=1)
begin = time.monotonic()
server = appium_log_source(ROOT)
offset = server.stat().st_size if server.is_file() else None
metadata = {
    "kind": "REAL_ANDROID_APPIUM_DEMO_CONSOLE",
    "scope": "NEW_DEMO_RUN_NOT_FORMAL114",
    "plan": plan,
    "started_utc": utc(),
    "process_id": os.getpid(),
    "recording_enabled": False,
    "automatic_case_retries": 0,
    "automatic_prompt_resends": 0,
    "appium_log_source": str(server) if offset is not None else None,
    "appium_log_offset": offset,
}
atomic(out / "execution_metadata.json", metadata)


def event(kind, **data):
    row = {"utc": utc(), "event": kind, **data}
    line = json.dumps(row, ensure_ascii=False)
    log.write(line + "\n")
    print(line, flush=True)


def stopcheck():
    if (out / "stop_requested").exists():
        raise KeyboardInterrupt("Presenter requested stop")


class StoppableDriver:
    def __init__(self, driver, observe=None):
        self._driver = driver
        self._observe = observe

    def __getattr__(self, name):
        if name != "quit":
            stopcheck()
        value = getattr(self._driver, name)
        if name == "page_source" and self._observe:
            self._observe(value)
        if callable(value):

            def call(*args, **kwargs):
                if name != "quit":
                    stopcheck()
                return value(*args, **kwargs)

            return call
        return value


class Observed(LiveAdapter):
    def __init__(self, path, app):
        stopcheck()
        self.context = {}
        self.current_prompt = None
        self.current_turn = None
        event("SESSION_START", app=app)
        super().__init__(path, app)
        self.driver = StoppableDriver(self.driver, self.observe_source)
        event("SESSION_READY", app=app, observation=getattr(self, "startup_observation", {}))

    def observe_source(self, xml):
        atomic(
            out / "screen_visibility.json",
            screen_visibility(
                xml, self.current_prompt, {**self.context, "turn": self.current_turn}
            ),
        )

    def hide_screen(self):
        atomic(
            out / "screen_visibility.json",
            {
                "allowed": False,
                "observed_epoch": time.time(),
                "attempt_id": self.context.get("attempt_id"),
                "turn": self.current_turn,
            },
        )

    def prepare_conversation(self, folder, conversation):
        stopcheck()
        self.current_prompt = None
        self.current_turn = None
        self.hide_screen()
        super().prepare_conversation(folder, conversation)
        folder = Path(folder)
        self.context = {
            "app": self.app,
            "case": folder.parents[1].name,
            "repeat": int(folder.parent.name.split("_")[-1]),
            "attempt_id": folder.name,
            "conversation": conversation,
            "evidence_directory": str(folder.relative_to(out)),
        }
        event("CONVERSATION_PREPARE", **self.context)

    def new_chat(self):
        event("NEW_CHAT", **self.context)
        try:
            r = super().new_chat()
            event("NEW_CHAT_READY", **self.context)
            return r
        except Exception as e:
            event("NAVIGATION_ERROR", **self.context, error=str(e))
            raise

    def send(self, prompt, case, turn, folder):
        stopcheck()
        self.current_prompt = prompt
        self.current_turn = turn
        self.hide_screen()
        event("TURN_START", **self.context, turn=turn, prompt=prompt)
        try:
            answer = super().send(prompt, case, turn, folder)
            event(
                "TURN_DONE",
                **self.context,
                turn=turn,
                prompt=prompt,
                response=answer,
                characters=len(answer),
            )
            return answer
        except Exception as e:
            network = check_android_network(str(adb), device)
            atomic(Path(folder) / f"{self.app}_{case}_{turn}.error_network.json", network)
            event(
                "TURN_ERROR",
                **self.context,
                turn=turn,
                prompt=prompt,
                error=str(e),
                hostname_http_204=network["hostname_http_204"],
            )
            raise

    def close(self):
        # Clean up only this worker's session even when a stop marker is set.
        raw = self.driver._driver if isinstance(self.driver, StoppableDriver) else self.driver
        raw.quit()


def environment(label):
    d = {
        "captured_utc": utc(),
        "python": sys.version,
        "appium_server": appium_server_url(config),
        "device": device,
        "android_release": command(
            [adb, "-s", device, "shell", "getprop", "ro.build.version.release"]
        )[1],
        "android_api": command([adb, "-s", device, "shell", "getprop", "ro.build.version.sdk"])[1],
        "packages": {},
    }
    for pkg in (
        "com.openai.chatgpt",
        "com.google.android.apps.bard",
        "com.google.android.googlequicksearchbox",
        "io.appium.settings",
    ):
        code, text, error = command([adb, "-s", device, "shell", "dumpsys", "package", pkg])
        d["packages"][pkg] = {
            "exit_code": code,
            "version_lines": [
                s.strip() for s in text.splitlines() if "versionCode=" in s or "versionName=" in s
            ],
            "error": error,
        }
    try:
        import importlib.metadata as md

        d["python_dependencies"] = {n: md.version(n) for n in ("Appium-Python-Client", "selenium")}
    except Exception:
        pass
    atomic(out / f"runtime_environment_{label}.json", d)


exit_code = 0
interrupted = False
try:
    event("STAGE_START", run_id=job["id"], plan=plan)
    environment("begin")
    stopcheck()
    network = check_android_network(str(adb), device)
    atomic(out / "network_preflight.json", network)
    event("NETWORK_PREFLIGHT", hostname_http_204=network["hostname_http_204"])
    if not network["hostname_http_204"]:
        raise RuntimeError("Device network preflight failed; no prompts were sent")
    summary = run_live(
        config_path,
        which=plan["app"],
        case_ids=",".join(plan["cases"]),
        repeats=plan["repeats"],
        output=out,
        adapter_factory=Observed,
        catalog_path=snap / "data/model_based_extension.csv",
    )
    event("RESULT", summary=summary)
except KeyboardInterrupt:
    interrupted = True
    exit_code = 130
    event(
        "INTERRUPTED",
        reason="Presenter stopped this run. Completed outcome rows are retained; no result invented for partial attempts.",
    )
    atomic(
        out / "interruption_record.json",
        {
            "utc": utc(),
            "scope": "PARTIAL_NEW_DEMO_RUN",
            "original_formal_results_modified": False,
            "no_synthetic_outcome_rows": True,
        },
    )
except Exception as e:
    exit_code = 1
    event("PROCESS_ERROR", error=f"{type(e).__name__}: {e}")
finally:
    # No extra Android actions after interruption; completed raw artifacts remain.
    if not interrupted:
        try:
            environment("end")
        except Exception as e:
            event("ENVIRONMENT_ERROR", error=str(e))
    metadata.update(
        ended_utc=utc(),
        wall_seconds=round(time.monotonic() - begin, 3),
        interrupted=interrupted,
        exit_code=exit_code,
    )
    atomic(out / "execution_metadata.json", metadata)
    if offset is not None:
        with server.open("rb") as src, (out / "appium_server.log").open("xb") as dst:
            src.seek(offset)
            shutil.copyfileobj(src, dst)
    event("STAGE_END", wall_seconds=metadata["wall_seconds"])
    log.close()
sys.exit(exit_code)
