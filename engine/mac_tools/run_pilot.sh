#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then echo 'Run on Mac only.' >&2; exit 2; fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
app="${1:-chatgpt}"
case_id="${2:-TC-FA-01}"
case "$app" in chatgpt|gemini) ;; *) echo 'Use chatgpt or gemini' >&2; exit 2;; esac
config="$ROOT/data/android_appium_config.local.json"
[ -f "$config" ] || { echo "Missing $config: create it and inspect real UI selectors first." >&2; exit 3; }
"$ROOT/.venv/bin/python" "$ROOT/mac_tools/config_validator.py" "$config" --app "$app"
if ! curl -fsS http://127.0.0.1:4723/status >/dev/null; then
  echo 'Appium is not running. Open another Terminal, source env_mac.sh and run: appium' >&2; exit 4
fi
cd "$ROOT"
output="reports/pilot_${app}_$(date +%Y%m%d_%H%M%S)"
"$ROOT/.venv/bin/python" -m group7_auto.live_runner --config "$config" --app "$app" --cases "$case_id" --output "$output"
echo "Inspect CSV, screenshots and XML inside $output. ERROR is not a model failure."
