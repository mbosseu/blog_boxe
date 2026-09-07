"""Lecture des JSON produits par ingest_news.py."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def _load(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def vu_ailleurs_items() -> list[dict]:
    items = _load("vu_ailleurs.json").get("items") or []
    return sorted(items, key=lambda x: x.get("date_iso") or "", reverse=True)


def wire_articles() -> list[dict]:
    out = []
    for item in _load("ffboxe_fil.json").get("items") or []:
        title = item["title"]
        url = item["url"]
        date = item["date"]
        excerpt = (
            f"Communiqué FFBoxe du {date}. Actu Boxe n’en recopie pas le texte : "
            f"lire la source officielle."
        )
        tags = ["actualites"]
        low = title.lower()
        if any(w in low for w in ("résultat", "resultat", "s’incline", "s'incline", "vainqueur", "champion")):
            tags.append("resultats")
        if "gala" in low:
            tags.append("galas")
        src_title = escape(title)
        src_url = escape(url, quote=True)
        body = f"""
<p>La Fédération française de boxe a publié un communiqué intitulé «&nbsp;{src_title}&nbsp;», le {escape(date)}.</p>
<p>Actu Boxe ne reprend pas le corps de l’article fédéral. Les faits (noms, dates, résultats) restent ceux de la source.</p>
<p><a href="{src_url}" target="_blank" rel="noopener">Lire le communiqué sur ffboxe.com</a></p>
<p class="wire-note">Fil automatique à partir du flux officiel FFBoxe. Photo : visuel du communiqué, crédit FFBoxe, lorsqu’un fichier hébergé par la fédération est disponible.</p>
"""
        art = {
            "slug": item["slug"],
            "title": title,
            "excerpt": excerpt,
            "date": date,
            "date_iso": item["date_iso"],
            "category": "Actualités",
            "category_href": "/actualites/",
            "active": "news",
            "tags": tags,
            "image_alt": item.get("image_alt") or "Visuel publié par la FFBoxe",
            "info": [
                ("Source", "FFBoxe"),
                ("Type", "Fil automatique"),
            ],
            "sources": [("Communiqué FFBoxe", url)],
            "body": body,
            "wire": True,
            "canonical_source": url,
        }
        if item.get("image"):
            art["image"] = item["image"]
        out.append(art)
    return out
