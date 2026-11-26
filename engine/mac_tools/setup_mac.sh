#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then
  echo 'ERROR: Run this on your MacBook, not ChatGPT/Linux.' >&2; exit 2
fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
if ! command -v adb >/dev/null || ! command -v emulator >/dev/null; then
  echo 'Install Android Studio, Android SDK Platform-Tools and Android Emulator first:'
  echo 'https://developer.android.com/studio'
  echo 'Then run: bash mac_tools/preflight_mac.sh'; exit 3
fi
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo 'Node.js is missing. If you use Homebrew: brew install node'; exit 3
fi
if ! command -v python3 >/dev/null; then echo 'Python 3 missing (3.10+ required)'; exit 3; fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
if ! command -v appium >/dev/null; then
  echo 'Installing Appium with npm into your configured npm global prefix...'
  npm install -g appium
fi
if ! appium driver list --installed 2>/dev/null | grep -qi 'uiautomator2'; then
  echo 'Installing UiAutomator2 driver...'
  appium driver install uiautomator2
fi
cd "$ROOT"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -r "$ROOT/requirements-optional-appium.txt"
"$ROOT/.venv/bin/python" -m unittest discover -s "$ROOT/tests" -v
"$ROOT/.venv/bin/python" -m unittest mac_tools.tests_mac_helpers -v
printf '\nChecking Appium driver prerequisites:\n'
appium driver doctor uiautomator2 || {
  echo 'Fix required Doctor checks before running real Android UI tests.' >&2; exit 4;
}
printf '\nLocal setup complete. Next: create/boot a Google Play Pixel AVD and sign into the apps manually.\n'
