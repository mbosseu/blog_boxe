"""Small RSS/Atom reader for the editorial bot, with no third-party dependency."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

VU_FEEDS = [
    ('BoxeNet', 'https://www.boxenet.fr/feed/'),
    ('Boxemag', 'https://www.boxemag.com/boxe/feed/'),
    ('La Sueur', 'https://lasueur.com/category/boxe/feed/'),
    ('RMC Sport', 'https://rmcsport.bfmtv.com/rss/boxe/'),
]


def parse_pubdate(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        value = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        try:
            value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except (TypeError, ValueError, AttributeError):
            return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def skip_item(title):
    return bool(re.search(r"\bmma\b|\bufc\b|kick.?boxing|muay.?tha[iï]|bare.?knuckle|d[ée]c[eè]s|n[’']est plus|nécrolog|carnet noir|pronostic|pari sportif", title, re.I))


def parse_feed(xml):
    if re.search(br'<!DOCTYPE|<!ENTITY', xml, re.I):
        raise ValueError('Flux XML avec déclaration externe refusé.')
    root = ET.fromstring(xml)
    if root.tag.rsplit('}', 1)[-1] not in {'rss', 'feed'}:
        raise ValueError('La réponse reçue n’est pas un flux RSS ou Atom.')
    items = []
    for element in root.iter():
        if element.tag.rsplit('}', 1)[-1] not in {'item', 'entry'}:
            continue
        fields = {c.tag.rsplit('}', 1)[-1]: c for c in element}
        def text(name):
            child = fields.get(name)
            return unescape(''.join(child.itertext())).strip() if child is not None else ''
        link = text('link')
        if not link:
            link = next((c.attrib['href'] for c in element if c.tag.rsplit('}', 1)[-1] == 'link' and c.attrib.get('rel', 'alternate') == 'alternate' and 'href' in c.attrib), '')
        if text('title') and link.startswith('https://'):
            items.append({'title': text('title'), 'url': link.split('#')[0], 'pubDate': text('pubDate') or text('published') or text('updated')})
    return items[:100]


def load_rss(url):
    request = Request(url, headers={'User-Agent': 'ActuBoxeBot/2.0 (+https://actu-boxe.com; contact@actu-boxe.com)', 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urlopen(request, timeout=20) as response:
        content = response.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError('Flux trop volumineux.')
    return parse_feed(content)
