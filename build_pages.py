"""Génère les pages statiques Actu Boxe."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

from content import ARTICLES, by_tag, get

ROOT = Path(__file__).resolve().parent / "actu-boxe"
SITE = "https://actu-boxe.com"

NAV = [
    ("/", "Accueil", "home"),
    ("/actualites/", "Actualités", "news"),
    ("/resultats/", "Résultats", "results"),
    ("/combats-a-venir/", "Combats", "fights"),
    ("/champions/", "Champions", "champs"),
    ("/clubs/", "Clubs", "clubs"),
]

PAGES = [
    ("actualites", "Actualités", "France et international",
     "Toute l’actualité de la boxe anglaise : galas, annonces, enjeux et suivi des boxeurs."),
    ("resultats", "Résultats", "Après les galas",
     "Les comptes rendus et résultats des combats en France et à l’international."),
    ("combats-a-venir", "Combats à venir", "Calendrier",
     "Les affiches à venir, les enjeux sportifs et les rendez-vous à suivre."),
    ("galas", "Galas", "Événements",
     "Les soirées de boxe anglaise, en France et à l’étranger."),
    ("champions", "Champions actuels", "Titres en cours",
     "Les champions du monde, d’Europe et de France, par organisation et catégorie de poids."),
    ("boxeurs", "Boxeurs", "Portraits",
     "Parcours, palmarès et style des boxeurs français et internationaux."),
    ("coachs", "Coachs", "Acteurs de terrain",
     "Les entraîneurs qui forment les boxeurs et font vivre les salles."),
    ("clubs", "Clubs de boxe", "France",
     "Portraits de clubs : histoire, salle, coachs, disciplines et rôle local."),
    ("organisations", "Organisations", "Écosystème",
     "WBC, WBA, IBF, WBO, EBU, FFB : comprendre les fédérations et les ceintures."),
    ("analyses", "Analyses", "Décryptage",
     "Lectures de combats, performances et enjeux sportifs."),
    ("interviews", "Interviews", "Paroles d’acteurs",
     "Extraits publics et entretiens, uniquement quand une source existe. Pas de citations inventées."),
    ("mentions-legales", "Mentions légales", "Informations",
     "Éditeur, hébergeur, contact et réseaux d’Actu Boxe."),
    ("confidentialite", "Politique de confidentialité", "Données",
     "Comment Actu Boxe traite les données de navigation et de contact."),
]


CSS = """
<link rel="stylesheet" href="/assets/css/vendor/global.css">
<link rel="stylesheet" href="/assets/css/vendor/scroll.css">
<link rel="stylesheet" href="/assets/css/vendor/colors.css">
<link rel="stylesheet" href="/assets/css/vendor/hover.css">
<link rel="stylesheet" href="/assets/css/vendor/animations.css">
<link rel="stylesheet" href="/assets/css/vendor/variables.css">
<link rel="stylesheet" href="/assets/css/vendor/menu.css">
<link rel="stylesheet" href="/assets/css/vendor/elements.css">
<link rel="stylesheet" href="/assets/css/vendor/z-index.css">
<link rel="stylesheet" href="/assets/css/vendor/footer.css">
<link rel="stylesheet" href="/assets/css/vendor/footer-contact.css">
<link rel="stylesheet" href="/assets/css/vendor/footer-links.css">
<link rel="stylesheet" href="/assets/css/vendor/back-to-top.css">
<link rel="stylesheet" href="/assets/css/vendor/blog-home.css">
<link rel="stylesheet" href="/assets/css/vendor/hero.css">
<link rel="stylesheet" href="/assets/css/vendor/sections.css">
<link rel="stylesheet" href="/assets/css/vendor/item.css">
<link rel="stylesheet" href="/assets/css/vendor/adbox.css">
<link rel="stylesheet" href="/assets/css/actu-boxe.css">
"""

ICONS = {
    "home": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M13.45 2.533a2.25 2.25 0 0 0-2.9 0L3.8 8.228a2.25 2.25 0 0 0-.8 1.72v9.305c0 .966.784 1.75 1.75 1.75h3a1.75 1.75 0 0 0 1.75-1.75V15.25c0-.68.542-1.232 1.217-1.25h2.566a1.25 1.25 0 0 1 1.217 1.25v4.003c0 .966.784 1.75 1.75 1.75h3a1.75 1.75 0 0 0 1.75-1.75V9.947a2.25 2.25 0 0 0-.8-1.72z"/></svg>',
    "news": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor"><path d="M11.5 3h-7A1.5 1.5 0 0 0 3 4.5v7A1.5 1.5 0 0 0 4.5 13h7a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 11.5 3z"/></svg>',
    "results": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M4.5 6.75h15v1.5h-15zm0 4.5h15v1.5h-15zm0 4.5h10.5v1.5H4.5z"/></svg>',
    "fights": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M6.75 3A2.25 2.25 0 0 0 4.5 5.25V9a7.5 7.5 0 0 0 7.5 7.5h.75V21h1.5v-4.5h.75A7.5 7.5 0 0 0 22.5 9V5.25A2.25 2.25 0 0 0 20.25 3h-3.879a2.25 2.25 0 0 0-1.59.659L12 6.44 10.22 4.66A2.25 2.25 0 0 0 8.629 3H6.75z"/></svg>',
    "champs": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M5.166 2.25h13.668a.75.75 0 0 1 .647 1.126l-2.79 4.882A8.25 8.25 0 1 1 5.31 8.258L2.52 3.376A.75.75 0 0 1 3.166 2.25H5.166z"/></svg>',
    "clubs": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M11.47 3.84a.75.75 0 0 1 1.06 0l8.69 8.69a.75.75 0 1 0 1.06-1.06l-8.689-8.69a2.25 2.25 0 0 0-3.182 0l-8.69 8.69a.75.75 0 0 0 1.061 1.06z"/></svg>',
}


def header(active: str) -> str:
    items = []
    for href, label, key in NAV:
        cls = ' class="is-active"' if active == key else ""
        items.append(
            f'<li><a href="{href}"{cls}>{ICONS[key]}<span>{label}</span></a></li>'
        )
    return f"""
