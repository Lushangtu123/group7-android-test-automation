#!/bin/bash
set -e
cd "$(dirname "$0")"
if [[ -n "${GROUP7_PYTHON:-}" ]]; then
 DEMO_PYTHON="$GROUP7_PYTHON"
elif [[ -x "../../outputs/Group7_D3_Mac_Emulator_Project/.venv/bin/python" ]]; then
 DEMO_PYTHON="../../outputs/Group7_D3_Mac_Emulator_Project/.venv/bin/python"
else
 DEMO_PYTHON="$(command -v python3 || true)"
fi
if [[ -z "$DEMO_PYTHON" ]]; then
 echo 'Select your existing Python environment with GROUP7_PYTHON.'
 exit 1
fi
echo 'Group 7 / Live Android Lab — http://127.0.0.1:8770'
echo 'Keep this terminal open. The Start real demo button runs actual Android tests.'
exec "$DEMO_PYTHON" server.py --open
