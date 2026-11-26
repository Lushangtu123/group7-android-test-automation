"""Configurable Android Appium 2 / UiAutomator2 UI adapter.

This is a NEW RECONSTRUCTED implementation, not the original team live runner.
Selectors must be inspected against each installed app and verified on device.
No account credentials, hardcoded package names, or fabricated live responses.
"""
import json
import re
import time
import warnings
import subprocess
from pathlib import Path
from uuid import uuid4


class LiveAdapter:
    """Drive one app through a real Appium WebDriver session."""

    def __init__(self, config_path, app, driver=None):
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.cfg = cfg
        if app not in cfg.get('apps', {}):
            raise ValueError(f'No app configuration for {app}')
        self.app = app
        self.spec = cfg['apps'][app]
        self._validate()
        self.poll = float(cfg.get('poll_seconds', 0.5))
        self.timeout = float(cfg.get('timeout_seconds', 90))
        self.stable = float(cfg.get('stable_seconds', 3))
        if driver is not None:
            self.driver = driver
            if self.spec.get('uiautomator_settings'):self.driver.update_settings(self.spec['uiautomator_settings'])
            return
        try:
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
        except ImportError as exc:
            raise RuntimeError('Install mobile dependencies: pip install -r requirements-optional-appium.txt') from exc
        opts = UiAutomator2Options().load_capabilities(self.spec['capabilities'])
        self._prelaunch_host_cleanup()
        self.driver = webdriver.Remote(cfg.get('server_url', 'http://127.0.0.1:4723'), options=opts)
        if self.spec.get('uiautomator_settings'):self.driver.update_settings(self.spec['uiautomator_settings'])

    def _validate(self):
        spec = self.spec
        if spec.get('platform', '').lower() != 'android':
            raise ValueError('This reconstructed live adapter is Android/UiAutomator2 only')
        caps = spec.get('capabilities', {})
        if caps.get('platformName', '').lower() != 'android':
            raise ValueError('platformName must be Android')
        if str(caps.get('appium:automationName', '')).lower() != 'uiautomator2':
            raise ValueError('appium:automationName must be UiAutomator2')
        if not caps.get('appium:appPackage'):
            raise ValueError('The inspected appPackage is required')
        required = ('new_chat_button', 'prompt_input', 'send_button', 'assistant_response_bubbles')
        for key in required:
            loc = spec.get('selectors', {}).get(key, {})
            if not loc.get('by') or not loc.get('value'):
                raise ValueError(f'App {self.app} missing selector: {key}')
        if caps.get('appium:appWaitForLaunch') is False and not spec.get('selectors', {}).get('new_chat_ready_marker'):
            raise ValueError('Nonblocking launch requires an inspected new-chat readiness marker')
        if spec.get('prelaunch_stop_host', False):
            host = caps.get('appium:appWaitPackage')
            if (not host or host == caps.get('appium:appPackage') or
                    not self.cfg.get('adb_path') or not caps.get('appium:udid')):
                raise ValueError('Prelaunch host cleanup requires a distinct inspected host, device and adb path')
        if spec.get('copy_response_action') not in (None, 'mobile: clickGesture'):
            raise ValueError('Unsupported copy action; use native click or mobile: clickGesture')
        if spec.get('selectors', {}).get('response_copy_parent_relative') and not (
                self.app == 'chatgpt' and spec.get('capture_mode') == 'copy'
                and spec.get('copy_response_action') == 'mobile: clickGesture'
                and spec.get('selectors', {}).get('response_copy_relative')
                and self.cfg.get('atomic_response_snapshot') and self.cfg.get('verify_prompt_text')):
            raise ValueError('Clickable parent recovery requires scoped Copy, verified input and atomic ownership')
        if spec.get('selectors', {}).get('enabled_send_control') and not (
                self.app == 'chatgpt' and self.cfg.get('verify_prompt_text')
                and spec['selectors'].get('disabled_send_control')):
            raise ValueError('Send readiness recovery requires inspected enabled/disabled controls and exact input verification')
        if spec.get('allow_initial_capitalization') and not (
                self.cfg.get('atomic_response_snapshot') and self.cfg.get('verify_prompt_text')):
            raise ValueError('Rendered capitalization policy requires exact pre-send verification and atomic ownership')
        if spec.get('native_full_response_capture') and not (self.app=='gemini' and
                self.cfg.get('atomic_response_snapshot') and self.cfg.get('verify_prompt_text') and
                spec.get('selectors',{}).get('new_chat_ready_marker')):
            raise ValueError('Native viewport proof requires inspected Gemini readiness, verified input and atomic ownership')
        if spec.get('capture_mode')=='native_full_response' and not spec.get('native_full_response_capture'):
            raise ValueError('Enable the inspected complete native proof feature for native_full_response mode')
        idle = spec.get('uiautomator_settings', {}).get('waitForIdleTimeout', 10000)
        if idle < 10000 and not (self.cfg.get('atomic_response_snapshot') and
                self.cfg.get('verify_prompt_text') and spec.get('selectors', {}).get('new_chat_ready_marker')):
            raise ValueError('Reduced native idle wait requires atomic, prompt and readiness state validation')
        blob = json.dumps(spec)
        if re.search(r'(REPLACE_|INSPECT_|TODO_|PLACEHOLDER)', blob, re.I):
            raise ValueError('Replace unverified app identifiers and UI selectors using Appium Inspector')
        if self.cfg.get('timeout_seconds', 90) <= 0:
            raise ValueError('timeout_seconds must be positive')

    @staticmethod
    def _locator(entry):
        names = {
            'id': 'id', 'xpath': 'xpath', 'accessibility id': 'accessibility id',
            'class name': 'class name', 'android uiautomator': '-android uiautomator',
        }
        kind = entry['by'].lower().strip()
        if kind not in names:
            raise ValueError(f'Unsupported locator type: {kind}')
        return (names[kind], entry['value'])

    def _prelaunch_host_cleanup(self):
        self.startup_observation = {'host_stopped':False}
        if not self.spec.get('prelaunch_stop_host', False):
            return
        caps = self.spec['capabilities']
        host = caps['appium:appWaitPackage']
        command = [self.cfg['adb_path'], '-s', caps['appium:udid'],
                   'shell', 'am', 'force-stop', host]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
        self.startup_observation = {'host_stopped':True, 'package':host,
            'command':command, 'exit_code':result.returncode, 'at_unix_seconds':time.time(),
            'account_data_cleared':False}

    def _elements(self, name):
        spec = self.spec['selectors'][name]
        return self.driver.find_elements(*self._locator(spec))

    def _find(self, name):
        end = time.monotonic() + self.timeout
        while time.monotonic() < end:
            if self.app == 'chatgpt' and name in ('new_chat_menu_button', 'new_chat_ready_marker'):
                self._dismiss_inspected_introduction()
            if name == 'new_chat_menu_button':
                self._cancel_unused_feature_notice()
            hits = self._elements(name)
            if hits:
                return hits[-1] if name in ('assistant_response_bubbles', 'copy_response_button', 'response_actions_button') else hits[0]
            time.sleep(self.poll)
        raise TimeoutError(f'No visible UI element for selector {name}; inspect app UI')

    def _dismiss_inspected_introduction(self):
        from .informational_sheet import known_informational_sheet
        notice = known_informational_sheet(self.driver.page_source)
        if notice is None:
            return
        observation = getattr(self, 'last_reset_observation', {})
        if observation.get('informational_sheet_close_requested'):
            return
        prefix = getattr(self, '_conversation_evidence_prefix', None)
        if prefix is not None:
            self._write_evidence(str(prefix) + '_introduction_before')
        selector = ("//*[@package='com.openai.chatgpt' and @content-desc='Close' and @window-id="
                    + self._xpath_literal(notice['window_id']) + "]")
        buttons = self.driver.find_elements('xpath', selector)
        if len(buttons) != 1:
            raise RuntimeError('Inspected introduction has no unique scoped Close control')
        buttons[0].click()
        observation['informational_sheet_close_requested'] = notice
        self.last_reset_observation = observation
        if prefix is not None:
            self._write_evidence(str(prefix) + '_introduction_after')
            Path(str(prefix) + '.introduction_recovery.json').write_text(json.dumps({
                'action': 'Close inspected temporary-chat introduction',
                'prompt_resent': False, 'acknowledged_continue': False,
                'notice': notice, 'subsequent_ready_marker_required': True,
            }, indent=2), encoding='utf-8')

    def _cancel_unused_feature_notice(self):
        notice = self.spec.get('startup_notice_cancel')
        if not notice:
            return
        import xml.etree.ElementTree as ET
        nodes = list(ET.fromstring(self.driver.page_source).iter())
        titles = [n for n in nodes if n.get('resource-id') == notice['title_resource_id'] and
                  n.get('text') == notice['title_text'] and n.get('displayed','true') != 'false']
        if not titles:
            return
        observation = getattr(self, 'last_reset_observation', {})
        if observation.get('startup_notice_cancelled'):
            return  # Wait for disappearance; never repeatedly click a fading dialog.
        title = titles[-1]
        candidates = [n for n in nodes if n.get('resource-id') == notice['cancel_resource_id'] and
                      n.get('text') == notice['cancel_text'] and n.get('package') == title.get('package') and
                      n.get('window-id') == title.get('window-id')]
        if not candidates:
            raise RuntimeError('Known unused-feature notice has no explicit cancellation control')
        prefix = getattr(self, '_conversation_evidence_prefix', None)
        if prefix is not None:
            self._write_evidence(str(prefix) + '_unused_notice_before')
        selector = f"//*[@resource-id={self._xpath_literal(notice['cancel_resource_id'])} and @text={self._xpath_literal(notice['cancel_text'])} and @package={self._xpath_literal(title.get('package',''))}]"
        buttons = self.driver.find_elements('xpath', selector)
        if not buttons:
            raise RuntimeError('Explicit cancellation control disappeared; startup remains unverified')
        buttons[-1].click()
        observation['startup_notice_cancelled'] = True
        observation['startup_notice_title'] = notice['title_text']
        self.last_reset_observation = observation
        if prefix is not None:
            self._write_evidence(str(prefix) + '_unused_notice_after')

    def _response_text(self, bubble):
        descendants = self.spec['selectors'].get('response_text_nodes')
        if descendants:
            parts = bubble.find_elements(*self._locator(descendants))
            texts = [(part.text or '').strip() for part in parts]
            return '\n'.join(text for text in texts if text)
        return (bubble.text or '').strip()

    def prepare_conversation(self, folder, conversation):
        self._conversation_evidence_prefix = Path(folder) / f'{self.app}_conversation{conversation}_reset'

    def _recover_appium_settings_anr(self, prefix):
        from .android_snapshot import appium_settings_anr
        source = self.driver.page_source
        if not appium_settings_anr(source):
            return
        observation = Path(str(prefix) + '_helper_anr.xml')
        observation.parent.mkdir(parents=True, exist_ok=True)
        observation.write_text(source, encoding='utf-8')
        self._write_evidence(str(prefix) + '_helper_anr', capture_xml=False)
        self.driver.terminate_app('io.appium.settings')
        deadline = time.monotonic() + 5
        while appium_settings_anr(self.driver.page_source):
            if time.monotonic() >= deadline:
                raise RuntimeError('Appium Settings ANR remains after scoped helper stop')
            time.sleep(self.poll)
        Path(str(prefix) + '.helper_anr_recovery.json').write_text(json.dumps({
            'at_unix_seconds': time.time(), 'action': 'terminate io.appium.settings',
            'before_new_conversation': True, 'prompt_resent': False,
            'target_app_restarted': False, 'modal_dismissal_verified': True,
        }, indent=2), encoding='utf-8')

    def new_chat(self):
        self.last_reset_observation = {'started_monotonic':time.monotonic(),
                                       'previous_generation_stopped':False}
        prefix = getattr(self, '_conversation_evidence_prefix', None)
        if prefix is not None and self.cfg.get('recover_appium_settings_anr_at_case_boundary'):
            self._recover_appium_settings_anr(prefix)
        if 'response_generating_marker' in self.spec['selectors']:
            generating = self._elements('response_generating_marker')
            if generating:
                if prefix is not None:
                    self._write_evidence(str(prefix) + '_before_stopping_previous_generation')
                generating[-1].click()
                self.last_reset_observation['previous_generation_stopped'] = True
                deadline = time.monotonic() + self.timeout
                while self._elements('response_generating_marker'):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Previous generation did not stop before new conversation')
                    time.sleep(self.poll)
        if 'new_chat_menu_button' in self.spec['selectors']:
            self._find('new_chat_menu_button').click()
        self._find('new_chat_button').click()
        time.sleep(float(self.cfg.get('chat_reset_wait_seconds', 1.0)))
        if 'new_chat_final_button' in self.spec['selectors']:
            self._find('new_chat_final_button').click()
            time.sleep(float(self.cfg.get('chat_reset_wait_seconds', 1.0)))
        if 'new_chat_ready_marker' in self.spec['selectors']:
            self._find('new_chat_ready_marker')
        # Verify input is reachable after a new chat
        self._find('prompt_input')
        self.last_reset_observation['ready_monotonic'] = time.monotonic()
        if prefix is not None:
            self._write_evidence(str(prefix) + '_ready')
            Path(str(prefix) + '.json').write_text(json.dumps(self.last_reset_observation,indent=2),encoding='utf-8')

    def _write_evidence(self, prefix, capture_xml=True):
        p = Path(prefix)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(str(p.with_suffix('.png')))
        if capture_xml:
            p.with_suffix('.xml').write_text(self.driver.page_source, encoding='utf-8')

    def capture_error(self, folder):
        self._write_evidence(Path(folder) / 'ERROR')

    @staticmethod
    def _xpath_literal(text):
        if "'" not in text:return "'" + text + "'"
        if '"' not in text:return '"' + text + '"'
        return "concat(" + ", \"'\", ".join("'"+part+"'" for part in text.split("'")) + ")"

    def _turn_bubbles(self, prompt, before):
        template=self.spec['selectors'].get('assistant_response_after_prompt_xpath')
        if template and before:
            rendered = getattr(self, '_last_rendered_prompt', None) or prompt
            return self.driver.find_elements('xpath',template.replace('{prompt}',self._xpath_literal(rendered))), True
        return self._elements('assistant_response_bubbles'), False

    def _copy_hits(self, bubble):
        relative=self.spec['selectors'].get('response_copy_relative')
        if relative:return bubble.find_elements(*self._locator(relative))
        return self._elements('copy_response_button')

    def _poll_for_fresh_copy(self, sentinel, prefix):
        deadline = time.monotonic() + float(self.cfg.get('clipboard_wait_seconds', 5))
        observed = None
        while time.monotonic() < deadline:
            observed = (self._read_clipboard(prefix) or '').strip()
            if observed and observed != sentinel:
                return observed, True
            time.sleep(self.poll)
        return observed, False

    def _retry_copy_on_clickable_parent(self, prompt, before, expected_text, prefix, sentinel):
        self._write_evidence(str(prefix) + '_copy_nonce_unchanged')
        self._dismiss_clipboard_overlay()
        visible_text, current_bubble = self._wait_atomic_response(
            prompt, before, str(prefix) + '.copy_retry_ready.state.jsonl', known_prompt_seen=True)
        parents = current_bubble.find_elements(
            *self._locator(self.spec['selectors']['response_copy_parent_relative']))
        if visible_text != expected_text or len(parents) != 1:
            raise RuntimeError('Copy retry cannot prove one clickable parent for the same completed response')
        current_clipboard = (self._read_clipboard(prefix) or '').strip()
        if current_clipboard != sentinel:
            # A delayed first copy is still validated for full visible agreement below.
            return current_clipboard, bool(current_clipboard), False
        parent = parents[0]
        Path(str(prefix) + '.copy_action_retry.json').write_text(json.dumps({
            'action': 'native_click_on_verified_copy_parent',
            'element_id': getattr(parent, 'id', None),
            'element_rect': getattr(parent, 'rect', None),
            'reason': 'Initial scoped Copy gesture did not replace the unique clipboard marker',
            'scoped_to_same_completed_response': True,
            'prompt_resent': False,
        }, indent=2), encoding='utf-8')
        parent.click()
        copied, fresh = self._poll_for_fresh_copy(sentinel, prefix)
        return copied, fresh, True

    def _read_clipboard(self, diagnostic_prefix):
        try:
            return self.driver.get_clipboard_text()
        except Exception as exc:
            message = str(exc).lower()
            helper_timeout = ('cannot retrieve the current clipboard content' in message and
                              'timed out' in message and
                              ('io.appium.settings' in message or 'appium settings' in message))
            if (not self.cfg.get('recover_clipboard_helper_once', False) or
                    not helper_timeout or getattr(self, '_clipboard_recoveries', 0) >= 1):
                raise
            self._clipboard_recoveries = 1
            self._write_evidence(str(diagnostic_prefix) + '_clipboard_helper_timeout')
            audit = Path(str(diagnostic_prefix) + '.clipboard_recovery.jsonl')
            audit.parent.mkdir(parents=True, exist_ok=True)
            with audit.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'at_unix_seconds':time.time(),
                    'original_error':str(exc), 'recovery':'terminate io.appium.settings; retry clipboard read once',
                    'prompt_resent':False, 'target_app_restarted':False})+'\n')
            # The driver starts its helper on the following read and restores
            # the current application/IME. Never restart the app under test.
            self.driver.terminate_app('io.appium.settings')
            return self.driver.get_clipboard_text()

    def _dismiss_clipboard_overlay(self, expect_overlay=False):
        if not self.cfg.get('manage_clipboard_overlay', False):
            return
        def trace(phase, **values):
            prefix = getattr(self, '_diagnostic_prefix', None)
            if prefix is not None:
                path = Path(str(prefix) + '.overlay.jsonl')
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('a', encoding='utf-8') as handle:
                    handle.write(json.dumps({'at_monotonic':time.monotonic(),
                        'phase':phase, 'expect_overlay':expect_overlay, **values})+'\n')
        from .android_snapshot import clipboard_overlay_state
        limit = float(self.cfg.get('overlay_timeout_seconds', 3))
        arrival_deadline = time.monotonic() + limit
        control_deadline = None
        dismissal_deadline = None
        while True:
            state = clipboard_overlay_state(self.driver.page_source)
            now = time.monotonic()
            trace('atomic_overlay', **state)
            if not state['present']:
                if dismissal_deadline is not None or not expect_overlay or now >= arrival_deadline:
                    return
            elif dismissal_deadline is not None:
                if now >= dismissal_deadline:
                    prefix = getattr(self, '_diagnostic_prefix', None)
                    if prefix is not None:
                        self._write_evidence(str(prefix) + '_overlay_timeout')
                    raise RuntimeError('System clipboard overlay still obstructs the application')
            else:
                if control_deadline is None:
                    control_deadline = now + limit
                clicked = False
                if state['dismiss_available']:
                    hits = self.driver.find_elements('id', 'com.android.systemui:id/dismiss_button')
                    if hits:
                        try:
                            hits[-1].click()
                            clicked = True
                        except Exception as exc:
                            if exc.__class__.__name__ not in ('StaleElementReferenceException','NoSuchElementException'):
                                raise
                            trace('dismiss_control_disappeared')
                if clicked:
                    trace('dismiss_clicked')
                    dismissal_deadline = time.monotonic() + limit
                elif time.monotonic() >= control_deadline:
                    prefix = getattr(self, '_diagnostic_prefix', None)
                    if prefix is not None:
                        self._write_evidence(str(prefix) + '_overlay_control_timeout')
                    raise RuntimeError('System clipboard overlay has no available dismissal control')
            time.sleep(self.poll)

    def _wait_atomic_response(self, prompt, before, audit_path, known_prompt_seen=False):
        from .android_snapshot import appium_settings_anr, read_snapshot, ResponseBudget
        budget = ResponseBudget(time.monotonic(), self.timeout,
                                self.cfg.get('capture_navigation_seconds', 120),
                                self.cfg.get('capture_stall_seconds', 15))
        prompt_seen = bool(known_prompt_seen)
        previous = None
        stable_since = None
        while True:
            source = self.driver.page_source
            if appium_settings_anr(source):
                raise RuntimeError('Appium Settings ANR obstructed the current response')
            state = read_snapshot(source, self.app, prompt, prompt_seen=prompt_seen,
                allow_initial_capitalization=self.spec.get('allow_initial_capitalization',False))
            if state.get('matched_prompt_text') is not None:
                self._last_rendered_prompt = state['matched_prompt_text']
                self._last_prompt_match = state['prompt_match']
            prompt_seen = prompt_seen or state['prompt_present']
            reply = state['reply']
            for label in (reply or {}).get('excluded_ui_metadata',[]):
                if label not in getattr(self,'_excluded_native_ui_labels',[]):
                    self._excluded_native_ui_labels=getattr(self,'_excluded_native_ui_labels',[])+[label]
            current = reply['text'] if reply else None
            signature = (current, reply.get('copy_bounds'), reply.get('body_bounds'),
                         state.get('fixed_input_top')) if current else None
            budget.observe(time.monotonic(), state['generating'],
                           signature if prompt_seen else None)
            if signature != previous or state['generating']:
                stable_since = time.monotonic()
            previous = signature
            complete = (prompt_seen and reply and reply['footer_completed'] and
                        not state['generating'] and not state['clipboard_overlay'])
            with Path(audit_path).open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'at_monotonic':time.monotonic(),
                    'prompt_present':state['prompt_present'], 'prompt_seen':prompt_seen,
                    'matched_prompt_text':state.get('matched_prompt_text'),
                    'prompt_match':state.get('prompt_match'),
                    'generating':state['generating'], 'overlay':state['clipboard_overlay'],
                    'fixed_input_top':state.get('fixed_input_top'),
                    'copy_bounds':reply.get('copy_bounds') if reply else None,
                    'characters':len(current or ''), 'completed':bool(complete)})+'\n')
            if complete and current and stable_since is not None and time.monotonic()-stable_since >= self.stable:
                bounds = reply.get('copy_bounds')
                numbers = list(map(int, re.findall(r'\d+', bounds or '')))
                safe_bottom = self.spec.get('response_footer_max_y', 2100)
                if state.get('fixed_input_top') is not None:
                    safe_bottom = min(safe_bottom, state['fixed_input_top'] - 12)
                if numbers and numbers[3] > safe_bottom:
                    self.driver.execute_script('mobile: swipeGesture', {
                        'left':300,'top':450,'width':650,'height':1250,
                        'direction':'up','percent':0.6})
                    stable_since = time.monotonic()
                else:
                    # Reacquire only after the atomic snapshot proves completion.
                    hits, _ = self._turn_bubbles(prompt, before)
                    if not hits:
                        hits = self._elements('assistant_response_bubbles')
                    if hits:
                        return current, hits[-1]
            elif (prompt_seen and reply and current and not state['generating'] and
                  not state['clipboard_overlay'] and not reply['footer_completed'] and
                  stable_since is not None and time.monotonic()-stable_since >= self.stable):
                self.driver.execute_script('mobile: swipeGesture', {
                    'left':300,'top':450,'width':650,'height':1250,
                    'direction':'up','percent':0.6})
                stable_since = time.monotonic()
            time.sleep(self.poll)

    def _capture_complete_native_response(self, prompt, diagnostic_prefix):
        """Prove accessible text from completed footer back to current prompt.

        Each earlier viewport must overlap the already recorded suffix. No
        missing paragraph is inferred, no global deduplication is performed,
        and non-text media remain screenshot/XML evidence, not transcriptions.
        """
        from .native_response import gemini_native_view, prepend_overlapping
        import hashlib
        if self.app != 'gemini':
            raise ValueError('Native viewport proof is inspected for Gemini only')
        deadline=time.monotonic()+float(self.cfg.get('native_capture_seconds',120))
        proof={'complete_accessible_text_proven':False,'views':[],
               'requested_prompt':prompt,'completed_footer_confirmed':False,
               'start_prompt_confirmed':False,'full_response_parts':[],
               'nontext_media_transcribed':False,
               'scope':'All accessible TextView/code text in the current response; media remain raw screenshots/XML'}
        path=Path(str(diagnostic_prefix)+'.native_proof.json');path.parent.mkdir(parents=True,exist_ok=True)
        combined=[];last_frame_hash=None;last_progress=time.monotonic()
        try:
            for index in range(60):
                previous=None;stable_since=time.monotonic()
                while time.monotonic()<deadline:
                    source=self.driver.page_source
                    view=gemini_native_view(source,prompt,True,self.spec.get('allow_initial_capitalization',False))
                    signature=json.dumps([view['parts'],view['body_bounds'],view['user_bounds'],view['footer_completed']])
                    if signature!=previous:stable_since=time.monotonic()
                    previous=signature
                    if time.monotonic()-stable_since>=self.stable:break
                    time.sleep(self.poll)
                else:raise TimeoutError('Native full-response capture deadline exceeded')
                frame=Path(str(diagnostic_prefix)+f'_native_view_{index:02}')
                png=Path(str(frame)+'.png');xml=Path(str(frame)+'.xml')
                self.driver.save_screenshot(str(png));xml.write_text(source,encoding='utf-8')
                frame_hash=hashlib.sha256(png.read_bytes()).hexdigest()
                item={**view,'xml_file':xml.name,'png_file':png.name,
                      'xml_sha256':hashlib.sha256(source.encode()).hexdigest(),
                      'png_sha256':frame_hash,'at_monotonic':time.monotonic()}
                proof['views'].append(item)
                if index==0:
                    if not view['footer_completed']:raise RuntimeError('Native capture lacks current completed-response footer')
                    proof['completed_footer_confirmed']=True;combined=list(view['parts']);item['overlap_parts']=None
                else:
                    combined,overlap=prepend_overlapping(view['parts'],combined);item['overlap_parts']=overlap
                proof['full_response_parts']=combined
                if view['start_prompt_confirmed']:
                    proof.update(start_prompt_confirmed=True,complete_accessible_text_proven=True,
                                 full_response_text='\n'.join(combined),
                                 final_view_position='START_OF_CURRENT_RESPONSE')
                    path.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding='utf-8')
                    return proof['full_response_text']
                if frame_hash!=last_frame_hash:last_progress=time.monotonic()
                elif time.monotonic()-last_progress>float(self.cfg.get('capture_stall_seconds',15)):
                    raise TimeoutError('Native full-response capture made no observed viewport progress')
                last_frame_hash=frame_hash
                # The inspected history margin is outside selectable text and
                # embedded image/video cards. Do not long-press response text.
                x=view['scroll_margin_x'];safe_bottom=min(view.get('fixed_input_top') or 2100,2100)-80
                start_y=min(650,safe_bottom-650);end_y=start_y+600
                if start_y<350 or end_y>safe_bottom:raise RuntimeError('Native capture has no inspected safe scroll corridor')
                self.driver.execute_script('mobile: dragGesture',{'startX':x,'startY':start_y,'endX':x,'endY':end_y,'speed':1800})
            raise TimeoutError('Native full-response viewport limit exceeded')
        except Exception as exc:
            proof['error']=str(exc);path.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding='utf-8');raise

    def _await_enabled_send_control(self, prompt, prefix):
        """Select the actual clickable send control before the only send action."""
        started = time.monotonic()
        deadline = started + float(self.cfg.get('prompt_verify_seconds', 15))
        reentry_at = started + float(self.cfg.get('send_control_reentry_after_seconds', 3))
        reentered = False
        while time.monotonic() < deadline:
            inputs = self._elements('prompt_input')
            if len(inputs) != 1 or inputs[0].text != prompt:
                if not reentered or (len(inputs) == 1 and inputs[0].text not in ('', None)):
                    raise RuntimeError('Exact prompt no longer present in the only composer; submission blocked')
                time.sleep(self.poll)
                continue
            controls = self._elements('enabled_send_control')
            if len(controls) == 1:
                return controls[0]
            if len(controls) > 1:
                raise RuntimeError('Multiple enabled send controls; submission blocked')
            if (not reentered and time.monotonic() >= reentry_at
                    and len(self._elements('disabled_send_control')) == 1):
                self._write_evidence(str(prefix) + '_send_control_disabled')
                Path(str(prefix) + '.send_control_recovery.json').write_text(json.dumps({
                    'reason': 'Exact test prompt remained in the composer with its send control disabled',
                    'action': 'clear unsent input and retype using mobile: type',
                    'prior_send_count': 0, 'prompt_resent': False,
                }, indent=2), encoding='utf-8')
                inputs[0].clear()
                self.driver.execute_script('mobile: type', {'text':prompt})
                reentered = True
            time.sleep(self.poll)
        raise TimeoutError('Send control stayed disabled; no prompt was submitted')

    def send(self, prompt, case_id, turn_idx, screenshot_dir):
        """Submit a prompt and return the fresh stable text of a NEW response bubble.

        Requires a newly completed response; supports virtualized message lists.
        Copy-based capture is optional and must be explicitly configured/verified.
        """
        self._clipboard_recoveries = 0
        self._last_rendered_prompt = None
        self._last_prompt_match = None
        self._excluded_native_ui_labels = []
        self._diagnostic_prefix = Path(screenshot_dir) / f'{self.app}_{case_id}_{turn_idx}'
        bubbles_before = self._elements('assistant_response_bubbles')
        before = len(bubbles_before)
        before_text = self._response_text(bubbles_before[-1]) if before else None
        self._dismiss_clipboard_overlay()
        entry = self._find('prompt_input')
        entry.click()
        self._find('prompt_input').send_keys(prompt)
        if self.cfg.get('verify_prompt_text', False):
            verify_until = time.monotonic() + float(self.cfg.get('prompt_verify_seconds', 15))
            while (self._find('prompt_input').text or '') != prompt:
                if time.monotonic() >= verify_until:
                    raise RuntimeError('Typed prompt does not match the requested prompt; submission blocked')
                time.sleep(self.poll)
            time.sleep(float(self.cfg.get('input_settle_seconds', 1)))
        diagnostic_prefix = Path(screenshot_dir) / f'{self.app}_{case_id}_{turn_idx}'
        send_control = self._await_enabled_send_control(prompt, diagnostic_prefix) if (
            'enabled_send_control' in self.spec['selectors']) else None
        if self.cfg.get('capture_submission_evidence', False):
            self._write_evidence(str(diagnostic_prefix) + '_before_send')
        (send_control if send_control is not None else self._find('send_button')).click()
        if self.cfg.get('capture_submission_evidence', False):
            time.sleep(0.5)
            self._write_evidence(str(diagnostic_prefix) + '_after_send')
        deadline = time.monotonic() + self.timeout
        last_text = None
        stable_since = None
        fresh_bubble = None
        last_scroll = float('-inf')
        atomic_result = None
        if self.cfg.get('atomic_response_snapshot', False):
            diagnostic_prefix.parent.mkdir(parents=True, exist_ok=True)
            atomic_result = self._wait_atomic_response(prompt, before,
                str(diagnostic_prefix)+'.state.jsonl')
            last_text, fresh_bubble = atomic_result
        while time.monotonic() < deadline:
            if atomic_result is not None:
                break
            # Check completion first, then reacquire the response: the UI can replace
            # its element or append text while we wait for the completion signal.
            markers = (self._elements('response_finished_marker')
                       if 'response_finished_marker' in self.spec['selectors'] else None)
            finished = markers is None or bool(markers)
            if markers and self.spec.get('response_footer_max_y') is not None:
                rect = markers[-1].rect
                finished = rect['y'] + rect['height'] <= self.spec['response_footer_max_y']
            generating = ('response_generating_marker' in self.spec['selectors'] and
                          bool(self._elements('response_generating_marker')))
            finished = finished and not generating
            bubbles, anchored = self._turn_bubbles(prompt, before)
            fresh = False
            if bubbles:
                fresh_bubble = bubbles[-1]
                current = self._response_text(fresh_bubble)
                # Recycler views can evict an old message as a new one appears.
                # An unchanged old answer never becomes fresh just because its
                # native element ID was rerendered.
                fresh = anchored or len(bubbles) > before or current != before_text
                if fresh and current and current == last_text and stable_since is not None:
                    if finished and time.monotonic() - stable_since >= self.stable:
                        break
                elif fresh:
                    last_text = current
                    stable_since = time.monotonic()
            if (not generating and (not fresh or not finished) and
                    'response_scroll_container' in self.spec['selectors'] and
                    time.monotonic() - last_scroll >= 2):
                containers = self._elements('response_scroll_container')
                if containers:
                    gesture = self.spec.get('response_scroll_gesture') or {
                        'elementId':containers[-1].id, 'direction':'down', 'percent':0.8}
                    self.driver.execute_script(self.spec.get('response_scroll_action','mobile: scrollGesture'), gesture)
                last_scroll = time.monotonic()
            time.sleep(self.poll)
        else:
            raise TimeoutError(f'New stable response bubble unavailable: {self.app}/{case_id}/{turn_idx}')
        captured = last_text
        mode = self.spec.get('capture_mode', 'text')
        actual_mode = mode
        if mode == 'native_full_response':
            captured=self._capture_complete_native_response(prompt,diagnostic_prefix)
            last_text=captured
            mode='verified_native_text'
            actual_mode='native_full_response_viewport_proof'
        elif mode == 'copy_or_text':
            if 'copy_response_button' not in self.spec['selectors']:
                raise ValueError('copy_or_text requires inspected copy_response_button')
            if self._copy_hits(fresh_bubble):
                mode = 'copy'
                actual_mode = 'copy'
            else:
                if self.spec.get('native_full_response_capture', False):
                    captured=self._capture_complete_native_response(prompt,diagnostic_prefix)
                    last_text=captured
                    mode='verified_native_text'
                    actual_mode='native_full_response_viewport_proof'
                elif self.spec.get('require_full_response_copy', False):
                    raise RuntimeError('Complete response Copy unavailable; native fallback coverage unverified')
                else:
                    mode = 'text'
                    actual_mode = 'native_text_copy_unavailable'
        if mode == 'copy':
            if 'copy_response_button' not in self.spec.get('selectors', {}):
                raise ValueError('copy capture requires inspected copy_response_button selector')
            baseline = self._read_clipboard(diagnostic_prefix) or ''
            sentinel = 'GROUP7_COPY_CHECK_' + uuid4().hex
            self.driver.set_clipboard_text(sentinel)
            self._dismiss_clipboard_overlay(expect_overlay=True)
            try:
                if self.cfg.get('atomic_response_snapshot', False):
                    # Clipboard/IME preparation can reflow rich content. Recheck
                    # the same proven turn and current footer before its action.
                    last_text, fresh_bubble = self._wait_atomic_response(prompt, before,
                        str(diagnostic_prefix)+'.copy_ready.state.jsonl', known_prompt_seen=True)
                fresh_bubble.click() if self.spec.get('tap_bubble_before_copy', False) else None
                if 'response_actions_button' in self.spec['selectors']:
                    self._find('response_actions_button').click()
                targets=self._copy_hits(fresh_bubble)
                if not targets:raise RuntimeError('Current response has no scoped Copy action')
                action = self.spec.get('copy_response_action')
                target = targets[-1]
                action_audit = Path(str(diagnostic_prefix)+'.copy_action.json')
                action_audit.parent.mkdir(parents=True,exist_ok=True)
                action_audit.write_text(json.dumps({'action':action or 'native_element_click',
                    'element_id':getattr(target,'id',None),
                    'element_rect':getattr(target,'rect',None),
                    'scoped_to_current_response':True},indent=2),encoding='utf-8')
                if action:
                    self.driver.execute_script(action, {'elementId':target.id})
                else:
                    target.click()
                copied, fresh = self._poll_for_fresh_copy(sentinel, diagnostic_prefix)
                retry_clicked = False
                if (not fresh and copied == sentinel and
                        self.spec['selectors'].get('response_copy_parent_relative')):
                    copied, fresh, retry_clicked = self._retry_copy_on_clickable_parent(
                        prompt, before, last_text, diagnostic_prefix, sentinel)
                if not fresh:
                    raise RuntimeError('Copy action yielded no verifiably fresh clipboard text')
                from .response_agreement import agrees_with_visible_text
                agreement = agrees_with_visible_text(last_text, copied)
                copy_audit = Path(str(diagnostic_prefix) + '.clipboard_observation.json')
                copy_audit.parent.mkdir(parents=True,exist_ok=True)
                copy_audit.write_text(json.dumps({'visible_native_text':last_text,
                    'copied_text':copied,'fresh_sentinel_replaced':True,
                    'copy_action_retried':retry_clicked,
                    'excluded_native_ui_labels':self._excluded_native_ui_labels,
                    'all_visible_content_lines_agree':agreement,
                    'agreement_method':'all visible content lines; explicit list-format normalization'},
                    ensure_ascii=False,indent=2),encoding='utf-8')
                if not agreement:
                    raise RuntimeError('Clipboard and visible response text disagree; manual capture check needed')
                captured = copied
            finally:
                try:
                    self.driver.set_clipboard_text(baseline)
                    self._dismiss_clipboard_overlay(expect_overlay=bool(baseline))
                except Exception:
                    warnings.warn('Could not restore the emulator clipboard after capture', RuntimeWarning)
            time.sleep(float(self.cfg.get('clipboard_settle_seconds', 0)))
        elif mode not in ('text', 'accessibility_text_only', 'verified_native_text'):
            raise ValueError(f'Unsupported capture_mode: {mode}')
        if not captured:
            raise RuntimeError('Empty captured answer; cannot score')
        safe_case = re.sub(r'[^A-Za-z0-9_-]', '_', case_id)
        prefix = Path(screenshot_dir) / f'{self.app}_{safe_case}_{turn_idx}'
        self._write_evidence(prefix)
        prefix.with_suffix('.capture.json').write_text(json.dumps({
            'requested_mode':self.spec.get('capture_mode','text'),
            'actual_mode':actual_mode,'visible_native_text':last_text,
            'captured_characters':len(captured),
            'configured_copy_action':self.spec.get('copy_response_action','native_element_click'),
            'requested_prompt':prompt,
            'rendered_user_prompt':self._last_rendered_prompt,
            'prompt_match':self._last_prompt_match,
            'prompt_ui_variant_limitation':('Exact pre-send input is preserved; initial uppercase appeared in submitted UI; backend request bytes were not observed'
                if self._last_prompt_match == 'INITIAL_ASCII_UPPERCASE_UI_VARIANT' else None),
            'native_full_response_proven':actual_mode == 'native_full_response_viewport_proof',
            'excluded_native_ui_labels':self._excluded_native_ui_labels,
            'clipboard_read_recovery_count':self._clipboard_recoveries,
            'limitation':('All accessible response text reconstructed with current-prompt/footer and ordered viewport overlap proof; non-text media are not transcribed'
                if actual_mode == 'native_full_response_viewport_proof' else
                'Native text excludes non-text media and may omit inaccessible card text'
                if actual_mode == 'native_text_copy_unavailable' else None),
        },ensure_ascii=False,indent=2),encoding='utf-8')
        return captured

    def close(self):
        self.driver.quit()