<a class="skip-link" href="#contenu">Aller au contenu</a>
<nav class="menu nosticky" aria-label="Navigation principale">
  <div class="logo">
    <a href="/" aria-label="Actu Boxe — accueil">
      <img src="/assets/img/logo.png" alt="Actu Boxe" width="220" height="92">
    </a>
    <div class="background hidden" aria-hidden="true"></div>
  </div>
  <input type="checkbox" id="nav-open" class="nav-open" hidden>
  <label for="nav-open" class="menu-toggle" aria-label="Ouvrir ou fermer le menu">
    <span></span><span></span><span></span>
  </label>
  <ul class="buttons">
    {''.join(items)}
  </ul>
</nav>
<div id="top" class="top_of_the_page"></div>
<a class="back_to_top" href="#top" aria-label="Retour en haut">↑</a>
"""


def footer() -> str:
    links = [
        ("/", "Accueil"),
        ("/actualites/", "Actualités"),
        ("/resultats/", "Résultats"),
        ("/combats-a-venir/", "Combats à venir"),
        ("/galas/", "Galas"),
        ("/champions/", "Champions"),
        ("/boxeurs/", "Boxeurs"),
        ("/coachs/", "Coachs"),
        ("/clubs/", "Clubs"),
        ("/organisations/", "Organisations"),
        ("/analyses/", "Analyses"),
        ("/interviews/", "Interviews"),
        ("/mentions-legales/", "Mentions légales"),
        ("/confidentialite/", "Confidentialité"),
    ]
    lis = "".join(f'<li class="hoverUnderline"><a href="{h}">{t}</a></li>' for h, t in links)
    return f"""
