"""Self-contained editorial illustrations for Actu Boxe (Python standard library).

These are explicitly labelled illustrations, never purported event photographs.
The caller is responsible for verifying all names and facts in ``image_brief``.
No source image, network request, external font or tracking URL is involved.
"""

from __future__ import annotations

from hashlib import sha256
from html import escape
from pathlib import Path
import unicodedata


_KINDS = {
    "fight": "COMBAT",
    "results": "RÉSULTATS",
    "championship": "CHAMPIONNAT",
    "club": "VIE DES CLUBS",
}


def _clean(value: object, limit: int = 1600) -> str:
    """Collapse whitespace and discard controls forbidden in XML or bidi text."""
    text = str(value or "")[:limit]
    text = "".join(
        " " if char.isspace() else char
        for char in text
        if (char.isspace() or unicodedata.category(char) not in {"Cc", "Cf", "Cs"})
        and ord(char) not in {0xFFFE, 0xFFFF}
    )
    return " ".join(text.split())


def _width(text: str, size: int) -> float:
    """Conservative advance estimate, also used as the SVG's actual text length."""
    width = 0.0
    for char in text:
        if unicodedata.combining(char):
            continue
        if unicodedata.east_asian_width(char) in {"W", "F"}:
            width += 1.0
        elif char in "MW@%Œœ":
            width += 0.96
        elif char in "ilI.,:;!|'’ ":
            width += 0.30
        elif char.isupper():
            width += 0.71
        else:
            width += 0.58
    return width * size


def _wrap(text: str, size: int, width: int, max_lines: int) -> list[str]:
    """Word wrap, including single oversized words; visibly truncate at the limit."""
    pending = _clean(text)
    lines: list[str] = []
    while pending and len(lines) < max_lines:
        if _width(pending, size) <= width:
            lines.append(pending)
            break
        end = 1
        while end < len(pending) and _width(pending[: end + 1], size) <= width:
            end += 1
        boundary = pending.rfind(" ", 0, end + 1)
        if boundary > 0:
            end = boundary
        line, pending = pending[:end].rstrip(), pending[end:].lstrip()
        if len(lines) == max_lines - 1 and pending:
            while line and _width(line + "…", size) > width:
                line = line[:-1].rstrip()
            line += "…"
        lines.append(line)
    return lines


def _text(
    value: str, *, x: int, y: int, size: int, width: int,
    lines: int = 1, leading: int | None = None, fill: str = "#ffffff",
    weight: int = 700, role: str = "label",
) -> str:
    rows = _wrap(value, size, width, lines)
    spans = []
    for index, row in enumerate(rows):
        length = min(float(width), _width(row, size))
        spans.append(
            f'<tspan x="{x}" y="{y + index * (leading or size + 8)}" '
            f'textLength="{length:.2f}" lengthAdjust="spacingAndGlyphs">'
            f'{escape(row)}</tspan>'
        )
    return (
        f'<text data-role="{role}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}">{"".join(spans)}</text>'
    )


def _glove(transform: str, color: str = "url(#glove)") -> str:
    # Original paths: curled fingers, thumb, stitched palm and wide wrist cuff.
    return f'''<g transform="{transform}" stroke-linejoin="round">
      <path d="M38 180 C15 159 9 126 18 106 L31 88 L31 50
               C31 12 58 -5 91 0 C128 -3 156 18 157 51 L160 112
               C160 143 146 164 132 179 L131 225 L42 225 Z"
            fill="{color}" stroke="#ff6464" stroke-width="3"/>
      <path d="M36 91 C3 79 -15 100 -5 124 L24 166 C34 182 51 183 62 169
               C70 157 64 145 56 135 L41 112"
            fill="{color}" stroke="#ff6464" stroke-width="3"/>
      <path d="M55 35 C78 21 107 22 133 40 M67 63 L137 67 M78 172 L127 172"
            fill="none" stroke="#ff9999" stroke-opacity=".52" stroke-width="3"/>
      <path d="M40 187 L134 187 L131 225 L42 225 Z" fill="#f5f4f0" stroke="#f5f4f0"/>
      <path d="M55 202 L115 202 M55 212 L104 212" stroke="#b1b1b1" stroke-width="3"/>
    </g>'''


def _motif(kind: str) -> str:
    if kind == "fight":
        return _glove("translate(805 176) rotate(-20 80 105) scale(.83)") + _glove(
            "translate(989 203) rotate(22 70 90) scale(.73)", "url(#silver)"
        )
    if kind == "championship":
        return '''<g transform="translate(930 287)">
          <path d="M-38 39 L-65 130 L-28 116 L0 142 L25 41" fill="#d31212"/>
          <path d="M-4 44 L25 142 L49 114 L81 125 L41 33" fill="#8f1111"/>
          <circle r="89" fill="#272729" stroke="#cfd3d8" stroke-width="3"/>
          <circle r="70" fill="#171719" stroke="#6c6c70" stroke-width="2"/>
          <path d="M0 -46 L13 -15 L47 -12 L21 10 L29 44 L0 26 L-29 44
                   L-21 10 L-47 -12 L-13 -15 Z" fill="#f5f4f0"/>
        </g>''' + _glove("translate(1044 163) rotate(17 60 85) scale(.43)")
    if kind == "results":
        return '''<g transform="translate(817 198) rotate(-7 115 110)">
          <rect width="224" height="227" rx="16" fill="#202023" stroke="#656569" stroke-width="2"/>
          <rect width="224" height="47" rx="16" fill="#d31212"/>
          <path d="M34 78 H181 M34 111 H148 M34 144 H164" stroke="#929298" stroke-width="8"/>
          <circle cx="166" cy="180" r="47" fill="#f4f3ef"/>
          <path d="M144 179 L160 196 L189 161" fill="none" stroke="#bd1111" stroke-width="9"/>
        </g>''' + _glove("translate(1031 133) rotate(20 60 85) scale(.45)")
    return '''<g stroke="#a1a1a7" fill="none" stroke-width="4">
      <path d="M871 129 V183 M1031 129 V202 M849 129 H1053"/>
      <path d="M909 196 H991 V400 Q950 428 909 400 Z" fill="#242427"/>
      <path d="M918 232 H982 M918 370 H982" stroke="#d31212" stroke-width="12"/>
    </g>''' + _glove("translate(790 213) rotate(-17 80 105) scale(.64)")


