"""Read generation, ownership and overlays from one immutable Android XML."""
import xml.etree.ElementTree as ET
import re


def appium_settings_anr(source):
    """Recognize only the Android dialog for the Appium clipboard helper."""
    nodes = [node for node in ET.fromstring(source).iter()
             if node.get('package') == 'android' and node.get('displayed') != 'false']
    modal_windows = {node.get('window-id') for node in nodes
                     if node.get('resource-id') == 'android:id/alertTitle'
                     and node.get('text') == "Appium Settings isn't responding"}
    return any(node.get('resource-id') == 'android:id/aerr_close'
               and node.get('window-id') in modal_windows - {None} for node in nodes)


def is_code_language_badge(node,parents):
    """Only the inspected code header's sibling label is UI metadata."""
    if node.get('resource-id','').endswith('/assistant_robin_code_info'):
        return True
    parent=parents.get(node)
    return (node.get('class')=='android.widget.TextView' and not node.get('content-desc') and
            parent is not None and any(c.get('content-desc')=='Code block' for c in parent))


def is_reply_control_label(node,parents):
    """An inspected Compose button wrapper's label is not paragraph text."""
    parent=parents.get(node)
    return (node.get('class')=='android.widget.TextView' and not node.get('content-desc') and
            parent is not None and parent.get('clickable')=='true' and
            any(c.get('class')=='android.widget.Button' for c in parent))


def clipboard_overlay_state(source):
    """Observe the clipboard window and its close control in the same tree."""
    nodes = list(ET.fromstring(source).iter())
    visible = [n for n in nodes if n.get('package') == 'com.android.systemui' and
               n.get('displayed', 'true') != 'false']
    present = any(n.get('resource-id', '').endswith('/clipboard_ui') for n in visible)
    dismiss = any(n.get('resource-id', '').endswith('/dismiss_button') for n in visible)
    return {'present':present, 'dismiss_available':bool(present and dismiss)}


class ResponseBudget:
    """Bound generation separately from scrolling, with a capture stall guard."""
    def __init__(self, start, generation_seconds, capture_seconds, stall_seconds):
        self.generation_deadline = start + generation_seconds
        self.capture_seconds = capture_seconds
        self.stall_seconds = stall_seconds
        self.capture_start = None
        self.progress_at = start
        self.previous = None

    def observe(self, now, generating, viewport):
        if self.capture_start is None:
            if now > self.generation_deadline:
                raise TimeoutError('Application generation deadline exceeded')
            if not generating and viewport:
                self.capture_start = self.progress_at = now
                self.previous = viewport
        else:
            if now - self.capture_start > self.capture_seconds:
                raise TimeoutError('Completed-response capture deadline exceeded')
            if viewport != self.previous:
                self.progress_at, self.previous = now, viewport
            elif now - self.progress_at > self.stall_seconds:
                raise TimeoutError('Completed-response capture made no viewport progress')


def read_snapshot(source, app, prompt, prompt_seen=False, allow_initial_capitalization=False):
    root = ET.fromstring(source)
    nodes = list(root.iter())
    order = {n: i for i, n in enumerate(nodes)}
    parents = {c: n for n in nodes for c in n}
    fixed_input_tops = []
    for n in nodes:
        if (n.get('resource-id', '').endswith('assistant_robin_chat_input_half_sheet') and
                n.get('displayed', 'true') == 'true'):
            bounds = list(map(int, re.findall(r'\d+', n.get('bounds', ''))))
            if len(bounds) == 4 and bounds[3] > bounds[1]:
                fixed_input_tops.append(bounds[1])
    overlay = any(n.get('package') == 'com.android.systemui' and
                  ('clipboard' in n.get('resource-id', '') or
                   'dismiss_button' in n.get('resource-id', '')) for n in nodes)
    generating = any(n.get('content-desc') ==
                     ('Stop' if app == 'chatgpt' else 'Stop generating response') for n in nodes)
    accepted_prompts = {prompt}
    if allow_initial_capitalization and prompt and 'a' <= prompt[0] <= 'z':
        accepted_prompts.add(prompt[0].upper() + prompt[1:])
    users = [n for n in nodes if n.get('text') in accepted_prompts and
             (n.get('resource-id', '').endswith('assistant_robin_user_message_text')
              if app == 'gemini' else n.get('class') == 'android.widget.TextView' and
              not n.get('content-desc'))]
    user = users[-1] if users else None
    answers = []
    for node in nodes:
        if app == 'chatgpt':
            if node.get('content-desc') != 'Copy':
                continue
            bubble = node
            for _ in range(6):
                bubble = parents.get(bubble)
            if bubble is None:
                continue
            copy = node
            complete = True
            parts = [n.get('text', '') for n in bubble.iter()
                     if n.get('class') == 'android.widget.TextView' and
                     n.get('text') and n.get('text') != 'Memory updated' and
                     not is_code_language_badge(n,parents) and not is_reply_control_label(n,parents)]
            ignored=[n.get('text') for n in bubble.iter() if n.get('text') and
                     (is_code_language_badge(n,parents) or is_reply_control_label(n,parents))]
        else:
            if not node.get('resource-id', '').endswith('assistant_robin_content_message_container'):
                continue
            bubble = node
            parts = [n.get('text', '') for n in bubble.iter()
                     if (n.get('class') == 'android.widget.TextView' or
                         n.get('resource-id', '').endswith(('assistant_robin_text', 'assistant_robin_code_impl')))
                     and n.get('text') and not is_code_language_badge(n,parents)]
            ignored=[n.get('text') for n in bubble.iter() if n.get('text') and is_code_language_badge(n,parents)]
            parent = parents.get(bubble)
            siblings = list(parent) if parent is not None else []
            pos = siblings.index(bubble) if bubble in siblings else -1
            footer = siblings[pos + 1] if pos >= 0 and pos + 1 < len(siblings) else None
            actions = list(footer.iter()) if footer is not None else []
            complete = any(n.get('resource-id', '').endswith('assistant_robin_message_content_actions_options_button')
                           for n in actions)
            copy = next((n for n in actions if n.get('content-desc') == 'Copy'), None)
        if user is not None and order[bubble] <= order[user]:
            continue
        if parts:
            answers.append({'text': '\n'.join(parts), 'copy_present': copy is not None,
                            'copy_bounds': copy.get('bounds') if copy is not None else None,
                            'body_bounds': bubble.get('bounds'), 'footer_completed': complete,
                            'excluded_ui_metadata':ignored})
    current = answers[-1] if answers else None
    if app == 'chatgpt' and current is None and (user is not None or prompt_seen):
        # A long current answer can render before its footer is in the viewport.
        # Observe body text for safe scrolling; never declare it complete yet.
        parts = [n for n in nodes if (user is None or order[n] > order[user]) and
                 n.get('class') == 'android.widget.TextView' and n.get('text') and
                 n.get('text') == n.get('content-desc')]
        if parts:
            current = {'text': '\n'.join(n.get('text') for n in parts),
                       'copy_present': False, 'copy_bounds': None,
                       'body_bounds': parts[-1].get('bounds'), 'footer_completed': False}
    return {'generating': generating, 'clipboard_overlay': overlay,
            'fixed_input_top': min(fixed_input_tops) if fixed_input_tops else None,
            'prompt_present': user is not None,
            'matched_prompt_text': user.get('text') if user is not None else None,
            'prompt_match': ('EXACT' if user.get('text') == prompt else
                             'INITIAL_ASCII_UPPERCASE_UI_VARIANT') if user is not None else None,
            'reply': current,
            'reply_completed': bool(user is not None and current and not generating and
                                    not overlay and current['footer_completed'])}