<nav id="footer">
  <main>
    <div class="logo">
      <img src="/assets/img/logo.png" alt="Actu Boxe">
    </div>
    <div class="links">
      <h4>Rubriques</h4>
      <ul>{lis}</ul>
    </div>
    <div class="contact">
      <h4>Nous contacter</h4>
      <div class="inner">
        <div class="mail">
          <header><p>Rédaction</p><span>actu-boxe.com</span></header>
          <a class="hoverUnderline" href="mailto:contact@actu-boxe.com">contact@actu-boxe.com</a>
        </div>
        <p class="footer-note">Aucun compte officiel Instagram, X ou Facebook à ce jour.</p>
      </div>
    </div>
  </main>
  <hr>
  <div class="copyright">
    <p><span>© 2026 Actu Boxe</span> — Tous droits réservés.</p>
  </div>
</nav>
<script src="/assets/js/sticky.js" defer></script>
<script src="/assets/js/back-to-top.js" defer></script>
"""


def ld_json(data: dict | list) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def page_shell(
    title: str,
    description: str,
    body: str,
    active: str,
    path: str = "/",
    image: str = "",
    *,
    og_type: str = "website",
    date_published: str = "",
    image_alt: str = "",
    noindex: bool = False,
    title_full: str | None = None,
    canonical: str | None = None,
    extra_ld: list | None = None,
) -> str:
    og_img = image or "/assets/img/logo.png"
    og_alt = escape(image_alt or "Actu Boxe")
    doc_title = title_full or f"{title} — Actu Boxe"
    desc = escape(description, quote=True)
    title_esc = escape(doc_title, quote=True)
    url = f"{SITE}{path}"
    canon = canonical or url
    robots = '<meta name="robots" content="noindex, follow">\n  ' if noindex else ""
    article_meta = ""
    if og_type == "article" and date_published:
        article_meta = f"""
  <meta property="article:published_time" content="{date_published}">
  <meta property="article:modified_time" content="{date_published}">
  <meta property="article:section" content="Boxe">"""
    graph = [
        {
            "@type": "NewsMediaOrganization",
            "@id": f"{SITE}/#org",
            "name": "Actu Boxe",
            "url": SITE,
            "logo": f"{SITE}/assets/img/logo.png",
            "email": "contact@actu-boxe.com",
            "inLanguage": "fr-FR",
        },
        {
            "@type": "WebSite",
            "@id": f"{SITE}/#website",
            "name": "Actu Boxe",
            "url": SITE,
            "publisher": {"@id": f"{SITE}/#org"},
            "inLanguage": "fr-FR",
        },
        {
            "@type": "WebPage",
            "@id": f"{canon}#webpage",
            "url": canon,
            "name": doc_title,
            "description": description,
            "isPartOf": {"@id": f"{SITE}/#website"},
            "inLanguage": "fr-FR",
        },
    ]
    if extra_ld:
        graph.extend(extra_ld)
    ld = ld_json({"@context": "https://schema.org", "@graph": graph})
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_esc}</title>
  <meta name="description" content="{desc}">
  {robots}<link rel="canonical" href="{canon}">
  <meta name="theme-color" content="#d31212">
  <meta property="og:locale" content="fr_FR">
  <meta property="og:site_name" content="Actu Boxe">
  <meta property="og:title" content="{title_esc}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{canon}">
  <meta property="og:image" content="{SITE}{og_img}">
  <meta property="og:image:alt" content="{og_alt}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title_esc}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{SITE}{og_img}">{article_meta}
  <link rel="icon" href="/assets/img/logo.png">
  <script type="application/ld+json">{ld}</script>
  {CSS}
</head>
<body>
{header(active)}
{body}
{footer()}
</body>
</html>
"""


def href_article(slug: str) -> str:
    return f"/articles/{slug}/"


def title_card_html(article: dict) -> str:
    cat = escape(article.get("category", "Actu"))
    title = escape(article.get("card_title") or article["title"])
    return f"""<div class="visual title-card">
      <div class="title-card-mesh" aria-hidden="true"></div>
      <div class="title-card-inner">
        <span>{cat}</span>
        <strong>{title}</strong>
        <em>Actu Boxe</em>
      </div>
    </div>"""


