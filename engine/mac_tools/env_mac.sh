#!/usr/bin/env bash
# Source this file: source mac_tools/env_mac.sh
# No changes are written to ~/.zshrc or other personal shell config.
if [ "$(uname -s)" != "Darwin" ]; then
  echo "ERROR: mac_tools/env_mac.sh must be sourced on macOS." >&2
  return 2 2>/dev/null || exit 2
fi
# Local toolchain installed for Group 7; keeps the project self-contained.
if [ -n "${BASH_VERSION:-}" ]; then
  GROUP7_ENV_SCRIPT="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
  GROUP7_ENV_SCRIPT="${(%):-%x}"
else
  echo 'Source this environment from Bash or Zsh.' >&2
  return 2 2>/dev/null || exit 2
fi
GROUP7_PROJECT_ROOT="$(cd "$(dirname "$GROUP7_ENV_SCRIPT")/.." && pwd)"
if [ -d "$GROUP7_PROJECT_ROOT/.tools/node/bin" ]; then
  export PATH="$GROUP7_PROJECT_ROOT/.tools/npm/bin:$GROUP7_PROJECT_ROOT/.tools/node/bin:$PATH"
  export npm_config_prefix="$GROUP7_PROJECT_ROOT/.tools/npm"
  export npm_config_cache="$GROUP7_PROJECT_ROOT/.tools/npm-cache"
  export APPIUM_HOME="$GROUP7_PROJECT_ROOT/.tools/appium-home"
fi
if [ -z "${JAVA_HOME:-}" ]; then
  GROUP7_JAVA="$(/usr/libexec/java_home -v 21 2>/dev/null || true)"
  if [ -n "$GROUP7_JAVA" ]; then export JAVA_HOME="$GROUP7_JAVA"; fi
fi
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
if [ -z "${JAVA_HOME:-}" ]; then
  if [ -x /usr/libexec/java_home ]; then
    FOUND_JAVA="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
    if [ -n "$FOUND_JAVA" ]; then export JAVA_HOME="$FOUND_JAVA"; fi
  fi
  if [ -z "${JAVA_HOME:-}" ] && [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
    export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  fi
fi
if [ -n "${JAVA_HOME:-}" ]; then export PATH="$JAVA_HOME/bin:$PATH"; fi
printf 'ANDROID_HOME=%s\nJAVA_HOME=%s\n' "$ANDROID_HOME" "${JAVA_HOME:-UNSET}"
