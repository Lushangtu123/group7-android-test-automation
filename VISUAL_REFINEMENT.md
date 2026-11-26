# Light presentation skin

The live workbench now uses the earlier Automation Studio palette: warm paper, forest-green controls, restrained borders, and serif display text. The log pane retains a dark terminal surface. Continuous device capture, Appium execution, validation, current-turn matching, logging and export behavior are unchanged.

Only `static/index.html` (header branding) and `static/style.css` changed. Backend Python and browser JavaScript hashes were checked against the previous delivery. Existing runtime evidence bytes were checked after browser inspection. No additional Android tests were executed for this visual-only revision.

Historical live acceptance results retain their actual original source snapshots and original dark interface screenshots. They are not presented as execution of this newer skin. New screenshots in `verification/refined_*.png` document the light interface in idle or explicitly selected completed-result states.

The earlier `Group7_Live_Demo.zip` is preserved. `Group7_Live_Demo_Presentation.zip` is a separate updated distribution. Its source mapping and checksum manifest describe its own bytes. The previous visual sources are also retained in the `visual_before_*` verification folder.

Open or refresh http://127.0.0.1:8770/ to see the revised skin. Click Start real demo when you want to execute the actual Android tests.

## Frontend usability revision

A later revision changed only `static/index.html`, `static/style.css`, `static/app.js`, `static/view_logic.mjs` and `tests/view_logic.test.mjs`. Backend Python, the Android engine, the 19-case catalog, oracles and all recorded evidence are unchanged.

- A selected saved run shows its last verified evidence frame, labelled as not live, instead of the idle "ready" screen.
- The workbench fills the screen height so the device view is larger; the results table scrolls into view when a watched run finishes.
- Captured answers use neutral text; the verdict pill and a coloured side bar carry PASS, REVIEW or ERROR.
- Appium log lines show shortened session ids and no repeated date; HTTP status codes are coloured. Log text stays at 20px or larger.
- Multi-turn cases show the conversation and turn position. Readiness results are listed per check. Saved-run labels name the case and applications.
- Stopping a run asks for confirmation. Result counts are coloured only when non-zero.
- Text contrast is at least 4.5:1, log tabs support arrow keys, all inserted values are escaped, and finished runs refresh every 5 seconds instead of several times a second.

Checks: 45 console tests and 5 JavaScript checks pass. One real two-attempt run of GEN-009 (ChatGPT + Gemini, 1 repeat each) completed 2/2 PASS on the existing emulator and accounts. That run was a frontend check only; its evidence is kept outside this repository and is not added to the live-demo ledger or any published count.

Earlier distributions (`Group7_Live_Demo.zip`, `Group7_Live_Demo_Presentation.zip`) and their checksum files are unchanged and still describe their own bytes.

## Laptop screens and evidence library

- Workbench: on screens up to 860px tall (for example 1366×768 and 1280×720) the header, controls and panels are tighter so the whole workbench fits in one screen; the controls stay on one row down to 1280px wide. Prompt and answer text stay at 24px or larger and logs at 20px. 1920×1080 is unchanged.
- Evidence library (`static/library/style.css` only): the accent orange is darker (#bf4320) so white button text and orange labels reach 4.5:1 contrast, the REVIEW label colour is darker, and no text is smaller than 12px. Checked on all five library views at 1920×1080 and 375px wide with no horizontal overflow.

No Android tests were run for this change.

## Demo flow

Browser files only (`static/index.html`, `static/style.css`, `static/app.js`, `static/view_logic.mjs`, `tests/view_logic.test.mjs`).

- Between turns, while Appium works on screens that are not published, the device panel keeps the last verified frame of the same attempt, dimmed, with a banner, instead of switching to a full "Preparing" screen. A frame from a different attempt or app is never held; a disconnected device still shows the full notice.
- Before any run is selected, the right column previews the chosen scenario: every prompt in order, the pass rule, and the target apps. Choosing "Choose a completed run" returns to this preview.
- Multi-turn attempts list their earlier finished turns (prompt and captured answer, one line each) above the current prompt. On short screens the list shows about two rows and keeps the newest in view, so the current answer stays visible.

Checks: 45 console and 7 JavaScript tests pass. One real GEN-013 run (ChatGPT, 1 repeat) completed 5/5 turns, PASS, 118.3 s; after the first live frame the panel never fell back to the full notice, and the earlier-turn list grew from 0 to 4. That run was a frontend check only and is not added to any published count.

## Presenting a run

Browser files only.

- The results table lists every planned execution from the start in the worker's order (application, then repeat). Rows read WAITING, RUNNING (with the current turn), the recorded outcome, or, once a run has ended, INTERRUPTED for the execution that was stopped and NOT RUN for any that never started.
- Focus mode (header button, Esc to exit) hides the controls, logs and results table and gives the device view and current turn the whole screen in two equal columns, with a short progress line. At 1920×1080 the device view grows from 323px to 377px wide.
- When the current prompt or answer is cut off by its box, a "Full answer" button opens the whole turn.

Checks: 45 console and 8 JavaScript tests pass. One real GEN-009 run (ChatGPT + Gemini, 1 repeat) completed 2/2 PASS; the table moved through WAITING, RUNNING and PASS for each row. Frontend check only; not added to any published count.

## One place to run, clear connection state, local times

Browser files only (workbench and evidence library).

- The evidence library no longer starts or stops real runs. Its "Run automation" view keeps saved runs and recorded evidence and links to the live workbench, which is now the only place that starts or stops Appium runs. Both pages link to each other from the header.
- When the local server stops answering, or was restarted so the page's session token is stale, the workbench shows a banner with a Reload button instead of failing silently. The restarted-server notice stays until the page is reloaded.
- All times are shown in the viewer's local time, 24-hour: Python events, Appium HTTP lines (Appium writes UTC; converted), frame and saved-frame times, saved-run labels and the library's event list. The log bar names the time zone.

Checks: 45 console and 9 JavaScript tests pass (the time test also passes with TZ=UTC). Browser: Appium and Python events for the same moment now read the same local time; the banner appeared when the server was stopped, changed to the restart notice after it came back, stayed steady, and cleared on reload; the library's five views load with no failed requests or overflow. No Android tests were run for this change.
