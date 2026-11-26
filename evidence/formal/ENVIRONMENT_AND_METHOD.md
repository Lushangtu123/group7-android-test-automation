# Environment and execution method

The tests use an Apple M2 Max with 64 GiB host memory. The existing Pixel 7 AVD
runs Android 15 / API 35 on an ARM64 Google Play system image, with 2 GiB guest
memory and four virtual CPU cores. The device ID is emulator-5554. Each stage
includes a read-only runtime observation with the installed versions and
effective UiAutomator2 settings.

The observed software versions are Appium 4.0.0, UiAutomator2 9.2.1,
ChatGPT Android 1.2026.314 and the Gemini launcher 1.0.995038376. Gemini renders
inside the Google application, whose updated version is 17.74.18.ve.arm64.
The package dump also lists an older factory Google application version.
The UI shows Gemini Auto. ChatGPT's underlying model ID is not exposed in the
captured UI.

Both applications use independent temporary conversations. Paired fairness
prompts are sent in separate conversations. Prompts within a memory or fixed-flow
case stay in the same conversation. Current prompt ownership and completed reply
controls must be verified before response collection.

The emulator was restarted with its existing userdata after a recorded QEMU
crash, and later after a device DNS fault. The current launch disables audio,
uses a headless window, and uses explicit DNS servers. The launch command,
diagnostic evidence and before/after connectivity checks are preserved under
the relevant environment-recovery directories. The installed apps and account
data were retained.

The primary ChatGPT collection channel is its current response Copy action.
Each capture requires a unique clipboard marker to be replaced, followed by
agreement with the current visible response. The revised collector records an
initial unsuccessful action before one guarded retry on the same response's
inspected clickable parent. It never resends a submitted prompt.

Gemini uses an accessibility collection path that verifies the completed
response footer, then reconstructs all accessible current-answer text while
scrolling back to the current prompt. Adjacent viewports must overlap in their
substantive text. Per-view screenshots, XML, ordering, hashes and the full
reconstruction are saved. Image and video content remain visible evidence
without a media transcript.

The revised ChatGPT input path checks the actual clickable Send control.
If an exact unsent prompt remains in a disabled composer, the collector permits
one clear-and-retype operation and records it. A persistent disabled control
raises ERROR before submission. A completed response without a fresh, validated
capture also raises ERROR.

Each measured round saves its own source snapshot, case and oracle hashes,
attempts, response details, checkpoints, XML, screenshots, environment and logs.
The first round's original ERROR records remain in its primary counts.
Independent targeted retests are linked to those records. The later rounds use
the verified collection revision with the same test cases and scoring rules.
Cross-round stability should therefore be interpreted with the collector
revision in view.

The 19 fixed cases generate 42 prompts per app and 84 prompts per complete round.
Three rounds plan 114 app cases and 252 prompt turns. A generated outcome row,
a proven submitted case and a completely captured case are counted separately.
REVIEW outcomes do not count as automatic PASS. Machine execution time is
measured. Human effort and financial charges were not measured.

Round 3 was interrupted and resumed without replacing its prior outcome rows.
The original first-segment directory is preserved and its single completed row
is copied into the combined continuation, counted once. Orphan evidence from
uncheckpointed attempts is retained without inventing an outcome. A memory
announcement and a temporary-chat introduction blocked two resumed startup
attempts; both remain ERROR. Environment preparation and an exact inspected
Close-only introduction guard are documented separately with device retests.
The introductory guard does not change scoring or enable personalization.

Complete end-to-end wall time for Round 3 cannot be reconstructed because the
original interrupted segment has no final clock measurement. Known segment
wall intervals and actual recorded-attempt durations are reported separately.
The idle interruption gap is excluded. No elapsed time is fabricated.

The original interrupted Round 3 did not finalize a dedicated Appium log slice.
The saved global server-log prefix in runs/round3_original_server_log_recovery
retains its commands with an explicit wider scope and hash. It is not presented
as an isolated stage log. Later resume segments have their own log slices.
