"""
Veille automatique Actu Boxe.

- FFBoxe : filets sourcés (titre + lien + date + photo fédérale si l’URL est sur ffboxe.com).
- Autres médias : titres + liens uniquement (aucun texte, aucune image).

Ne recopie pas les articles de L’Équipe, Boxemag, BoxeNet, La Sueur ou RMC Sport.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from content import ARTICLES

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WIRE_IMG = ROOT / "actu-boxe" / "assets" / "img" / "wire"
UA = "ActuBoxeBot/1.0 (+https://actu-boxe.com; contact@actu-boxe.com)"
HEADERS = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.8"}
TIMEOUT = 20

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

SKIP_RE = re.compile(
    r"d[ée]c[eè]s|n[’']est plus|nécrolog|carnet noir|pass sport|pass colo|colonies|"
    r"appel à candidature|agent sportif|certificat|règlement médical|"
    r"gant blanc|agoaps|\bufc\b|\bmma\b|dana white|kickboxing|kick-boxing|"
    r"bareknuckle|mains nues",
    re.I,
)

VU_FEEDS = [
    ("BoxeNet", "https://www.boxenet.fr/feed/"),
    ("Boxemag", "https://www.boxemag.com/boxe/feed/"),
    ("La Sueur", "https://lasueur.com/category/boxe/feed/"),
    ("RMC Sport", "https://rmcsport.bfmtv.com/rss/boxe/"),
]


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1]


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return unescape(el.text).strip()


def slugify(title: str) -> str:
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return (s or "communique")[:72]


def date_fr(dt: datetime) -> str:
    return f"{dt.day} {MONTHS_FR[dt.month - 1]} {dt.year}"


def parse_pubdate(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError, OverflowError):
        return None


def fetch(url: str) -> requests.Response:
    return requests.get(url, headers=HEADERS, timeout=TIMEOUT)


def parse_rss(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    items = []
    for item in root.iter():
        if _tag(item) != "item":
            continue
        fields = {_tag(c): c for c in list(item)}
        title = _text(fields.get("title"))
        link = _text(fields.get("link"))
        pub = _text(fields.get("pubDate"))
        cats = [_text(c) for c in list(item) if _tag(c) == "category"]
        if title and link:
            items.append({"title": title, "url": link.split("#")[0], "pubDate": pub, "categories": cats})
    return items


def editorial_urls() -> set[str]:
    urls = set()
    for art in ARTICLES:
        for src in art.get("sources") or []:
            if isinstance(src, (list, tuple)) and len(src) == 2 and str(src[1]).startswith("http"):
                urls.add(src[1].rstrip("/") + "/")
    return urls


def skip_item(title: str, categories: list[str] | None = None) -> bool:
    blob = title + " " + " ".join(categories or [])
    if SKIP_RE.search(blob):
        return True
    if any("nécrolog" in (c or "").lower() for c in (categories or [])):
        return True
    return False


def og_image_ffboxe(article_url: str) -> str | None:
    host = urlparse(article_url).netloc.lower()
    if host not in {"www.ffboxe.com", "ffboxe.com"}:
        return None
    try:
        html = fetch(article_url).text
    except requests.RequestException:
        return None
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if not tag:
        return None
    raw = (tag.get("content") or "").strip()
    if not raw:
        return None
    img_url = urljoin(article_url, raw)
    parsed = urlparse(img_url)
    if parsed.netloc.lower() not in {"www.ffboxe.com", "ffboxe.com"}:
        return None
    if not re.search(r"\.(jpe?g|png|webp)(\?|$)", parsed.path, re.I):
        return None
    return img_url


def download_ffboxe_image(img_url: str, slug: str) -> str | None:
    WIRE_IMG.mkdir(parents=True, exist_ok=True)
    ext = Path(urlparse(img_url).path).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    dest = WIRE_IMG / f"{slug}{ext}"
    rel = f"/assets/img/wire/{dest.name}"
    if dest.exists() and dest.stat().st_size > 800:
        return rel
    try:
        r = fetch(img_url)
        r.raise_for_status()
    except requests.RequestException:
        return None
    ctype = (r.headers.get("content-type") or "").lower()
    if "image" not in ctype and ext == ".jpg":
        return None
    if len(r.content) < 800 or len(r.content) > 2_500_000:
        return None
    dest.write_bytes(r.content)
    return rel


def ingest_ffboxe(known: set[str]) -> list[dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    previous = []
    prev_path = DATA / "ffboxe_fil.json"
    if prev_path.exists():
        previous = json.loads(prev_path.read_text(encoding="utf-8")).get("items") or []
    by_url = {i["url"].rstrip("/") + "/": i for i in previous}

    rss = parse_rss(fetch("https://www.ffboxe.com/feed/").content)
    for entry in rss:
        url = entry["url"].rstrip("/") + "/"
        if skip_item(entry["title"], entry.get("categories")):
            continue
        if url in known:
            continue
        dt = parse_pubdate(entry.get("pubDate") or "")
        if not dt:
            continue
        if url in by_url:
            continue
        slug = "ffboxe-" + slugify(entry["title"])
        if any(i.get("slug") == slug for i in by_url.values()):
            slug = f"{slug}-{dt.strftime('%Y%m%d')}"
        image = None
        img_url = og_image_ffboxe(entry["url"])
        time.sleep(0.35)
        if img_url:
            image = download_ffboxe_image(img_url, slug)
            time.sleep(0.2)
        by_url[url] = {
            "slug": slug,
            "title": entry["title"],
            "url": entry["url"].split("#")[0],
            "date_iso": dt.date().isoformat(),
            "date": date_fr(dt),
            "image": image,
            "image_alt": "Visuel publié par la FFBoxe",
            "categories": entry.get("categories") or [],
        }

    items = [
        i for i in by_url.values()
        if not skip_item(i["title"], i.get("categories"))
    ]
    items = sorted(items, key=lambda x: x["date_iso"], reverse=True)[:12]
    payload = {"updated": datetime.now(timezone.utc).isoformat(), "items": items}
    prev_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return items


def ingest_vu_ailleurs() -> list[dict]:
    items: list[dict] = []
    seen = set()
    for source, feed_url in VU_FEEDS:
        try:
            entries = parse_rss(fetch(feed_url).content)
        except requests.RequestException:
            continue
        for entry in entries:
            if skip_item(entry["title"]):
                continue
            url = entry["url"].rstrip("/") + "/"
            if url in seen:
                continue
            dt = parse_pubdate(entry.get("pubDate") or "")
            seen.add(url)
            items.append({
                "source": source,
                "title": entry["title"],
                "url": entry["url"].split("#")[0],
                "date_iso": dt.date().isoformat() if dt else "",
                "date": date_fr(dt) if dt else "",
            })
        time.sleep(0.25)
    items = sorted(items, key=lambda x: x.get("date_iso") or "", reverse=True)[:40]
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "vu_ailleurs.json").write_text(
        json.dumps({"updated": datetime.now(timezone.utc).isoformat(), "items": items}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return items


def main() -> None:
    known = editorial_urls()
    wires = ingest_ffboxe(known)
    links = ingest_vu_ailleurs()
    print(f"ffboxe wires: {len(wires)}")
    print(f"vu ailleurs: {len(links)}")


if __name__ == "__main__":
    main()