def visual_html(article: dict, lazy: bool = True, list_view: bool = False, compact: bool = False) -> str:
    if compact:
        src = article.get("thumb") or article.get("image")
    else:
        src = article.get("list_image") if list_view else None
        src = src or article.get("image")
    if not src:
        return title_card_html(article)
    alt = escape(article.get("image_alt", article["title"]))
    load = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    poster = " visual-poster" if list_view and article.get("list_image") else ""
    return f'<div class="visual{poster}"><img src="{src}" alt="{alt}"{load}></div>'


def card(article: dict, extra_class: str = "", *, list_view: bool = True, compact: bool = False) -> str:
    heading = escape(article.get("card_title") or article["title"])
    return f"""
<article class="item {extra_class}">
  <a href="{href_article(article['slug'])}">
    {visual_html(article, list_view=list_view, compact=compact)}
    <div class="meta">
      <span class="date">{article['date']}</span>
      <h3>{heading}</h3>
      <p>{article['excerpt']}</p>
    </div>
  </a>
</article>
"""


def cards_html(articles: list[dict]) -> str:
    if not articles:
        return """<div class="empty-state"><strong>Contenus à venir</strong>
        <p>Les premiers articles de cette rubrique seront ajoutés ensuite.</p></div>"""
    return '<div class="cards-grid">' + "".join(card(a) for a in articles) + "</div>"


def home() -> str:
    featured = get("championnats-d-europe-2026-la-selection-francaise-pour-sofia")
    others = [
        get("flora-pili-s-incline-face-a-katie-taylor-a-dublin"),
        get("ibrahim-boukedim-defend-son-titre-a-metz"),
        get("gala-saint-nazaire-clavier-ntambwe"),
        get("toulouse-minimes-boxing-club"),
    ]
    hero = [featured, *others]
    cards = []
    for i, art in enumerate(hero, 1):
        extra = f"<p>{art['excerpt']}</p>" if i == 1 else ""
        cards.append(f"""
        <article class="hero-item hero-item-{i}">
          <a href="{href_article(art['slug'])}">
            {visual_html(art, lazy=i > 1)}
            <div class="overlay"></div>
            <div class="content">
              <span>{art['date']} · {art['category']}</span>
              <h2>{art['title']}</h2>
              {extra}
            </div>
          </a>
        </article>""")
    sections = [
        ("France", "Actualités", "/actualites/", by_tag("actualites")),
        ("Après le gong", "Résultats", "/resultats/", by_tag("resultats")),
        ("Calendrier", "Combats à venir", "/combats-a-venir/", by_tag("combats-a-venir")),
        ("Salles", "Clubs", "/clubs/", by_tag("clubs")),
        ("Portraits", "Boxeurs", "/boxeurs/", by_tag("boxeurs")),
        ("Soirées", "Galas", "/galas/", by_tag("galas")),
        ("Paroles", "Interviews", "/interviews/", by_tag("interviews")),
        ("Décryptage", "Analyses", "/analyses/", by_tag("analyses")),
    ]
    sec_html = []
    for label, title, more, arts in sections:
        items = "".join(card(a, list_view=False, compact=True) for a in arts[:6])
        sec_html.append(f"""
        <section class="section is-visible">
          <header>
            <div>
              <span>{label}</span>
              <h2>{title}</h2>
            </div>
            <a class="more" href="{more}">Voir tout</a>
          </header>
          <div class="list">{items}</div>
        </section>""")
    body = f"""
<main id="blog-home">
  <h1 class="visually-hidden" id="contenu">Actu Boxe — actualité de la boxe anglaise</h1>
  <div class="inner">
    <section class="hero-grid">{''.join(cards)}</section>
    <div class="adBox" style="--ad-logo: url('/assets/img/logo.png');">
      <h3>Vous représentez un club ou un gala ?</h3>
      <a href="mailto:contact@actu-boxe.com"><p>Écrire à <strong>contact@actu-boxe.com</strong></p></a>
    </div>
    <div class="sections">{''.join(sec_html)}</div>
  </div>
</main>
"""
    return page_shell(
        "Accueil",
        "Média francophone d’actualité sur la boxe anglaise : résultats, galas, champions, clubs et analyses.",
        body,
        "home",
        path="/",
        image="/assets/img/sofia-equipe-france-card.jpg",
        image_alt="Boxeurs de l’équipe de France, visuel FFBoxe",
        title_full="Actu Boxe | Actualité de la boxe anglaise",
    )


