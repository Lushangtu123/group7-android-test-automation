#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then echo 'Run on Mac only.' >&2; exit 2; fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
name="${1:-app}"
serial="${2:-}"
if [ -z "$serial" ]; then serial="$(adb devices | awk '$2=="device"{print $1}' | head -1)"; fi
[ -n "$serial" ] || { echo 'No emulator selected. Supply serial: bash mac_tools/capture_ui.sh chatgpt emulator-5554' >&2; exit 3; }
case "$name" in chatgpt|gemini) ;; *) echo 'Name must be chatgpt or gemini' >&2; exit 2 ;; esac
stamp="$(date +%Y%m%d_%H%M%S)"
out="$ROOT/reports/inspector_$name";mkdir -p "$out"
echo 'Privacy: open a non-sensitive test chat; XML/screenshot can contain personal data.'
adb -s "$serial" shell uiautomator dump /sdcard/window-group7.xml >/dev/null
adb -s "$serial" pull /sdcard/window-group7.xml "$out/$stamp.xml" >/dev/null
adb -s "$serial" shell rm /sdcard/window-group7.xml >/dev/null || true
adb -s "$serial" exec-out screencap -p > "$out/$stamp.png"
echo "Wrote $out/$stamp.xml and $out/$stamp.png"
echo 'Use Appium Inspector to identify verified selectors and package IDs. Do NOT publish these files without review.'
