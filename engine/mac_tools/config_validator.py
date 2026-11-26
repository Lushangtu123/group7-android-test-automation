#!/usr/bin/env python3
"""Check configuration before launching live Appium tests.

No app identifiers or locators are guessed. Optionally checks the connected
Android device and the actual installed application packages.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

APPS = ('chatgpt', 'gemini')
SELECTORS = ('new_chat_button', 'prompt_input', 'send_button', 'assistant_response_bubbles')
PLACEHOLDER = re.compile(r'(REPLACE_|INSPECT_|TODO_|PLACEHOLDER)', re.I)


def validate_config(config_path, apps=('chatgpt', 'gemini'), device_check=True):
    data = json.loads(Path(config_path).read_text(encoding='utf-8'))
    errors = []
    if not str(data.get('server_url', '')).startswith(('http://127.0.0.1:', 'http://localhost:')):
        errors.append('Expected localhost Appium server_url; verify it explicitly')
    for app in apps:
        spec = data.get('apps', {}).get(app, {})
        caps = spec.get('capabilities', {})
        if str(caps.get('platformName', '')).lower() != 'android':
            errors.append(f'{app}: platformName must be Android')
        if str(caps.get('appium:automationName', '')).lower() != 'uiautomator2':
            errors.append(f'{app}: automationName must be UiAutomator2')
        for name in ('appium:udid', 'appium:appPackage', 'appium:deviceName'):
            val = str(caps.get(name, ''))
            if not val or PLACEHOLDER.search(val):
                errors.append(f'{app}: missing verified {name}')
        for name in SELECTORS:
            entry = spec.get('selectors', {}).get(name, {})
            val = str(entry.get('value', ''))
            by = str(entry.get('by', ''))
            if not val or not by or PLACEHOLDER.search(val):
                errors.append(f'{app}: missing inspected selector {name}')
        if spec.get('capture_mode') not in ('text','accessibility_text_only','copy'):
            errors.append(f'{app}: unsupported capture_mode')
        if spec.get('capture_mode') == 'copy' and not spec.get('selectors', {}).get('copy_response_button'):
            errors.append(f'{app}: copy capture needs inspected copy_response_button')
        if device_check and shutil.which('adb') and not errors:
            udid = caps.get('appium:udid')
            package = caps.get('appium:appPackage')
            try:
                state = subprocess.run(['adb', '-s', udid, 'get-state'], capture_output=True, text=True, timeout=12)
                if state.returncode != 0 or state.stdout.strip() != 'device':
                    errors.append(f'{app}: ADB device {udid} not ready/authorized')
                else:
                    chk = subprocess.run(['adb', '-s', udid, 'shell', 'pm', 'path', package], capture_output=True, text=True, timeout=20)
                    if chk.returncode or 'package:' not in chk.stdout:
                        errors.append(f'{app}: appPackage {package} not installed on {udid}')
            except (OSError, subprocess.TimeoutExpired) as ex:
                errors.append(f'{app}: ADB check failed: {ex}')
        elif device_check and not shutil.which('adb'):
            errors.append('ADB missing; install Android Platform-Tools')
    return errors


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('config')
    p.add_argument('--app', choices=('both',)+APPS, default='both')
    p.add_argument('--skip-device-check', action='store_true', help='For syntax inspection only; not proof of real readiness')
    a = p.parse_args(argv)
    errors = validate_config(a.config, APPS if a.app=='both' else (a.app,), not a.skip_device_check)
    if errors:
        print('CONFIGURATION NOT READY:')
        for error in errors:
            print(' -', error)
        return 2
    print('Configuration structure OK and connected app packages verified.' if not a.skip_device_check else 'Configuration structure OK (device not checked).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