def listing_page(slug: str, title: str, kicker: str, intro: str) -> str:
    extra = ""
    if slug == "mentions-legales":
        extra = """<div class="legal-content">
          <h2>Éditeur</h2>
          <p><strong>Actu Boxe</strong> — média francophone d’actualité sur la boxe anglaise.</p>
          <p>Publication visée&nbsp;: <strong>actu-boxe.com</strong> (site en préproduction).</p>
          <p>Directeur de la publication&nbsp;: à désigner avant la mise en ligne publique. Aucun nom ni SIRET n’est inventé ici.</p>
          <h2>Contact</h2>
          <p>Email définitif de la rédaction&nbsp;: <a href="mailto:contact@actu-boxe.com">contact@actu-boxe.com</a></p>
          <h2>Réseaux sociaux</h2>
          <p>Aucun compte officiel Instagram, X, Facebook, TikTok ou YouTube n’est ouvert à ce jour. Toute page tierce utilisant le nom Actu Boxe n’est pas un compte du site.</p>
          <h2>Hébergeur</h2>
          <p>Préproduction&nbsp;: hébergement local sur la machine de développement.</p>
          <p>Production&nbsp;: l’hébergeur (nom, raison sociale, adresse) sera indiqué ici lors de la mise en ligne sur actu-boxe.com.</p>
          <h2>Propriété intellectuelle</h2>
          <p>Textes&nbsp;: Actu Boxe. Photos&nbsp;: crédits indiqués sous chaque cliché (Moselle TV / Matthieu Henkinet, FFBoxe, clubs, visuels de gala). Le seul lien sortant vers un club est celui du Toulouse Minimes Boxing Club.</p>
        </div>"""
    if slug == "interviews":
        extra = """<div class="legal-content">
          <p>Les paroles publiées ici sont des extraits sourcés. Mehdi Boutlelis, Oussama (TMBC), Jean-Claude Mbiye et Ben Bachir n’ont pas encore d’entretien exclusif Actu Boxe&nbsp;: dès qu’un échange aura lieu, il remplacera cette mention.</p>
        </div>"""
    if slug == "confidentialite":
        extra = """<div class="legal-content">
          <p>Ce site n’utilise pour l’instant que les cookies techniques nécessaires au fonctionnement.</p>
          <p>Aucune donnée n’est cédée à des partenaires publicitaires à ce stade.</p>
          <p>Contact données&nbsp;: <a href="mailto:contact@actu-boxe.com">contact@actu-boxe.com</a></p>
        </div>"""
    cards = ""
    if slug not in {"mentions-legales", "confidentialite"}:
        cards = cards_html(by_tag(slug))
    active = {
        "actualites": "news",
        "resultats": "results",
        "combats-a-venir": "fights",
        "champions": "champs",
        "clubs": "clubs",
    }.get(slug, "home")
    body = f"""
<main class="page-shell" id="contenu">
  <header>
    <span>{kicker}</span>
    <h1>{title}</h1>
    <p>{intro}</p>
  </header>
  {cards}
  {extra}
</main>
"""
    crumbs = [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE}/"},
        {"@type": "ListItem", "position": 2, "name": title, "item": f"{SITE}/{slug}/"},
    ]
    return page_shell(
        title,
        intro,
        body,
        active,
        path=f"/{slug}/",
        extra_ld=[{"@type": "BreadcrumbList", "itemListElement": crumbs}],
    )


