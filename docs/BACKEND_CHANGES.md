# Backend changes

Changes to the local console server (`server.py`, `console_core.py`, `live_worker.py`). The Android engine, the 19-case catalog, oracles and all recorded evidence are unchanged. Each run still snapshots the console and engine sources it actually used, so earlier runs keep their original code hashes.

## Host check, saved-frame order, configured Appium address

- **Loopback Host only.** Every GET and POST is refused with 421 unless the `Host` header is `127.0.0.1:<port>` or `localhost:<port>`. A page on another hostname that resolves to 127.0.0.1 (DNS rebinding) can no longer read `/api/bootstrap`, the session token, live device frames or logs. The existing Origin and token checks for POST remain.
- **Saved frame by turn order.** The frame shown for a finished run is chosen by conversation, turn and stage (final capture after the answer, then native views, then after-send, then before-send), not by file modification time, which changes when a run folder is copied or unpacked. Its time comes from the turn checkpoint (`capture_time_source: turn_checkpoint`) when available. The run folder is resolved first, so a runtime path behind a symlink (for example macOS `/var` → `/private/var`) no longer raises an error.
- **Configured Appium address.** The readiness check and each run's environment record use `server_url` from `engine/data/android_appium_config.local.json` (default `http://127.0.0.1:4723`), the same address the engine connects to.

Checks: 50 console tests (5 new; the Host and saved-frame tests fail on the previous code), 197 engine tests and 9 view-logic tests pass. A real GEN-009 run (ChatGPT, 1 repeat) completed PASS through the updated server; its environment record names the configured server and its saved frame is the final capture with the checkpoint time. Frontend check runs are not added to any published count.
