#!/bin/bash
set -e
cd "$(dirname "$0")"
if python3 - <<'PY' 2>/dev/null
import json,sys,urllib.request
with urllib.request.urlopen('http://127.0.0.1:4723/status',timeout=2) as f:data=json.load(f)
sys.exit(0 if data.get('value',{}).get('ready') else 1)
PY
then
 echo 'The existing Appium server is ready at 127.0.0.1:4723. Reusing it.'
 exit 0
fi
if [[ -f "../../outputs/Group7_D3_Mac_Emulator_Project/mac_tools/env_mac.sh" ]]; then
 source "../../outputs/Group7_D3_Mac_Emulator_Project/mac_tools/env_mac.sh"
fi
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
DEMO_TOOLS="../../outputs/Group7_D3_Mac_Emulator_Project/.tools"
if [[ -d "$DEMO_TOOLS/npm/bin" && -d "$DEMO_TOOLS/node/bin" ]]; then
 export PATH="$PWD/$DEMO_TOOLS/node/bin:$PWD/$DEMO_TOOLS/npm/bin:$PATH"
 export APPIUM_HOME="$PWD/$DEMO_TOOLS/appium-home"
fi
if ! command -v appium >/dev/null 2>&1; then
 echo "The existing Appium executable is unavailable. Use the Appium installation configured for this project. No installation was attempted."
 exit 1
fi
mkdir -p runtime/services
exec appium --address 127.0.0.1 --port 4723 --log "$PWD/runtime/services/appium.log" --log-no-colors