def article_page(article: dict) -> str:
    related = [a for a in ARTICLES if a["slug"] != article["slug"] and set(a["tags"]) & set(article["tags"])][:4]
    info = "".join(f"<p><strong>{k}</strong> — {v}</p>" for k, v in article.get("info") or [])
    rel = "".join(
        f'<a href="{href_article(a["slug"])}">{a["title"]}</a>' for a in related
    ) or "<p>Plus d’articles à venir.</p>"
    hero_bg = ""
    hero_class = "ab-hero"
    if article.get("image"):
        alt = escape(article.get("image_alt", article["title"]))
        hero_bg = f'<div class="ab-hero-bg"><img src="{article["image"]}" alt="{alt}" fetchpriority="high"></div>'
    else:
        hero_class = "ab-hero ab-hero-typo"
        hero_bg = '<div class="title-card-mesh" aria-hidden="true"></div>'
    gallery = ""
    if article.get("gallery"):
        figs = "".join(
            f'<figure><img src="{src}" alt="{escape(alt)}" loading="lazy" decoding="async"><figcaption>{escape(alt)}</figcaption></figure>'
            for src, alt in article["gallery"]
        )
        gallery = f'<div class="ab-gallery">{figs}</div>'
    sources_html = ""
    if article.get("sources"):
        lis = []
        for item in article["sources"]:
            if isinstance(item, str):
                lis.append(f"<li>{item}</li>")
                continue
            label, href = item
            if not href:
                lis.append(f"<li>{label}</li>")
            elif href.startswith("/"):
                lis.append(f'<li><a href="{href}">{label}</a></li>')
            else:
                lis.append(f'<li><a href="{href}" target="_blank" rel="noopener">{label}</a></li>')
        sources_html = f'<section class="ab-sources"><h3>Sources</h3><ul>{"".join(lis)}</ul></section>'
    crumbs = [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE}/"},
        {"@type": "ListItem", "position": 2, "name": article["category"], "item": f"{SITE}{article['category_href']}"},
        {"@type": "ListItem", "position": 3, "name": article["title"], "item": f"{SITE}/articles/{article['slug']}/"},
    ]
    news_ld = {
        "@type": "NewsArticle",
        "headline": article["title"],
        "description": article["excerpt"],
        "datePublished": article["date_iso"],
        "dateModified": article["date_iso"],
        "inLanguage": "fr-FR",
        "mainEntityOfPage": f"{SITE}/articles/{article['slug']}/",
        "author": {"@id": f"{SITE}/#org"},
        "publisher": {"@id": f"{SITE}/#org"},
        "image": f"{SITE}{article['image']}" if article.get("image") else f"{SITE}/assets/img/logo.png",
    }
    body = f"""
<main class="page-shell" id="contenu">
  <article>
    <header class="{hero_class}">
      {hero_bg}
      <div class="inner">
        <a class="ab-badge" href="{article['category_href']}">{article['category']}</a>
        <h1>{article['title']}</h1>
        <p class="excerpt">{article['excerpt']}</p>
        <div class="ab-meta">
          <span>{article['date']}</span>
          <span>Actu Boxe</span>
        </div>
      </div>
    </header>
    <div class="ab-layout">
      <div class="ab-body">{gallery}{article['body']}{sources_html}</div>
      <aside class="ab-aside">
        <div class="ab-box">
          <h3>Informations</h3>
          {info}
        </div>
        <div class="ab-box">
          <h3>À lire aussi</h3>
          {rel}
        </div>
      </aside>
    </div>
  </article>
</main>
"""
    return page_shell(
        article["title"],
        article["excerpt"],
        body,
        article["active"],
        path=f"/articles/{article['slug']}/",
        image=article.get("image", ""),
        image_alt=article.get("image_alt", article["title"]),
        og_type="article",
        date_published=article["date_iso"],
        extra_ld=[
            {"@type": "BreadcrumbList", "itemListElement": crumbs},
            news_ld,
        ],
    )


