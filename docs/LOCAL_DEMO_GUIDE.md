# Group 7 / Live Android Lab

This version opens directly into an English live execution workbench. The left pane continuously captures the current Android screen over ADB. The right pane shows actual Python events, actual Appium HTTP commands, the current prompt and the validated response. The result table updates as each independent test ends.

## Start the real demonstration

Double-click **Start Live Demo.command**, or run it from this folder:

```bash
bash "Start Live Demo.command"
```

Open **http://127.0.0.1:8770**. Before a run, the right pane previews the selected scenario: every prompt, its pass rule and the target apps. Click **Check readiness** (each check is listed with ✓ or ✕), then **Start real demo**. The default is GEN-009, ChatGPT + Gemini, two executions per app: four real Android tests. The page does not automatically execute tests when opened, and completed historical results are not selected as a pretend live run. Real runs start and stop only here; the evidence library is for viewing.

The configured Pixel 7 emulator and Appium must already be running. A headless emulator works with this mirror. Reuse the existing device and logged-in apps. If the existing Appium server is stopped, run `bash "Start Appium.command"` in another Terminal. Nothing is installed and no accounts are created. Keep the console Terminal open.

For a moved copy, select your existing Appium Python environment:

```bash
GROUP7_PYTHON=/actual/path/to/venv/bin/python bash "Start Live Demo.command"
```

Use the venv executable directly; do not resolve its symlink to system Python. `ANDROID_HOME` or `ANDROID_SDK_ROOT` selects the existing SDK. `GROUP7_APPIUM_LOG` can select the actual existing server log. Its default discovery prefers this console's server log, then the earlier console's log, then the legacy project log. Check readiness does not guarantee app backend health, login or selector compatibility.

## What the audience sees