def render_news_image(article: dict, destination: Path) -> None:
    """Write a deterministic 1200×675 original SVG for a verified article.

    ``image_brief`` accepts ``kicker``, a short ``headline``, two or three verified
    ``facts`` and a ``kind`` (fight, results, championship or club). Long text is
    wrapped then ellipsized; no facts are invented to fill missing fields.
    """
    brief = article.get("image_brief") or {}
    if not isinstance(brief, dict):
        raise ValueError("image_brief must be an object")
    title = _clean(article.get("title") or "Actualité boxe")
    headline = _clean(brief.get("headline")) or title
    kind = brief.get("kind", "fight")
    if not isinstance(kind, str) or kind not in _KINDS:
        kind = "fight"
    facts = brief.get("facts") or []
    if not isinstance(facts, list):
        raise ValueError("image_brief.facts must be a list")
    facts = [_clean(fact) for fact in facts[:3] if _clean(fact)]
    seed = sha256(_clean(article.get("slug") or title).encode("utf-8")).digest()
    accent_width = 120 + seed[0] % 100
    text = [
        _text("ACTU BOXE", x=55, y=66, size=25, width=225),
        _text(_KINDS[kind], x=835, y=64, size=15, width=302, fill="#cfd3d8"),
        _text(_clean(brief.get("kicker")) or _KINDS[kind], x=55, y=151,
              size=17, width=615, fill="#ff6666"),
        _text(headline, x=52, y=222, size=53, width=626, lines=3,
              leading=61, weight=800, role="headline"),
        _text("Illustration Actu Boxe", x=802, y=627, size=15, width=335,
              fill="#dadadd", weight=400, role="credit"),
        _text("L’ACTUALITÉ, AU PLUS PRÈS DU RING.", x=55, y=627,
              size=12, width=635, fill="#a1a1a7", weight=400),
    ]
    for index, fact in enumerate(facts):
        y = 428 + index * 54
        text.append(f'<rect x="55" y="{y - 14}" width="4" height="17" fill="#d31212"/>')
        text.append(_text(fact, x=75, y=y, size=19, width=595, lines=2,
                          leading=23, fill="#d7d7db", weight=400, role="fact"))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675"
        viewBox="0 0 1200 675" role="img" aria-labelledby="title description">
      <title id="title">{escape(title)}</title>
      <desc id="description">Illustration originale Actu Boxe : {escape(headline)}.
        Dessin stylisé de boxe, sans représentation photographique de l’événement.</desc>
      <defs>
        <linearGradient id="background" x2="1" y2="1">
          <stop stop-color="#1c1c1f"/><stop offset="1" stop-color="#09090a"/>
        </linearGradient>
        <radialGradient id="halo">
          <stop stop-color="#9b161c" stop-opacity=".42"/>
          <stop offset="1" stop-color="#9b161c" stop-opacity="0"/>
        </radialGradient>
        <linearGradient id="glove" x2="1" y2="1">
          <stop stop-color="#ee3333"/><stop offset="1" stop-color="#8b070d"/>
        </linearGradient>
        <linearGradient id="silver" x2="1" y2="1">
          <stop stop-color="#757579"/><stop offset="1" stop-color="#333338"/>
        </linearGradient>
        <clipPath id="canvas"><rect width="1200" height="675"/></clipPath>
      </defs>
      <g clip-path="url(#canvas)" font-family="Arial, Helvetica, sans-serif">
        <rect width="1200" height="675" fill="url(#background)"/>
        <rect width="1200" height="7" fill="#d31212"/>
        <circle cx="965" cy="298" r="300" fill="url(#halo)"/>
        <path d="M704 96 L704 567" stroke="#ffffff" stroke-opacity=".1"/>
        <circle cx="948" cy="294" r="177" fill="none" stroke="#d31212" stroke-opacity=".35"/>
        <circle cx="948" cy="294" r="190" fill="none" stroke="#ffffff" stroke-opacity=".05"/>
        <path d="M727 476 L943 573 L1157 464 L946 383 Z" fill="#27272b" stroke="#66666c"/>
        <path d="M727 476 L727 491 L943 590 L943 573 M943 590 L1157 480 L1157 464"
              fill="#141416" stroke="#515157"/>
        <g fill="none" stroke-width="3">
          <path d="M740 422 L943 514 L1144 412 M740 440 L943 532 L1144 430"
                stroke="#b6b6ba"/>
          <path d="M740 458 L943 550 L1144 448" stroke="#d31212"/>
        </g>
        <path d="M740 413 V480 M943 503 V574 M1144 402 V470"
              stroke="#f4f3ef" stroke-width="8"/>
        {_motif(kind)}
        <rect x="55" y="379" width="{accent_width}" height="4" fill="#d31212"/>
        <path d="M55 588 H1145" stroke="#ffffff" stroke-opacity=".12"/>
        {''.join(text)}
      </g>
    </svg>'''
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8")