def champions_page() -> str:
    body = """
<main class="page-shell" id="contenu">
  <header>
    <span>Titres en cours</span>
    <h1>Champions actuels</h1>
    <p>France, Europe, monde&nbsp;: uniquement les lignes vérifiées au 7 septembre 2026. Pas de tableau inventé.</p>
  </header>
  <h2>France</h2>
  <div class="table-scroll">
  <table class="champ-table">
    <thead><tr><th>Catégorie</th><th>Champion / championne</th><th>Organisation</th><th>Note</th></tr></thead>
    <tbody>
      <tr>
        <td>Poids lourds</td>
        <td>Eder Galina Fortes (FRA)</td>
        <td>Championnat de France professionnel</td>
        <td>Titre pris le 1er août 2026 à Deauville, aux points contre Clément Gilet (97-92, 98-91, 95-94). Source FFBoxe, 2 août 2026.</td>
      </tr>
      <tr>
        <td>Lourds-légers (90,719 kg)</td>
        <td>Vacant</td>
        <td>Championnat de France professionnel</td>
        <td>Enjeu le 9 octobre 2026 à Saint-Nazaire&nbsp;: Brice Clavier vs Gaëtan Ntambwe (Ouest-France, août 2026).</td>
      </tr>
      <tr>
        <td>Mi-lourds (79,378 kg)</td>
        <td>Vacant</td>
        <td>Championnat de France professionnel</td>
        <td>Enjeu le 17 octobre 2026 à Béziers&nbsp;: Lenny Patrach vs Samir Ghodbane (FFBoxe, DNA).</td>
      </tr>
    </tbody>
  </table>
  </div>
  <h2>Europe</h2>
  <div class="table-scroll">
  <table class="champ-table">
    <thead><tr><th>Catégorie</th><th>Champion / championne</th><th>Organisation</th><th>Note</th></tr></thead>
    <tbody>
      <tr>
        <td>Élites amateur</td>
        <td>—</td>
        <td>European Boxing · Sofia</td>
        <td>Championnats d’Europe Élites du 17 au 26 septembre 2026. Aucun titre issu de cette édition n’est encore attribué. Sélection FFBoxe du 4 septembre.</td>
      </tr>
    </tbody>
  </table>
  </div>
  <h2>Monde</h2>
  <div class="table-scroll">
  <table class="champ-table">
    <thead><tr><th>Catégorie</th><th>Champion / championne</th><th>Organisation</th><th>Note</th></tr></thead>
    <tbody>
      <tr>
        <td>Super-légers femmes</td>
        <td>
          <div class="champ-cell">
            <img src="/assets/img/katie-taylor.jpg" alt="Katie Taylor">
            <span>Vacant</span>
          </div>
        </td>
        <td>WBA, WBO, IBF, WBC, IBO</td>
        <td>Katie Taylor (IRL) sacre incontesté le 5 sept. 2026 à Dublin (26-1), puis retrait. Ceintures libérées. Pas de successeur vérifié.</td>
      </tr>
      <tr>
        <td>Coqs · Youth</td>
        <td>
          <div class="champ-cell">
            <img src="/assets/img/ibrahim-boukedim.jpg" alt="Ibrahim Boukedim">
            <span>Ibrahim Boukedim (FRA)</span>
          </div>
        </td>
        <td>WBC Youth</td>
        <td>Titre pris à Dubaï le 14 fév. 2026 (FFBoxe). Première défense à Metz le 18 sept. 2026. Ce n’est pas un titre mondial majeur.</td>
      </tr>
    </tbody>
  </table>
  </div>
  <p class="update-note">Dernière mise à jour : 7 septembre 2026. Les autres ceintures monde / Europe / France resteront vides tant qu’une source à jour n’est pas disponible.</p>
</main>
"""
    return page_shell(
        "Champions actuels",
        "Champions de France, d’Europe et du monde, uniquement avec une source à jour.",
        body,
        "champs",
        path="/champions/",
        image="/assets/img/ibrahim-boukedim.jpg",
        extra_ld=[{
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Champions", "item": f"{SITE}/champions/"},
            ],
        }],
    )


