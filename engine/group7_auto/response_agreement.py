"""Check capture provenance; never score or rewrite the saved response."""
import re


def _normalize(text):
    text = re.sub(r'```[A-Za-z0-9_-]*', '', text)
    text = re.sub(r'\\([\\`*{}\[\]()#+.!_>~-])', r'\1', text)
    text = text.replace('\u200b', '').replace('\u2060', '').replace('\ufffc', '')
    text = re.sub(r'(\*\*|__)(.+?)\1', r'\2', text)
    text = re.sub(r'(?<!\w)\*([^*\n]+)\*(?!\w)', r'\1', text)
    text = re.sub(r'(?m)^\s*#{1,6}\s+', '', text)
    return re.sub(r'\s+', ' ', text.replace('`', '')).strip()


def agrees_with_visible_text(visible, copied):
    """Require every visible content line, not an arbitrary first-line keyword.

    Compose lists expose their counters as separate text nodes. Copy exports
    the same items as Markdown bullets. Those standalone counters and the final
    Sources control do not identify response content. All other lines must
    occur in the fresh, current-answer copy with token boundaries. Underscores
    inside code identifiers are retained. The caller saves both originals.
    """
    lines = [line.strip() for line in visible.splitlines() if line.strip()]
    if lines and lines[-1] == 'Sources':
        lines.pop()
    content = []
    for line in lines:
        if re.fullmatch(r'\d{1,3}[.)]|[•●▪]', line):
            continue
        line = re.sub(r'^\d{1,3}[.)]\s+', '', line)
        normalized = _normalize(line)
        if normalized:
            inline_link_is_rendered = '\u2060' in line and '\ufffc' in line and not re.search(r'https?://', line)
            content.append((normalized, inline_link_is_rendered))
    full = _normalize(copied)
    labels_only = _normalize(re.sub(r'(?<!!)\[([^\[\]\n]+)\]\(https?://[^\s)]+\)', r'\1', copied))
    return bool(content) and all(
        re.search(r'(?<!\w)' + re.escape(line) + r'(?!\w)', full) or
        (inline_link_is_rendered and re.search(r'(?<!\w)' + re.escape(line) + r'(?!\w)', labels_only))
        for line, inline_link_is_rendered in content
    )
