#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then echo 'Run on Mac only.' >&2; exit 2; fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
repeats="${1:-3}"
case "$repeats" in ''|*[!0-9]*) echo 'repeats must be a positive integer' >&2; exit 2 ;; esac
[ "$repeats" -ge 1 ] || { echo 'repeats must be >=1' >&2;exit 2; }
config="$ROOT/data/android_appium_config.local.json"
[ -f "$config" ] || { echo 'Missing local config' >&2; exit 3; }
"$ROOT/.venv/bin/python" "$ROOT/mac_tools/config_validator.py" "$config" --app both
curl -fsS http://127.0.0.1:4723/status >/dev/null || { echo 'Start Appium in a second terminal.' >&2;exit 4; }
cd "$ROOT"
output="reports/mac_live_both_r${repeats}_$(date +%Y%m%d_%H%M%S)"
echo "Starting: 19 scenarios x 2 apps x $repeats repeats = $((19*2*repeats)) planned app-case runs."
"$ROOT/.venv/bin/python" -m group7_auto.live_runner --config "$config" --app both --repeats "$repeats" --output "$output"
echo "Saved $output"