def gone_cotes_page() -> str:
    body = """
<main class="page-shell" id="contenu">
  <header>
    <span>Page retirée</span>
    <h1>Cette rubrique n’existe plus</h1>
    <p>La page Cotes / pronostics a été retirée. Les lectures de combats restent dans Analyses.</p>
  </header>
  <p><a href="/analyses/">Aller aux analyses</a> · <a href="/articles/ibrahim-boukedim-defend-son-titre-a-metz/">Gala La Relève à Metz</a></p>
</main>
"""
    return page_shell(
        "Page retirée",
        "La rubrique Cotes a été retirée. Consultez les analyses Actu Boxe.",
        body,
        "home",
        path="/cotes/",
        canonical=f"{SITE}/analyses/",
        noindex=True,
    )


def organisations_page() -> str:
    body = """
<main class="page-shell" id="contenu">
  <header>
    <span>Écosystème</span>
    <h1>Organisations</h1>
    <p>Repères pour lire les ceintures et les fédérations, sans jargon inutile.</p>
  </header>
  <div class="ab-body">
    <h2>Les ceintures mondiales professionnelles</h2>
    <p><strong>WBC, WBA, IBF et WBO</strong> sont les quatre organisations dont les titres mondiaux structurent le plus souvent l’actualité. Un boxeur « incontesté » réunit les quatre dans la même catégorie. L’<strong>IBO</strong> est une ceinture supplémentaire, souvent défendue en même temps qu’une des quatre.</p>
    <p><strong>L’EBU</strong> organise notamment les titres européens professionnels. <strong>La FFBoxe</strong> est la fédération française : licences, amateur, championnats de France, cadre fédéral.</p>
    <p><strong>WBC Youth</strong> n’est pas un titre mondial majeur. C’est une ceinture jeunesse de la WBC. Ibrahim Boukedim la détient chez les coqs ; sa première défense est à Metz le 18 septembre 2026.</p>
    <h2>Amateur et Jeux</h2>
    <p>Le circuit amateur international a changé de gouvernance. Les Championnats d’Europe 2026 à Sofia sont présentés par la FFBoxe comme la première édition Élites sous l’égide d’European Boxing, dans un paysage tourné vers World Boxing et le calendrier olympique de Los Angeles 2028 (sept catégories hommes, sept femmes).</p>
    <p>Cette page n’envoie vers aucun site d’organisation. Les ceintures suivies, une fois vérifiées, sont dans <a href="/champions/">Champions</a>.</p>
  </div>
</main>
"""
    return page_shell(
        "Organisations",
        "WBC, WBA, IBF, WBO, EBU, FFBoxe : comprendre les organisations de la boxe anglaise.",
        body,
        "home",
        path="/organisations/",
        extra_ld=[{
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "Organisations", "item": f"{SITE}/organisations/"},
            ],
        }],
    )


def write(rel: str, html: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


def write_sitemap() -> None:
    urls = ["/"]
    for slug, *_ in PAGES:
        urls.append(f"/{slug}/")
    for article in ARTICLES:
        urls.append(f"/articles/{article['slug']}/")
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in urls:
        lastmod = ""
        art = next((a for a in ARTICLES if f"/articles/{a['slug']}/" == path), None)
        if art:
            lastmod = f"<lastmod>{art['date_iso']}</lastmod>"
        else:
            lastmod = "<lastmod>2026-09-07</lastmod>"
        body.append(f"  <url><loc>{SITE}{path}</loc>{lastmod}</url>")
    body.append("</urlset>")
    write("sitemap.xml", "\n".join(body) + "\n")
    write(
        "robots.txt",
        "User-agent: *\nAllow: /\nDisallow: /cotes/\nSitemap: https://actu-boxe.com/sitemap.xml\n",
    )


def main() -> None:
    write("index.html", home())
    write("champions/index.html", champions_page())
    write("cotes/index.html", gone_cotes_page())
    write("organisations/index.html", organisations_page())
    for slug, title, kicker, intro in PAGES:
        if slug in {"champions", "organisations"}:
            continue
        write(f"{slug}/index.html", listing_page(slug, title, kicker, intro))
    for article in ARTICLES:
        write(f"articles/{article['slug']}/index.html", article_page(article))
    write_sitemap()


if __name__ == "__main__":
    main()