- **Device live:** fresh frames from the emulator, targeted at five frames per second. Capture time, observed frame rate and capture-to-page delay are visible. Appium can enter a prompt in one operation; input is shown at its actual speed.
- **Current turn:** only the current attempt and turn can supply the displayed response. Generation remains visible in the Android pane; the separate answer pane updates after the collection checks finish. Multi-turn cases show the turn position and list earlier finished turns of the attempt. When a prompt or answer is cut off, **Full answer** opens the whole turn.
- **Python events / Appium HTTP log:** switch between two actual log sources while the test continues. HTTP command paths, status codes and observed timings come from the server log; request and response payloads are withheld. Session ids are shortened, and every time on the page is local 24-hour time (Appium's UTC timestamps are converted); the log bar names the zone.
- **Independent outcomes:** every planned execution is listed from the start as WAITING, then RUNNING with the current turn, then its app, repeat, attempt ID, turn completeness, verdict and duration. After a stop, the stopped execution reads INTERRUPTED and any not started read NOT RUN. Click an attempt to inspect its complete prompt/answer pairs. REVIEW is not PASS and ERROR is not a model FAIL.
- **3D model & generator:** an auxiliary panel runs the actual deterministic Python generator and displays its real output count and execution time. There are 16 coordinates and four executable scenarios. This panel does not claim all coordinates were executed or human approved.

Use **Full screen** for projection and **Focus** (Esc to exit) to give the device view and current turn the whole screen with a short progress line. Interface prompts and responses use large text; logs are at least 20px. **Enlarge view** opens the Android image at a larger scale. The layout fits laptop screens down to 1280×720. The recorded evidence library and original repeated-case comparison are clearly labelled auxiliary views; both pages link to each other in the header.

## Privacy, connection and lifecycle

The mirror is active only for a current real run. It reuses XML already read by the Appium adapter to verify current-prompt ownership and reject account pages. Navigation and unverified pages are never shown: while they are on screen the status reads **View guarded** and the panel keeps the last verified frame of the same attempt, dimmed, under a banner. A frame from another attempt or app is never kept. The guard is refreshed from actual UI observations; observations older than three seconds stop publication. It is a conservative UI guard, not a general image-content anonymity guarantee: prepare the dedicated test device and do not manually navigate to private content while presenting.

The service retains just the latest preview PNG in memory, shared across viewers. It does not write continuous frames to disk or make a new movie. Standard original-run screenshots/XML are still saved by the runner. **Stream delayed** appears after two seconds without a fresh frame. A mirror failure is separate from case scoring and never causes a prompt resend. If the local server stops answering or is restarted, a banner with a **Reload page** button appears at the top of the workbench. Normal device capture is capped at 5fps rather than advertised as 30/60fps video.

Stop interrupts this worker, stops its mirror, and retains complete rows and partial evidence. An unfinished case is not given a synthetic verdict. At normal completion the mirror stops; its retained image is explicitly labelled **last live frame**, with the camera indicator off. A refresh reconnects an active task without creating a second worker. Restarting the console also recovers a worker that has finished while the server was unavailable.

This is a loopback-only local presentation service, not a public website. The live frames and log APIs require the console session token. No arbitrary command or device-control API is exposed. Avoid running the older console's independent Android controls at the same time; this console permits one worker within its own runtime.

## Evidence and historical results

Each new run has its own `runtime/runs/<UTC-ID>/` folder containing attempts.csv, summary.json, response_details.jsonl, turn_checkpoints.jsonl, screenshots, XML, actual logs, observed environment, source/config snapshots and hashes. Final-version runs freeze the console Python and browser sources before launching the worker in `console_snapshot/` with `console_source_sha256.json`. Imported scoring and collection engine files remain unchanged. Mirror statistics record frame counts and latency, not preview image bytes.

**Export evidence** downloads a privacy derivative with raw/export SHA-256 mappings and withheld-image counts. Executable source is preserved without rewriting its regex syntax. Raw runtime files and browser profiles are private and are excluded from the portable delivery. Exported preview screenshots still require the existing prompt/account checks; raw files remain local. The provenance manifest identifies sanitized bytes.

The formal study remains **114 outcomes: 37 PASS / 0 FAIL / 58 REVIEW / 19 ERROR**, with **111 primary submitted cases + 3 linked coverage retests**. Its 58 human review rows remain unsigned. The independent historical model batch remains **12 PASS / 0 FAIL / 1 REVIEW / 3 ERROR**, covering four of 16 coordinates. New live-demo tests are separate and do not replace errors, sign reviews or establish full rubric marks.

The preserved reference library has all 114 status rows and captured response details plus 10 curated visual samples. Full visual evidence remains in the existing Core, Representative, Optimization and complete evidence packages. Existing MP4s are neither re-encoded nor included in this new ZIP; the library links the original optimized video when this folder remains in the workspace.

## Validation and reproduction

Read `verification/DELIVERY_REPORT.json` for final observed outcomes, live-frame performance, local checks and archive preservation. Initial and final acceptance runs are distinct; neither is merged into the formal study. The initial acceptance predates the final console-source snapshot and stream lifecycle refinements, and remains labelled accordingly.

Local checks use no app prompts:

```bash
python3 -m unittest discover -s tests -v
node --test tests/view_logic.test.mjs
PYTHONPATH=engine python3 -m unittest discover -s engine/tests
```

Node is needed only for the JavaScript regression checks. The running console itself needs Python, the existing Appium Python client and the existing Android environment. Browser acceptance helpers use the existing websocket-client dependency and an isolated Chrome debugging session; they are not required to present the project. Console, JavaScript and engine unit tests are not Android application tests.

The portable `Group7_Live_Demo.zip` contains code, the unchanged engine, the reference library, documentation, selected verification screenshots and sanitized exports of both acceptance runs. It excludes raw runtime, browser profiles, continuous frames, installed dependencies and videos. After extracting it, run `shasum -a 256 -c SHA256SUMS.txt` inside its folder. `PACKAGE_SOURCE_MAPPING.json` identifies local-to-package privacy derivatives. Archive source hashes still refer to original bytes.

The original console remains at port 8769 and is preserved along with its ZIP. This new version uses port 8770. Closing the web server does not cancel an independent Appium worker: finish or stop the task first. Appium and the emulator have their own lifecycles and retain their apps and login state.

Implementation references: [Android ADB screen capture](https://developer.android.com/tools/adb#screencap), [Android screencap source](https://android.googlesource.com/platform/frameworks/base/+/master/cmds/screencap/screencap.cpp), and [Python threading](https://docs.python.org/3.13/library/threading.html).
