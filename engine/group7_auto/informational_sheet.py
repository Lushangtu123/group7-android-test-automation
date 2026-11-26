"""Recognize the inspected, dismissible introduction; never select Continue."""
from xml.etree import ElementTree as ET

TITLE = 'Temporary chat'
BODY = ('This chat won’t appear in history. You can choose whether ChatGPT uses '
        'memory, files, plugins, and custom instructions to personalize replies.')

def known_informational_sheet(source):
    nodes = list(ET.fromstring(source).iter())
    for title in nodes:
        if not (title.get('package') == 'com.openai.chatgpt'
                and title.get('text') == TITLE and title.get('heading') == 'true'
                and title.get('displayed', 'true') != 'false' and title.get('window-id')):
            continue
        window = title.get('window-id')
        scoped = [n for n in nodes if n.get('package') == title.get('package')
                  and n.get('window-id') == window and n.get('displayed','true') != 'false']
        texts = {n.get('text') for n in scoped if n.get('text')}
        closes = [n for n in scoped if n.get('content-desc') == 'Close']
        if texts == {TITLE, BODY, 'Continue'} and len(closes) == 1:
            return {'name': 'temporary_chat_introduction', 'window_id': window,
                    'action_by': 'accessibility id', 'action_value': 'Close'}
    return None
