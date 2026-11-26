#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then
  echo 'ERROR: This check must run on the M2 Max Mac (not inside ChatGPT/Linux).'
  exit 2
fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
printf '\n=== GROUP 7 macOS PREFLIGHT ===\n'
printf 'System: '; sw_vers -productVersion
printf 'CPU: '; uname -m
printf 'Physical memory (GB): '; sysctl -n hw.memsize | awk '{printf "%.1f\n",$1/1073741824}'
printf 'Available space: '; df -h "$HOME" | tail -1
for cmd in python3 node npm java adb emulator sdkmanager avdmanager appium curl; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '[OK] %s -> %s\n' "$cmd" "$(command -v "$cmd")"
    case "$cmd" in python3|node|npm|java|appium) "$cmd" --version 2>&1 | head -2 || true ;; esac
  else
    printf '[MISSING] %s\n' "$cmd"
  fi
done
if [ -d "$ANDROID_HOME" ]; then echo "[OK] Android SDK folder: $ANDROID_HOME"; else echo '[MISSING] Android SDK: install Android Studio and run its SDK Setup Wizard'; fi
if command -v emulator >/dev/null 2>&1; then
  printf '\nAvailable Android virtual devices:\n'
  emulator -list-avds || true
fi
if command -v adb >/dev/null 2>&1; then
  printf '\nConnected Android devices:\n'
  adb devices -l || true
fi
if command -v appium >/dev/null 2>&1; then
  printf '\nInstalled Appium drivers:\n'
  appium driver list --installed || true
fi
printf '\nPreflight does not install software or prove that ChatGPT/Gemini are usable in the emulator.\n'
