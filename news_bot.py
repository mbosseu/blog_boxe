"""Editorial publication gate. Research/writing is performed by the scheduled agent.

No model credentials are required here. RSS is discovery only, never evidence.
Source URLs and review records stay outside the public output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PARIS = ZoneInfo('Europe/Paris')
MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
CHECKS = ('facts_checked', 'independent_sources', 'contradictions_resolved', 'original_wording', 'image_checked', 'no_unverified_quotes')
TAGS = {'actualites', 'resultats', 'combats-a-venir', 'galas', 'clubs', 'boxeurs', 'analyses'}


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def atomic_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Date ISO requise.')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def words(text: str) -> list[str]:
    return re.findall(r"[\w]+(?:[’'-][\w]+)*", text.lower())


def source_domain(url: str) -> str:
    try:
        return (urlsplit(url).hostname or '').lower().removeprefix('www.')
    except ValueError:
        return ''


def plain(value, label: str, errors: list[str], minimum=1, maximum=2000) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        errors.append(f'{label}: texte requis ({minimum}–{maximum} caractères).')
        return ''
    if re.search(r'<[^>]*>|https?://|www\.|\]\s*\(|\b(?:href|src)\s*=|[\x00-\x08]', value, re.I):
        errors.append(f'{label}: HTML et URL interdits dans le texte public.')
    return value.strip()


def validate_draft(draft: dict, published: list[dict], existing: list[dict], now: datetime) -> list[str]:
    errors: list[str] = []
    if not isinstance(draft, dict):
        return ['Dossier JSON invalide : objet requis.']
    # Reject malformed structures before iterating or constructing sets.
    for key in ('sources', 'claims', 'sections'):
        if not isinstance(draft.get(key), list) or any(not isinstance(x, dict) for x in draft[key]):
            return [f'{key}: liste d’objets requise.']
    for key in ('tags', 'lead_claim_ids'):
        if not isinstance(draft.get(key), list) or any(not isinstance(x, str) for x in draft[key]):
            return [f'{key}: liste de textes requise.']
    for source in draft['sources']:
        if any(not isinstance(source.get(k), str) for k in ('id', 'url', 'publisher_group', 'published_at', 'retrieved_at')):
            return ['Source invalide : identifiant, URL, groupe et dates doivent être des textes.']
    for claim in draft['claims']:
        if not isinstance(claim.get('source_ids'), list) or any(not isinstance(x, str) for x in claim['source_ids']):
            return ['source_ids: liste de textes requise.']
    for section in draft['sections']:
        if not isinstance(section.get('paragraphs'), list):
            return ['paragraphs: liste requise.']
        for paragraph in section['paragraphs']:
            if not isinstance(paragraph, dict) or not isinstance(paragraph.get('claim_ids'), list) or any(not isinstance(x, str) for x in paragraph['claim_ids']):
                return ['Paragraphe invalide : objet avec claim_ids requis.']
    if not isinstance(draft.get('central_claim_id'), str) or not isinstance(draft.get('image_brief'), dict):
        return ['Fait central ou illustration manquant.']
    image_refs = draft['image_brief'].get('claim_ids')
    if not isinstance(image_refs, list) or any(not isinstance(x, str) for x in image_refs):
        return ['image.claim_ids: liste de textes requise.']
    today = now.astimezone(PARIS).date()
    slug = draft.get('slug', '')
    if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 100:
        errors.append('Slug invalide.')
    topic = plain(draft.get('topic_key'), 'topic_key', errors, 8, 150)
    title = plain(draft.get('title'), 'title', errors, 25, 140)
    excerpt = plain(draft.get('excerpt'), 'excerpt', errors, 70, 280)
    lead = plain(draft.get('lead'), 'lead', errors, 100, 1600)
    if not isinstance(draft.get('tags'), list) or not draft['tags'] or not set(draft['tags']) <= TAGS:
        errors.append('Rubriques invalides.')
    sources = draft.get('sources', [])
    if not isinstance(sources, list):
        sources = []
    source_map = {}
    domains, groups, recent = set(), set(), False
    for source in sources:
        if not isinstance(source, dict):
            errors.append('Source mal formée.')
            continue
        sid = source.get('id')
        if not isinstance(sid, str) or not sid or sid in source_map:
            errors.append('Chaque source doit avoir un identifiant unique.')
            continue
        source_map[sid] = source
        try:
            parsed = urlsplit(source.get('url', ''))
        except ValueError:
            errors.append(f'{sid}: URL invalide.')
            continue
        host = (parsed.hostname or '').lower().removeprefix('www.')
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password:
            errors.append(f'{sid}: URL HTTPS de source invalide.')
        domains.add(host)
        group = source.get('publisher_group', '')
        groups.add(group.strip().casefold())
        plain(source.get('publisher'), f'{sid}.publisher', errors, 2, 100)
        plain(group, f'{sid}.publisher_group', errors, 2, 100)
        plain(source.get('title'), f'{sid}.title', errors, 8, 250)
        plain(source.get('evidence_summary'), f'{sid}.evidence_summary', errors, 40, 1200)
        try:
            date = parse_time(source['published_at'])
            retrieved = parse_time(source['retrieved_at'])
            if date > now or retrieved > now + timedelta(minutes=5):
                errors.append(f'{sid}: date de source future.')
            if retrieved < now - timedelta(hours=24):
                errors.append(f'{sid}: source non relue dans les dernières 24 h.')
            if now - timedelta(days=7) <= date <= now:
                recent = True
        except (KeyError, TypeError, ValueError):
            errors.append(f'{sid}: dates de publication et consultation requises.')
    if len(domains) < 2 or len(groups) < 2 or len(sources) < 2:
        errors.append('Au moins deux domaines et deux éditeurs indépendants sont requis.')
    if not any(s.get('primary') is True for s in source_map.values()):
        errors.append('Une source primaire au minimum est requise.')
    if not recent:
        errors.append('Aucune information publiée au cours des sept derniers jours.')
    claims = draft.get('claims', [])
    if not isinstance(claims, list):
        claims = []
    claim_map = {}
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get('id'), str) or claim['id'] in claim_map:
            errors.append('Identifiant de fait absent ou dupliqué.')
            continue
        claim_map[claim['id']] = claim
        plain(claim.get('text'), 'claim.text', errors, 15, 700)
        refs = claim.get('source_ids', [])
        if not isinstance(refs, list) or not refs or any(ref not in source_map for ref in refs):
            errors.append(f"{claim['id']}: références factuelles invalides.")
    central = claim_map.get(draft.get('central_claim_id'))
    refs = [source_map[r] for r in (central or {}).get('source_ids', []) if r in source_map]
    central_domains = {source_domain(s['url']) for s in refs} - {''}
    if len(central_domains) < 2 or len({s.get('publisher_group', '').casefold() for s in refs}) < 2 or not any(s.get('primary') is True for s in refs):
        errors.append('Le fait central doit être confirmé par deux éditeurs dont une source primaire.')
    try:
        if not any(now - timedelta(days=7) <= parse_time(s['published_at']) <= now for s in refs):
            errors.append('Le fait central ne possède aucune source publiée dans les sept derniers jours.')
    except ValueError:
        errors.append('Date invalide pour une source du fait central.')
    if not draft.get('lead_claim_ids') or any(c not in claim_map for c in draft.get('lead_claim_ids', [])):
        errors.append('Le chapeau doit être rattaché à des faits vérifiés.')
    sections = draft.get('sections', [])
    if not isinstance(sections, list) or not 3 <= len(sections) <= 6:
        errors.append('Prévoir trois à six sections.')
        sections = []
    prose = [title, excerpt, lead]
    for section in sections:
        prose.append(plain(section.get('heading'), 'heading', errors, 8, 120))
        paragraphs = section.get('paragraphs', [])
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 4:
            errors.append('Une section contient un à quatre paragraphes.')
            continue
        for paragraph in paragraphs:
            prose.append(plain(paragraph.get('text'), 'paragraph', errors, 70, 1600))
            ids = paragraph.get('claim_ids', [])
            if not ids or any(c not in claim_map for c in ids):
                errors.append('Chaque paragraphe doit être rattaché aux faits du dossier.')
    count = len(words(' '.join(prose)))
    if not 350 <= count <= min(850, len(sources) * 200):
        errors.append(f'Longueur inadaptée : {count} mots (350 à min(850, 200 × sources)).')
    for old in published + existing:
        if slug == old.get('slug') or topic == old.get('topic_key'):
            errors.append('Sujet ou adresse déjà publié.')
        if title and SequenceMatcher(None, ' '.join(words(title)), ' '.join(words(old.get('title', '')))).ratio() > .82:
            errors.append('Titre trop proche d’un article existant.')
    for old in published:
        try:
            if parse_time(old['published_at']).astimezone(PARIS).date() == today:
                errors.append('Limite atteinte : un article par jour, heure de Paris.')
        except (KeyError, ValueError):
            errors.append('Historique de publication invalide : publication suspendue.')
    review = draft.get('review', {})
    if not isinstance(review, dict) or any(review.get(key) is not True for key in CHECKS):
        errors.append('Relecture factuelle, originalité et contrôle des images incomplets.')
    if isinstance(review, dict):
        plain(review.get('notes'), 'review.notes', errors, 60, 2000)
    brief = draft.get('image_brief', {})
    if not isinstance(brief, dict):
        brief = {}
    if brief.get('kind') not in {'fight', 'results', 'championship', 'club'}:
        errors.append('Type d’illustration invalide.')
    plain(brief.get('headline'), 'image.headline', errors, 5, 80)
    plain(brief.get('kicker'), 'image.kicker', errors, 3, 35)
    facts = brief.get('facts', [])
    if not isinstance(facts, list) or not 2 <= len(facts) <= 3:
        errors.append('Deux ou trois repères sont requis pour l’image.')
    else:
        for fact in facts:
            plain(fact, 'image.fact', errors, 3, 65)
    if not brief.get('claim_ids') or any(c not in claim_map for c in brief.get('claim_ids', [])):
        errors.append('Les repères de l’image doivent être reliés aux faits vérifiés.')
    return sorted(set(errors))


def make_public_article(draft: dict, now: datetime) -> dict:
    date = now.astimezone(PARIS)
    slug = draft['slug']
    body = '<p>' + escape(draft['lead']) + '</p>\n'
    for section in draft['sections']:
        body += '<h2>' + escape(section['heading']) + '</h2>\n'
        body += '\n'.join('<p>' + escape(p['text']) + '</p>' for p in section['paragraphs']) + '\n'
    body += '<p><small>Article produit avec assistance automatisée à partir de sources recoupées. Illustration originale Actu Boxe.</small></p>'
    return {
        'slug': slug, 'topic_key': draft['topic_key'], 'title': draft['title'], 'excerpt': draft['excerpt'],
        'date': f'{date.day} {MONTHS[date.month-1]} {date.year}', 'date_iso': date.date().isoformat(),
        'published_at': now.isoformat(), 'category': 'Actualités', 'category_href': '/actualites/',
        'active': 'news', 'tags': list(dict.fromkeys(['actualites'] + draft['tags'])), 'automated': True,
        'image': f'/assets/img/news/{slug}.svg', 'image_alt': 'Illustration Actu Boxe — ' + draft['image_brief']['headline'],
        'info': [('Publication', 'Actu Boxe · veille et rédaction assistées'), ('Illustration', 'Création originale Actu Boxe')],
        'sources': [s['publisher'] + ' — ' + s['title'] + ' (' + s['published_at'][:10] + ')' for s in draft['sources']],
        'body': body,
    }


def publish_draft(draft: dict, root: Path = ROOT, now: datetime | None = None) -> dict:
    from content import ARTICLES
    from news_images import render_news_image
    now = now or datetime.now(timezone.utc)
    data = root / 'data'
    data.mkdir(parents=True, exist_ok=True)
    lock = data / '.news-publish.lock'
    # Exclusive local lock; remote races are rejected by a non-forced Git push.
    try:
        guard = lock.open('x')
    except FileExistsError as exc:
        raise ValueError('Une publication est déjà en cours ; vérifier le verrou.') from exc
    guard.close()
    created = []
    try:
            registry = load_json(data / 'news_articles.json', {'items': []})
            published = registry['items']
            errors = validate_draft(draft, published, ARTICLES, now)
            if errors:
                raise ValueError('\n'.join(errors))
            slug = draft['slug']
            audit = data / 'news_audit' / f'{slug}.json'
            image = root / 'actu-boxe/assets/img/news' / f'{slug}.svg'
            if audit.exists() or image.exists() or (root / 'actu-boxe/articles' / slug / 'index.html').exists():
                raise ValueError('Publication existante : aucun écrasement automatique.')
            record = make_public_article(draft, now)
            image.parent.mkdir(parents=True, exist_ok=True)
            render_news_image(draft, image)
            created.append(image)
            record['audit_sha256'] = hashlib.sha256(json.dumps(draft, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            atomic_json(audit, {'published_at': now.isoformat(), 'draft': draft})
            created.append(audit)
            atomic_json(data / 'news_articles.json', {'items': published + [record]})
            return record
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    finally:
        lock.unlink()


def publish(draft: dict, root: Path = ROOT, now: datetime | None = None) -> dict:
    return publish_draft(draft, root, now)


def collect_candidates(root: Path = ROOT) -> dict:
    from news_discovery import VU_FEEDS, load_rss, parse_pubdate, skip_item
    now = datetime.now(timezone.utc)
    candidates, failures = [], []
    feeds = [('FFBoxe', 'https://www.ffboxe.com/feed/')] + VU_FEEDS
    for publisher, url in feeds:
        try:
            for item in load_rss(url):
                date = parse_pubdate(item.get('pubDate', ''))
                if not date or not now - timedelta(days=7) <= date <= now or skip_item(item['title']):
                    continue
                if re.search(r'g2c|échéancier|gants de couleur|appel à|comité directeur', item['title'], re.I):
                    continue
                candidates.append({'publisher': publisher, 'title': item['title'], 'url': item['url'], 'published_at': date.isoformat()})
        except Exception as exc:
            failures.append({'publisher': publisher, 'error': type(exc).__name__})
    if len(failures) == len(feeds):
        raise RuntimeError('Toutes les sources de découverte sont indisponibles ; aucun remplacement du dernier relevé.')
    unique = {c['url']: c for c in candidates}
    payload = {'items': sorted(unique.values(), key=lambda c: parse_time(c['published_at']), reverse=True)[:60], 'unavailable_feeds': failures}
    path = root / 'data/news_candidates.json'
    if payload != load_json(path, {}):
        atomic_json(path, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['collect', 'status', 'validate', 'publish'])
    parser.add_argument('draft', nargs='?', type=Path)
    args = parser.parse_args()
    if args.command == 'collect':
        result = collect_candidates()
        print(f"{len(result['items'])} sujets détectés ; {len(result['unavailable_feeds'])} flux indisponibles.")
    elif args.command == 'status':
        now = datetime.now(timezone.utc)
        items = load_json(ROOT/'data/news_articles.json', {'items': []})['items']
        used = sum(parse_time(a['published_at']).astimezone(PARIS).date() == now.astimezone(PARIS).date() for a in items)
        print(json.dumps({'date_paris': str(now.astimezone(PARIS).date()), 'remaining_today': max(0, 1-used), 'articles': len(items)}, ensure_ascii=False))
    else:
        if not args.draft:
            parser.error('Le dossier JSON est requis.')
        draft = load_json(args.draft, {})
        if args.command == 'validate':
            from content import ARTICLES
            errors = validate_draft(draft, load_json(ROOT/'data/news_articles.json', {'items': []})['items'], ARTICLES, datetime.now(timezone.utc))
            if errors:
                parser.exit(1, '\n'.join(errors)+'\n')
            print('Dossier conforme aux contrôles automatiques. La relecture des sources reste obligatoire.')
        else:
            print(json.dumps(publish(draft), ensure_ascii=False))


if __name__ == '__main__':
    main()
