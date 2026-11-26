#!/usr/bin/env bash
# Optional CLI alternative to Android Studio > Device Manager > Create Device.
# Fails safely if the requested ARM64 Play Store image or Pixel hardware profile is unavailable.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$(uname -s)" != "Darwin" ]; then echo 'Use on Mac only.' >&2; exit 2; fi
# shellcheck disable=SC1091
source "$ROOT/mac_tools/env_mac.sh"
command -v sdkmanager >/dev/null || { echo 'Install Android SDK Command-line Tools (latest) in Android Studio > SDK Manager.' >&2; exit 3; }
command -v avdmanager >/dev/null || { echo 'avdmanager missing; install Android SDK Command-line Tools (latest).' >&2; exit 3; }
IMAGE='system-images;android-35;google_apis_playstore;arm64-v8a'
NAME='Group7_Pixel7_API35'
if emulator -list-avds 2>/dev/null | grep -Fxq "$NAME"; then
  echo "AVD already exists: $NAME. Not overwriting it."
  exit 0
fi
printf 'Installing Android 15 ARM64 Google Play image (may prompt for licenses)...\n'
if ! sdkmanager 'platform-tools' 'emulator' 'platforms;android-35' "$IMAGE"; then
  echo 'Image not available in your SDK configuration; create a Google Play Pixel AVD in Android Studio Device Manager instead.' >&2
  exit 5
fi
if ! avdmanager list device | grep -q 'pixel_7'; then
  echo 'Pixel 7 hardware profile unavailable. Use Android Studio Device Manager to create a Google Play Pixel AVD.' >&2
  exit 5
fi
printf 'no\n' | avdmanager create avd --name "$NAME" --package "$IMAGE" --device 'pixel_7'
printf '\nCreated %s. Start it with: emulator -avd %s\n' "$NAME" "$NAME"
