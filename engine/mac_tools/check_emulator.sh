#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then echo 'Run on Mac only.' >&2; exit 2; fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
command -v adb >/dev/null || { echo 'adb missing'; exit 2; }
serial="${1:-}"
if [ -z "$serial" ]; then
  serial="$(adb devices | awk '$2=="device"{print $1}' | head -1)"
fi
[ -n "$serial" ] || { echo 'No authorized Android device. Start emulator and run adb devices.' >&2; exit 3; }
if ! adb -s "$serial" get-state | grep -q 'device'; then echo "Not an active device: $serial" >&2; exit 3; fi
printf 'Serial: %s\n' "$serial"
printf 'Android release: '; adb -s "$serial" shell getprop ro.build.version.release | tr -d '\r'
printf 'ABI: '; adb -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r'
printf 'Emulator boot completed: '; adb -s "$serial" shell getprop sys.boot_completed | tr -d '\r'
printf 'Installed packages matching names (not authoritative app-package identification):\n'
adb -s "$serial" shell pm list packages | grep -Ei 'openai|chatgpt|gemini|googlequicksearchbox' || true
printf 'Current foreground app (check AFTER opening each target application):\n'
adb -s "$serial" shell dumpsys activity activities | grep -E -m 3 '(mResumedActivity|topResumedActivity|ResumedActivity)' || true
printf '\nVerify Google Play, ChatGPT and Gemini actually launch and can accept prompts before configuring selectors.\n'
