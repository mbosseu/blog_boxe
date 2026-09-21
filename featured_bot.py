"""Independent publication gate for articles promoted on the homepage.

This instance reuses the editorial safeguards from ``news_bot`` while keeping
its candidates, quota, registry, audit files, image directory and lock apart.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from content import ARTICLES
from news_bot import (
    PARIS,
    ROOT,
    atomic_json,
    load_json,
    make_public_article,
    parse_time,
    validate_draft,
)

REGISTRY_NAME = "featured_articles.json"
CANDIDATES_NAME = "featured_candidates.json"
AUDIT_DIR = "featured_audit"
LOCK_NAME = ".featured-publish.lock"
IMAGE_DIR = "featured"


def registry_items(root: Path = ROOT) -> list[dict]:
    return load_json(root / "data" / REGISTRY_NAME, {"items": []}).get("items", [])


def existing_articles(root: Path = ROOT) -> list[dict]:
    regular = load_json(root / "data" / "news_articles.json", {"items": []}).get("items", [])
    return ARTICLES + regular + registry_items(root)


def validate_featured_draft(draft: dict, root: Path, now: datetime) -> list[str]:
    # The daily quota is independent, but duplicate detection covers both bots
    # and all manually maintained articles.
    return validate_draft(draft, registry_items(root), existing_articles(root), now)


def make_featured_article(draft: dict, now: datetime) -> dict:
    record = make_public_article(draft, now)
    slug = draft["slug"]
    record.update({
        "featured": True,
        "bot_instance": "featured-editorial",
        "image": f"/assets/img/{IMAGE_DIR}/{slug}.svg",
        "image_alt": "Illustration Actu Boxe - " + draft["image_brief"]["headline"],
    })
    return record


def publish_draft(draft: dict, root: Path = ROOT, now: datetime | None = None) -> dict:
    from news_images import render_news_image

    now = now or datetime.now(timezone.utc)
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    lock = data / LOCK_NAME
    try:
        guard = lock.open("x")
    except FileExistsError as exc:
        raise ValueError("Une publication featured est déjà en cours ; vérifier le verrou.") from exc
    guard.close()

    created: list[Path] = []
    try:
        published = registry_items(root)
        errors = validate_draft(draft, published, existing_articles(root), now)
        if errors:
            raise ValueError("\n".join(errors))

        slug = draft["slug"]
        audit = data / AUDIT_DIR / f"{slug}.json"
        image = root / "actu-boxe" / "assets" / "img" / IMAGE_DIR / f"{slug}.svg"
        page = root / "actu-boxe" / "articles" / slug / "index.html"
        if audit.exists() or image.exists() or page.exists():
            raise ValueError("Publication existante : aucun écrasement automatique.")

        record = make_featured_article(draft, now)
        image.parent.mkdir(parents=True, exist_ok=True)
        render_news_image(draft, image)
        created.append(image)
        record["audit_sha256"] = hashlib.sha256(
            json.dumps(draft, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        atomic_json(audit, {"published_at": now.isoformat(), "instance": "featured", "draft": draft})
        created.append(audit)
        atomic_json(data / REGISTRY_NAME, {"items": published + [record]})
        return record
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    finally:
        lock.unlink(missing_ok=True)


def publish(draft: dict, root: Path = ROOT, now: datetime | None = None) -> dict:
    return publish_draft(draft, root, now)


def collect_candidates(root: Path = ROOT) -> dict:
    from news_discovery import VU_FEEDS, load_rss, parse_pubdate, skip_item

    now = datetime.now(timezone.utc)
    candidates: list[dict] = []
    failures: list[dict] = []
    feeds = [("FFBoxe", "https://www.ffboxe.com/feed/")] + VU_FEEDS
    for publisher, url in feeds:
        try:
            for item in load_rss(url):
                date = parse_pubdate(item.get("pubDate", ""))
                if not date or not now - timedelta(days=7) <= date <= now or skip_item(item["title"]):
                    continue
                if re.search(r"g2c|échéancier|gants de couleur|appel à|comité directeur", item["title"], re.I):
                    continue
                candidates.append({
                    "publisher": publisher,
                    "title": item["title"],
                    "url": item["url"],
                    "published_at": date.isoformat(),
                })
        except Exception as exc:
            failures.append({"publisher": publisher, "error": type(exc).__name__})
    if len(failures) == len(feeds):
        raise RuntimeError("Toutes les sources sont indisponibles ; le dernier relevé featured est conservé.")

    unique = {candidate["url"]: candidate for candidate in candidates}
    payload = {
        "instance": "featured",
        "items": sorted(unique.values(), key=lambda item: parse_time(item["published_at"]), reverse=True)[:60],
        "unavailable_feeds": failures,
    }
    path = root / "data" / CANDIDATES_NAME
    if payload != load_json(path, {}):
        atomic_json(path, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "status", "validate", "publish"])
    parser.add_argument("draft", nargs="?", type=Path)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)

    if args.command == "collect":
        result = collect_candidates()
        print(f"{len(result['items'])} sujets featured détectés ; {len(result['unavailable_feeds'])} flux indisponibles.")
        return
    if args.command == "status":
        items = registry_items()
        used = sum(
            parse_time(article["published_at"]).astimezone(PARIS).date() == now.astimezone(PARIS).date()
            for article in items
        )
        print(json.dumps({
            "instance": "featured",
            "date_paris": str(now.astimezone(PARIS).date()),
            "remaining_today": max(0, 1 - used),
            "articles": len(items),
        }, ensure_ascii=False))
        return
    if not args.draft:
        parser.error("Le dossier JSON est requis.")
    draft = load_json(args.draft, {})
    if args.command == "validate":
        errors = validate_featured_draft(draft, ROOT, now)
        if errors:
            parser.exit(1, "\n".join(errors) + "\n")
        print("Dossier featured conforme. La relecture des sources reste obligatoire.")
        return
    print(json.dumps(publish(draft), ensure_ascii=False))


if __name__ == "__main__":
    main()
