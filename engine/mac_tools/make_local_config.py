#!/usr/bin/env python3
"""Create a local Appium configuration with the emulator serial.

App packages and UI locators must still be inspected on the actual installed
apps; this helper deliberately never invents them.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def make_config(serial, chatgpt_package=None, gemini_package=None, dest=None):
    if not serial or not serial.strip():
        raise ValueError('ADB serial is required, e.g. emulator-5554')
    template = ROOT/'data'/'android_appium_config.example.json'
    target = dest or ROOT/'data'/'android_appium_config.local.json'
    target = Path(target)
    if target.exists():
        raise FileExistsError(f'Not overwriting existing local config: {target}')
    data = json.loads(template.read_text(encoding='utf-8'))
    for app in ('chatgpt','gemini'):
        caps = data['apps'][app]['capabilities']
        caps['appium:udid'] = serial.strip()
        caps['appium:deviceName'] = serial.strip()
    if chatgpt_package:
        data['apps']['chatgpt']['capabilities']['appium:appPackage'] = chatgpt_package.strip()
    if gemini_package:
        data['apps']['gemini']['capabilities']['appium:appPackage'] = gemini_package.strip()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    return target


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--serial',required=True,help='Exact device ID from adb devices')
    p.add_argument('--chatgpt-package',default='',help='Exact INSPECTED installed package, optional')
    p.add_argument('--gemini-package',default='',help='Exact INSPECTED installed package, optional')
    args=p.parse_args()
    result=make_config(args.serial,args.chatgpt_package,args.gemini_package)
    print('Created:',result)
    print('NEXT: Replace ALL remaining REPLACE_WITH... UI selectors based on Appium Inspector.')
    print('Do not run live tests until mac_tools/config_validator.py passes.')

if __name__=='__main__':main()
