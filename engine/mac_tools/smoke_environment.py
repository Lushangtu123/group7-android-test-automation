"""Verify Android/Appium infrastructure using Settings, without accessing AI accounts."""
import json
from datetime import datetime, timezone
from pathlib import Path
from appium import webdriver
from appium.options.android import UiAutomator2Options

root = Path(__file__).resolve().parents[1]
out = root / 'verification/mac_install'
out.mkdir(parents=True, exist_ok=True)
options = UiAutomator2Options().load_capabilities({
    'platformName': 'Android',
    'appium:automationName': 'UiAutomator2',
    'appium:udid': 'emulator-5554',
    'appium:deviceName': 'Group7_Pixel7_API35',
    'appium:appPackage': 'com.android.settings',
    'appium:appActivity': '.Settings',
    'appium:noReset': True,
    'appium:forceAppLaunch': True,
    'appium:newCommandTimeout': 60,
})
driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
try:
    package = driver.current_package
    assert package == 'com.android.settings', package
    source = driver.page_source
    assert len(source) > 100
    driver.save_screenshot(str(out / 'android_settings_smoke.png'))
    result = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'result': 'PASS', 'scope': 'Android Settings infrastructure smoke test only',
        'device': 'emulator-5554', 'foreground_package': package,
        'platform_version': driver.capabilities.get('platformVersion'),
        'ui_xml_characters': len(source),
        'chatgpt_gemini_tested': False,
    }
    (out / 'infrastructure_smoke.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
finally:
    driver.quit()
