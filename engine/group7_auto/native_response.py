"""Explicit ownership and overlap proofs for virtualized accessible text."""
import re
import xml.etree.ElementTree as ET
from .android_snapshot import read_snapshot,is_code_language_badge


def _inspected_live_promotions(body,parents):
    excluded=set();observations=[]
    for frame in body.iter():
        parent=parents.get(frame)
        if not (frame.get('class')=='android.widget.FrameLayout'
                and frame.get('is-collection-item')=='true' and not frame.get('resource-id')
                and parent is not None and parent.get('resource-id','').endswith('assistant_robin_message_content')
                and any(c.get('class')=='androidx.compose.ui.platform.ComposeView' for c in frame)):
            continue
        nodes=list(frame.iter());window=frame.get('window-id');package=frame.get('package')
        if not window or package!='com.google.android.googlequicksearchbox':continue
        if any(n.get('window-id')!=window or n.get('package')!=package for n in nodes):continue
        titles=[n for n in nodes if n.get('class')=='android.widget.TextView'
                and n.get('heading')=='true' and n.get('text')=='Talk about this with Gemini Live']
        ctas=[n for n in nodes if n.get('class')=='android.widget.TextView'
              and n.get('text')=='Try a real-time voice conversation']
        if len(titles)!=1 or len(ctas)!=1:continue
        action=parents.get(ctas[0])
        if action is None or action.get('clickable')!='true' or not any(n.get('class')=='android.widget.Button' for n in action):continue
        texts=[n.get('text') for n in nodes if n.get('text')]
        if set(texts)!={'Talk about this with Gemini Live','Try a real-time voice conversation'}:continue
        excluded.update(nodes);observations.append({'kind':'INSPECTED_GEMINI_LIVE_PROMOTION',
            'bounds':frame.get('bounds'),'window_id':window,'excluded_labels':texts,
            'reason':'Separate collection-item Compose promotion with heading and actionable voice Button; no content-word filter'})
    return excluded,observations


def gemini_native_view(source, prompt, known_prompt_seen, allow_initial_capitalization=False):
    state=read_snapshot(source,'gemini',prompt,known_prompt_seen,allow_initial_capitalization)
    if state['generating']:
        raise RuntimeError('Native response is still generating')
    if state['clipboard_overlay']:
        raise RuntimeError('Native response is obstructed by clipboard overlay')
    root=ET.fromstring(source);nodes=list(root.iter());order={n:i for i,n in enumerate(nodes)}
    parents={c:n for n in nodes for c in n}
    users=[n for n in nodes if n.get('resource-id','').endswith('assistant_robin_user_message_text')]
    current=[n for n in users if state['matched_prompt_text'] is not None and n.get('text')==state['matched_prompt_text']]
    user=current[-1] if current else None
    if user is not None and users[-1] is not user:
        raise RuntimeError('Native current-turn ownership lost: later user message differs')
    if user is None and (not known_prompt_seen or users):
        raise RuntimeError('Native current-turn ownership cannot be confirmed')
    bodies=[n for n in nodes if n.get('resource-id','').endswith('assistant_robin_content_message_container')
            and (user is None or order[n]>order[user])]
    if not bodies:
        raise RuntimeError('Native current response body unavailable')
    body=bodies[-1]
    excluded,excluded_metadata=_inspected_live_promotions(body,parents)
    parts=[];media=[]
    for n in body.iter():
        if n in excluded:continue
        text=n.get('text','')
        if is_code_language_badge(n,parents):continue
        if text and (n.get('class')=='android.widget.TextView' or
                n.get('resource-id','').endswith('assistant_robin_code_impl') and
                not any(c is not n and c.get('class')=='android.widget.TextView' and c.get('text') for c in n.iter())):
            parts.append(text)
        description=n.get('content-desc')
        if description and not text and n.get('class') in ('android.widget.ImageView','android.widget.FrameLayout'):
            media.append(description)
    if not parts:
        raise RuntimeError('Native current response has no accessible text')
    parent=parents.get(body);siblings=list(parent) if parent is not None else []
    index=siblings.index(body) if body in siblings else -1
    footer=siblings[index+1] if index>=0 and index+1<len(siblings) else None
    completed=footer is not None and any(n.get('resource-id','').endswith('assistant_robin_message_content_actions_options_button') for n in footer.iter())
    history=next((n for n in nodes if n.get('resource-id','').endswith('assistant_robin_chat_history_list')),None)
    body_bounds=list(map(int,re.findall(r'\d+',body.get('bounds',''))))
    history_bounds=list(map(int,re.findall(r'\d+',history.get('bounds','')))) if history is not None else []
    if len(body_bounds)!=4 or len(history_bounds)!=4 or body_bounds[0]-history_bounds[0]<16:
        raise RuntimeError('Inspected non-text conversation margin unavailable for native capture')
    return {'parts':parts,'body_bounds':body.get('bounds'),'user_bounds':user.get('bounds') if user is not None else None,
            'excluded_ui_metadata':excluded_metadata,
            'start_prompt_confirmed':user is not None,'matched_prompt_text':state['matched_prompt_text'],
            'footer_completed':completed,'media_descriptions':media,
            'scroll_margin_x':(history_bounds[0]+body_bounds[0])//2,
            'fixed_input_top':state.get('fixed_input_top')}


def prepend_overlapping(earlier,later):
    """Join ordered viewports only when their shared content proves continuity."""
    for length in range(min(len(earlier),len(later)),0,-1):
        if earlier[-length:]!=later[:length]:
            continue
        overlap=earlier[-length:]
        if earlier!=later and not (any(len(t.strip())>=24 for t in overlap) or sum(len(t.strip()) for t in overlap)>=40):
            raise RuntimeError('Native viewport overlap is ambiguous: only short repeated items')
        return earlier[:-length]+later,length
    raise RuntimeError('Native response viewports have no verifiable overlap; cannot infer missing text')
