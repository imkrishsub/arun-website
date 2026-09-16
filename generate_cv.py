#!/usr/bin/env python3
"""
CV generation pipeline for arun-website.

Reads a source page, extracts structured CV data, and renders a print-optimised
A4 PDF using Playwright. The PDF keeps the site's financial-terminal aesthetic
(Courier New, gold accents, uppercase section labels) on a white background
suitable for recruiters and ATS scanners.

Two languages, both two pages: --lang en renders index.html to
Arun-Murugan-CV-print.pdf, --lang de renders de/index.html to
Arun-Murugan-Lebenslauf-print.pdf. --generic additionally drops the sought-role
line under the name and in the footer, for applications outside reconciliation
(--lang de --generic renders Arun-Murugan-Lebenslauf-generisch.pdf).

Requirements:
    pip install -r requirements-cv.txt
    playwright install chromium

Usage:
    python generate_cv.py [--lang en|de] [--generic] [--source PAGE] [--output PDF]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import pathlib
import re
import sys

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    sys.exit("Error: beautifulsoup4 not installed. Run: pip install -r requirements-cv.txt")

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit(
        "Error: playwright not installed. Run:\n"
        "  pip install -r requirements-cv.txt\n"
        "  playwright install chromium"
    )

REPO_ROOT = pathlib.Path(__file__).parent

# Chrome the CV adds on top of the site content: section headings, the footer
# strapline and the document title. Everything else is lifted verbatim from the
# source page, so index.html feeds the English CV and de/index.html the German.
# Header contact icons as (viewBox, path). Material Symbols (outlined) for mail,
# call, language and location_on; Material has no LinkedIn mark, so that one is
# the Simple Icons brand glyph.
CONTACT_ICONS = {
    "mail": ("0 -960 960 960", "M160-160q-33 0-56.5-23.5T80-240v-480q0-33 23.5-56.5T160-800h640q33 0 56.5 23.5T880-720v480q0 33-23.5 56.5T800-160H160Zm320-280L160-640v400h640v-400L480-440Zm0-80 320-200H160l320 200ZM160-640v-80 480-400Z"),
    "linkedin": ("0 0 24 24", "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"),
    "website": ("0 -960 960 960", "M480-80q-82 0-155-31.5t-127.5-86Q143-252 111.5-325T80-480q0-83 31.5-155.5t86-127Q252-817 325-848.5T480-880q83 0 155.5 31.5t127 86q54.5 54.5 86 127T880-480q0 82-31.5 155t-86 127.5q-54.5 54.5-127 86T480-80Zm0-82q26-36 45-75t31-83H404q12 44 31 83t45 75Zm-104-16q-18-33-31.5-68.5T322-320H204q29 50 72.5 87t99.5 55Zm208 0q56-18 99.5-55t72.5-87H638q-9 38-22.5 73.5T584-178ZM170-400h136q-3-20-4.5-39.5T300-480q0-21 1.5-40.5T306-560H170q-5 20-7.5 39.5T160-480q0 21 2.5 40.5T170-400Zm216 0h188q3-20 4.5-39.5T580-480q0-21-1.5-40.5T574-560H386q-3 20-4.5 39.5T380-480q0 21 1.5 40.5T386-400Zm268 0h136q5-20 7.5-39.5T800-480q0-21-2.5-40.5T790-560H654q3 20 4.5 39.5T660-480q0 21-1.5 40.5T654-400Zm-16-240h118q-29-50-72.5-87T584-782q18 33 31.5 68.5T638-640Zm-234 0h152q-12-44-31-83t-45-75q-26 36-45 75t-31 83Zm-200 0h118q9-38 22.5-73.5T376-782q-56 18-99.5 55T204-640Z"),
    "phone": ("0 -960 960 960", "M798-120q-125 0-247-54.5T329-329Q229-429 174.5-551T120-798q0-18 12-30t30-12h162q14 0 25 9.5t13 22.5l26 140q2 16-1 27t-11 19l-97 98q20 37 47.5 71.5T387-386q31 31 65 57.5t72 48.5l94-94q9-9 23.5-13.5T670-390l138 28q14 4 23 14.5t9 23.5v162q0 18-12 30t-30 12ZM241-600l66-66-17-94h-89q5 41 14 81t26 79Zm358 358q39 17 79.5 27t81.5 13v-88l-94-19-67 67ZM241-600Zm358 358Z"),
    "address": ("0 -960 960 960", "M480-480q33 0 56.5-23.5T560-560q0-33-23.5-56.5T480-640q-33 0-56.5 23.5T400-560q0 33 23.5 56.5T480-480Zm0 294q122-112 181-203.5T720-552q0-109-69.5-178.5T480-800q-101 0-170.5 69.5T240-552q0 71 59 162.5T480-186Zm0 106Q319-217 239.5-334.5T160-552q0-150 96.5-239T480-880q127 0 223.5 89T800-552q0 100-79.5 217.5T480-80Zm0-480Z"),
}


def _contact_icon(name: str) -> str:
    """Inline SVG marker for a header contact item.

    SVG, not font glyphs: the embedded Plex subsets are latin-only, so symbols
    like U+2709/260E fell back to a system font and printed at the wrong
    weight. SVG also stays out of the extracted text, so ATS parsers read the
    bare values. Sized inline so the cover letter and work-authorization pages
    can reuse it without copying CSS.
    """
    view_box, path = CONTACT_ICONS[name]
    return (
        f'<svg viewBox="{view_box}" aria-hidden="true" '
        f'style="width:8.5pt;height:8.5pt;fill:currentColor;flex:none">'
        f'<path d="{path}"/></svg>'
    )


LOCALE = {
    "en": {
        "doc_lang": "en",
        "doc_title": "CV",
        "zoom": 1.0,
        "sections": {
            "profile": "Professional profile",
            "experience": "Performance history",
            "skills": "Skills",
            "education": "Education &amp; awards",
            "languages": "Languages",
        },
        # One fact per line: as a single "·"-separated run these wrapped at
        # whatever word hit the right margin, stranding fragments mid-clause.
        "footer": [
            "Chancenkarte holder — no sponsorship required",
            "Based in Frankfurt am Main",
        ],
        # The site no longer publishes an address; the CV still prints one.
        # A source page that has its own Address row overrides this.
        "address": "Frankfurt am Main, Germany",
    },
    "de": {
        "doc_lang": "de",
        "doc_title": "Lebenslauf",
        "zoom": 1.05,
        "sections": {
            "profile": "Kurzprofil",
            "experience": "Berufserfahrung",
            "skills": "Kenntnisse",
            "education": "Ausbildung &amp; Auszeichnungen",
            "languages": "Sprachkenntnisse",
        },
        "footer": [
            "Chancenkarte-Inhaber — keine Sponsorship nötig",
            "Wohnhaft in Frankfurt am Main",
        ],
        "address": "Frankfurt am Main, Deutschland",
    },
}


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def _text(el: Tag | None, default: str = "") -> str:
    return el.get_text(strip=True) if el else default


def extract(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Header
    name = _text(soup.select_one(".symbol"))
    full_name = _text(soup.select_one(".full-name"))
    description = _text(soup.select_one(".hero-desc"))

    tags = [
        {"text": _text(t), "highlight": "highlight" in t.get("class", [])}
        for t in soup.select(".hero-tags .tag")
    ]

    # Contact
    contact: dict[str, str] = {}
    for row in soup.select(".contact-row"):
        lbl = _text(row.select_one(".lbl")).lower()
        val = _text(row.select_one(".val"))
        if "mail" in lbl:  # "Email" (en) and "E-Mail" (de)
            contact["email"] = val
        elif "linkedin" in lbl:
            contact["linkedin"] = val
        elif "website" in lbl or "webseite" in lbl:
            contact["website"] = val
        elif "phone" in lbl or "telefon" in lbl:
            contact["phone"] = val
        elif "address" in lbl or "adresse" in lbl:
            contact["address"] = val

    # Key stats
    stats = [
        {
            "label": _text(c.select_one(".stat-label")),
            "value": _text(c.select_one(".stat-value")),
            "sub": _text(c.select_one(".stat-sub")),
        }
        for c in soup.select(".stat-card")
    ]

    # Skills
    skills: dict[str, list] = {"core": [], "tools": []}
    for panel in soup.select(".panel"):
        title = _text(panel.select_one(".panel-title")).lower()
        rows = [
            {
                "name": _text(r.select_one(".skill-name")),
                "level": _text(r.select_one(".skill-badge")),
                "cls": next(
                    (c for c in r.select_one(".skill-badge").get("class", [])
                     if c != "skill-badge"),
                    ""
                ) if r.select_one(".skill-badge") else "",
            }
            for r in panel.select(".skill-row")
            if r.select_one(".skill-name") and r.select_one(".skill-badge")
        ]
        if "core" in title or "kernkompetenzen" in title:
            skills["core"] = rows
        elif "tools" in title or "soft" in title:
            skills["tools"] = rows

    # Experience
    experience = [
        {
            "company": _text(r.select_one(".company")),
            "period": _text(r.select_one(".period")),
            "role": _text(r.select_one(".role-tag")),
            "bullets": [_text(li) for li in r.select("ul li")],
        }
        for r in soup.select(".ledger tbody tr")
        if r.select_one(".company")
    ]

    # Education — from the Academic record panel
    education = []
    for panel in soup.select(".panel"):
        panel_title = _text(panel.select_one(".panel-title")).lower()
        if "academic" in panel_title or "akademischer" in panel_title:
            education = [
                {
                    "degree": _text(i.select_one(".edu-degree")),
                    "school": _text(i.select_one(".edu-school")),
                    "meta": _text(i.select_one(".edu-meta")),
                }
                for i in panel.select(".edu-item")
                if i.select_one(".edu-degree")
            ]
            break

    # Languages
    languages = []
    for row in soup.select(".lang-row"):
        dots = row.select(".lang-dot")
        languages.append(
            {
                "name": _text(row.select_one(".lang-name")),
                "level": _text(row.select_one(".lang-level")),
                "filled": sum(1 for d in dots if "filled" in d.get("class", [])),
                "total": len(dots),
            }
        )

    return {
        "name": name,
        "full_name": full_name,
        "description": description,
        "tags": tags,
        "contact": contact,
        "stats": stats,
        "skills": skills,
        "experience": experience,
        "education": education,
        "languages": languages,
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_FONTS_DIR = REPO_ROOT / "assets" / "fonts"

# (family, weight declaration, style, filename) — Sans is a variable font
# covering 400–700 in one file; Mono ships as static weights.
_FONT_FILES = [
    ("IBM Plex Sans", "400 700", "normal", "IBMPlexSans-400-600-700-latin.woff2"),
    ("IBM Plex Mono", "400", "normal", "IBMPlexMono-400-latin.woff2"),
    ("IBM Plex Mono", "600", "normal", "IBMPlexMono-600-latin.woff2"),
]


def _font_css() -> str:
    """Embed the CV fonts as data URIs (set_content has no file base URL)."""
    faces = []
    for family, weight, style, filename in _FONT_FILES:
        path = _FONTS_DIR / filename
        if not path.exists():
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        faces.append(
            "@font-face {"
            f"font-family:'{family}';"
            f"font-weight:{weight};"
            f"font-style:{style};"
            f"src:url(data:font/woff2;base64,{encoded}) format('woff2');"
            "}"
        )
    return "\n".join(faces)


_CSS_TEMPLATE = """
@page { size: A4; margin: 13mm 15mm 13mm 15mm; }

:root {
  --gold: #b08000;
  --gold-bg: rgba(176,128,0,0.10);
  --muted: #555;
  --border: #d4d4d4;
  --text: #1a1a1a;
  --rule: #c8a000;
  --mono: 'IBM Plex Mono', 'Courier New', Courier, monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  /* Every size below is an absolute pt value, so a base font-size change does
     not cascade. zoom scales the whole layout uniformly instead, filling the
     page-1 gap left by moving skills to page 2 (9pt body reads as ~10pt).
     Substituted per language from LOCALE["zoom"]: German prose runs ~15% longer
     than the English, so it needs a smaller zoom to hold the same two pages.
     Raising either value past its tuned point pushes a whole experience block
     onto the next page and spills the CV to three pages. */
  zoom: {zoom};
  font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
  font-size: 9pt;
  color: var(--text);
  line-height: 1.5;
  background: #fff;
}

/* ── Header ── */
.cv-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14pt;
  border-bottom: 2px solid var(--rule);
  padding-bottom: 9pt;
  margin-bottom: 11pt;
}

.cv-header-main { flex: 1; min-width: 0; }

/* Photo top-right (German Lebenslauf convention) */
.cv-photo img {
  width: 28mm;
  height: 36mm;
  object-fit: cover;
  object-position: top;
  border: 1.5pt solid var(--rule);
  display: block;
}

.cv-name {
  font-family: var(--mono);
  font-size: 21pt;
  font-weight: 600;
  letter-spacing: 2px;
  line-height: 1.1;
}

.cv-name-accent { color: var(--gold); }

.cv-title {
  font-family: var(--mono);
  font-size: 8.5pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 3pt;
}

.cv-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4pt;
  margin-top: 6pt;
}

.tag {
  font-family: var(--mono);
  border: 1px solid var(--border);
  padding: 1.5pt 6pt;
  font-size: 7.5pt;
  letter-spacing: 0.5px;
  color: var(--muted);
}

.tag.hi {
  border-color: var(--gold);
  color: var(--gold);
  font-weight: bold;
}

.cv-contact {
  font-family: var(--mono);
  display: flex;
  flex-wrap: wrap;
  gap: 4pt 13pt;
  margin-top: 6pt;
  font-size: 8pt;
  color: var(--muted);
}

.cv-contact-item {
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 3pt;
}

/* Clickable in a PDF reader, but visually identical to the surrounding text —
   a printed CV should not sprout underlined blue links. */
.cv-link { color: inherit; text-decoration: none; }

/* ── Single-column body ── */
.cv-body {
  display: block;
}

/* ── Section headings ── */
.section { margin-bottom: 11pt; }

.sec-hdr {
  display: flex;
  align-items: center;
  gap: 7pt;
  margin-bottom: 6pt;
}

.sec-num {
  font-family: var(--mono);
  font-size: 7.5pt;
  letter-spacing: 2px;
  color: var(--gold);
  text-transform: uppercase;
}

.sec-title {
  font-size: 8.5pt;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 1.5px;
}

.sec-rule {
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* ── Summary ── */
.summary {
  font-size: 9pt;
  color: #333;
  line-height: 1.7;
  padding: 8pt 11pt;
  border-left: 3px solid var(--gold);
  background: #fafaf7;
}

/* ── Skills ── */
/* The section straddled the page boundary; start it on page 2 so it reads as
   one block. Everything after it (education, languages) follows on page 2. */
.section-skills { break-before: page; }

.skills-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 20pt;
}
.skill-panel + .skill-panel { margin-top: 7pt; }

.skill-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3.5pt 0;
  border-bottom: 1px solid #ebebeb;
  font-size: 9pt;
}

.skill-row:last-child { border-bottom: none; }

.skill-name { color: var(--muted); }

.skill-badge {
  font-family: var(--mono);
  font-size: 7.5pt;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  padding: 1pt 6pt;
}

.badge-expert    { background: var(--gold-bg); color: #7a5c00; }
.badge-advanced  { background: rgba(37,99,235,0.09); color: #1d4ed8; }
.badge-proficient { background: rgba(13,148,136,0.09); color: #0f766e; }
.badge-metric    { background: rgba(22,163,74,0.10); color: #15803d; }

/* ── Experience ── */
.exp-item { margin-bottom: 11pt; break-inside: avoid; }
.exp-item:last-child { margin-bottom: 0; }

.exp-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.exp-company { font-weight: bold; font-size: 9.5pt; }

.exp-period { font-family: var(--mono); font-size: 8pt; color: var(--muted); }

.exp-role {
  font-family: var(--mono);
  font-size: 7.5pt;
  color: var(--gold);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin: 2pt 0 4pt;
}

.exp-bullets { list-style: none; padding: 0; }

.exp-bullets li {
  font-size: 9pt;
  color: #333;
  margin-bottom: 2.5pt;
  padding-left: 11pt;
  position: relative;
}

/* Drawn with borders rather than "▸" (U+25B8): the embedded Plex subsets are
   latin-only and have no such glyph, so the character fell back to a system
   font on every bullet. A CSS triangle depends on no font at all. */
.exp-bullets li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 4pt;
  width: 0;
  height: 0;
  border-left: 3.2pt solid var(--gold);
  border-top: 2.4pt solid transparent;
  border-bottom: 2.4pt solid transparent;
}

/* ── Education ── */
.edu-item { margin-bottom: 5pt; }
.edu-item:last-child { margin-bottom: 0; }
.edu-degree { font-weight: bold; font-size: 9pt; }
.edu-school { color: var(--gold); font-size: 8.5pt; margin-top: 1pt; }
.edu-meta { color: var(--muted); font-size: 8pt; margin-top: 0.5pt; }
.edu-divider { height: 1px; background: var(--border); margin: 5pt 0; }

/* ── Languages ── */
.lang-row {
  display: flex;
  align-items: center;
  gap: 9pt;
  padding: 4.5pt 0;
  border-bottom: 1px solid #ebebeb;
  font-size: 9pt;
}

.lang-row:last-child { border-bottom: none; }

.lang-name { width: 55pt; }

.lang-dots { display: flex; gap: 4pt; }

.dot {
  width: 8pt;
  height: 8pt;
  border-radius: 50%;
  background: #ddd;
  flex-shrink: 0;
}

.dot.on { background: var(--gold); }

.lang-level { font-size: 8pt; color: var(--muted); margin-left: auto; text-align: right; max-width: 65%; }

/* ── Footer ── */
.cv-footer {
  font-family: var(--mono);
  margin-top: 12pt;
  padding-top: 7pt;
  border-top: 1px solid var(--border);
  font-size: 7.5pt;
  color: #aaa;
  text-align: center;
  letter-spacing: 1px;
}

.cv-footer-line { margin-bottom: 2.5pt; }
.cv-footer-line:last-child { margin-bottom: 0; }
"""

# Appended after _CSS. Tuned for office laser printers, which drop light tints
# and greyscale the gold: every accent is darkened past 7:1 on white, and tinted
# fills are swapped for outlines so they survive a mono print.
_PRINT_CSS = """
:root {
  --gold: #6b4e00;
  --gold-bg: #ffffff;
  --muted: #3a3a3a;
  --border: #8a8a8a;
  --text: #000;
  --rule: #000;
}

.summary {
  color: #000;
  background: #f0f0f0;
  border-left-width: 4px;
  border-left-color: #000;
}

.exp-bullets li, .skill-name { color: #1a1a1a; }

.skill-row, .lang-row { border-bottom-color: #9a9a9a; }

/* Outlined badges instead of tinted fills — a 9% alpha wash prints as nothing. */
.skill-badge {
  background: #fff;
  border: 1px solid currentColor;
  padding: 0.5pt 5pt;
}

.badge-expert     { color: #5a4300; }
.badge-advanced   { color: #17408b; }
.badge-proficient { color: #0b524c; }
.badge-metric     { color: #14532d; }

/* Language dots read as filled vs hollow, not gold vs grey. */
.dot { background: #fff; border: 1pt solid #000; }
.dot.on { background: #000; }

.cv-footer { color: #444; border-top-color: #8a8a8a; }
"""


def _skill_badge(cls: str, text: str) -> str:
    mapping = {
        "expert": "badge-expert",
        "advanced": "badge-advanced",
        "proficient": "badge-proficient",
        "metric": "badge-metric",
    }
    css = mapping.get(cls, "badge-proficient")
    return f'<span class="skill-badge {css}">{text}</span>'


def _skill_rows(rows: list) -> str:
    return "".join(
        f'<div class="skill-row">'
        f'<span class="skill-name">{r["name"]}</span>'
        f'{_skill_badge(r["cls"], r["level"])}'
        f'</div>'
        for r in rows
    )


def _dot_row(filled: int, total: int) -> str:
    dots = "".join(
        f'<div class="dot{"  on" if i < filled else ""}"></div>'
        for i in range(total)
    )
    return f'<div class="lang-dots">{dots}</div>'


def _photo_data_uri(path: pathlib.Path) -> str:
    """Return the portrait as a data URI (set_content has no file base URL)."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def render_html(data: dict, lang: str = "en", generic: bool = False) -> str:
    d = data
    contact = d["contact"]
    extra_css = _PRINT_CSS
    loc = LOCALE[lang]
    sec = loc["sections"]
    _css = _CSS_TEMPLATE.replace("{zoom}", str(loc["zoom"]))

    # ── Header ──
    # The site uses the ticker symbol "ARUN.MUR" as a design motif; the CV
    # must stand alone, so use the real name from .full-name instead.
    full_parts = [p.strip() for p in d["full_name"].split("·")]
    person_name = full_parts[0] or "Arun Murugan"
    # generic drops the role line under the name and in the footer, for
    # applications outside reconciliation where naming a sought role narrows
    # the CV. Everything else — summary, tags, experience — is unchanged.
    role = "" if generic else (full_parts[1] if len(full_parts) > 1 else "")

    name_words = person_name.upper().split()
    if len(name_words) > 1:
        name_html = (
            f'{" ".join(name_words[:-1])} '
            f'<span class="cv-name-accent">{name_words[-1]}</span>'
        )
    else:
        name_html = person_name.upper()

    tag_html = " ".join(
        f'<span class="tag{"  hi" if t["highlight"] else ""}">{t["text"]}</span>'
        for t in d["tags"]
    )

    # Chromium only emits a PDF link annotation for a real <a href>, so the
    # linkable values are anchored.
    def _link(href: str, label: str) -> str:
        return f'<a class="cv-link" href="{href}">{label}</a>'

    def _tel_href(value: str) -> str:
        """tel: URI for a displayed number.

        The site writes the number the way a German reader expects to read it —
        "+49 (0)1603488387 (WhatsApp)" — but the trunk zero is an alternative to
        the country code, not part of it, and dialling it would fail. Drop the
        parenthesised parts, then keep the digits.
        """
        bare = re.sub(r"\(.*?\)", "", value)
        return "tel:+" + "".join(c for c in bare if c.isdigit())

    contact_parts = []
    if email := contact.get("email"):
        contact_parts.append(f"{_contact_icon('mail')}{_link(f'mailto:{email}', email)}")
    if li := contact.get("linkedin"):
        contact_parts.append(f"{_contact_icon('linkedin')}{_link(f'https://{li}', li)}")
    if site := contact.get("website"):
        contact_parts.append(f"{_contact_icon('website')}{_link(f'https://{site}', site)}")
    if ph := contact.get("phone"):
        contact_parts.append(f"{_contact_icon('phone')}{_link(_tel_href(ph), ph)}")
    if addr := contact.get("address", loc["address"]):
        contact_parts.append(f"{_contact_icon('address')}<span>{addr}</span>")

    # Each part is its own flex item so a long value (the site URL) wraps as a
    # whole instead of splitting mid-token at a hyphen. The flex gap separates
    # them; a literal "|" would strand itself at the end of a wrapped line.
    contact_html = "".join(
        f'<span class="cv-contact-item">{p}</span>' for p in contact_parts
    )

    photo_uri = _photo_data_uri(REPO_ROOT / "arun.jpg")
    photo_html = (
        f'<div class="cv-photo"><img src="{photo_uri}" alt="Arun Murugan"></div>'
        if photo_uri
        else ""
    )

    # ── Stats ──
    stats_html = "".join(
        f'<div class="stat-box">'
        f'<div class="stat-val">{s["value"]}</div>'
        f'<div class="stat-lbl">{s["label"]}</div>'
        f'<div class="stat-sub">{s["sub"]}</div>'
        f'</div>'
        for s in d["stats"]
    )

    # ── Summary ──
    summary_html = f'<div class="summary">{d["description"]}</div>'

    # ── Skills ──
    core_rows = _skill_rows(d["skills"]["core"])
    tools_rows = _skill_rows(d["skills"]["tools"])

    # ── Experience ──
    exp_items = []
    for exp in d["experience"]:
        bullets = "".join(f"<li>{b}</li>" for b in exp["bullets"])
        exp_items.append(f"""
        <div class="exp-item">
          <div class="exp-top">
            <span class="exp-company">{exp["company"]}</span>
            <span class="exp-period">{exp["period"]}</span>
          </div>
          <div class="exp-role">{exp["role"]}</div>
          <ul class="exp-bullets">{bullets}</ul>
        </div>""")
    exp_html = "".join(exp_items)

    # ── Education ──
    edu_items = []
    for i, edu in enumerate(d["education"]):
        if i > 0:
            edu_items.append('<div class="edu-divider"></div>')
        edu_items.append(f"""
        <div class="edu-item">
          <div class="edu-degree">{edu["degree"]}</div>
          <div class="edu-school">{edu["school"]}</div>
          <div class="edu-meta">{edu["meta"]}</div>
        </div>""")
    edu_html = "".join(edu_items)

    # ── Languages ──
    # The embedded IBM Plex subsets are latin-only and carry no U+2192, so the
    # site's "A1→A2" falls back to a system font in the PDF and prints at the
    # wrong weight. "»" is in the subset and reads the same.
    lang_rows = "".join(
        f'<div class="lang-row">'
        f'<span class="lang-name">{lang["name"]}</span>'
        f'{_dot_row(lang["filled"], lang["total"])}'
        f'<span class="lang-level">{lang["level"].replace("→", " » ")}</span>'
        f'</div>'
        for lang in d["languages"]
    )

    # With no role there is nothing to put on the title line, so it is dropped
    # rather than falling back to .full-name, which carries the role itself.
    title_html = f'<div class="cv-title">{role}</div>' if role else ""

    footer_ident = f"{person_name} &nbsp;·&nbsp; {role}" if role else person_name
    footer_html = "".join(
        f'<div class="cv-footer-line">{line}</div>' for line in loc["footer"]
    )

    return f"""<!DOCTYPE html>
<html lang="{loc["doc_lang"]}">
<head>
  <meta charset="UTF-8">
  <title>{person_name} — {loc["doc_title"]}</title>
  <style>{_font_css()}{_css}{extra_css}</style>
</head>
<body>

  <!-- Header -->
  <div class="cv-header">
    <div class="cv-header-main">
      <div class="cv-name">{name_html}</div>
      {title_html}
      <div class="cv-tags">{tag_html}</div>
      <div class="cv-contact">{contact_html}</div>
    </div>
    {photo_html}
  </div>

  <!-- Single-column layout: profile → experience → skills → education → languages -->
  <div class="cv-body">

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">01</span>
        <span class="sec-title">{sec["profile"]}</span>
        <div class="sec-rule"></div>
      </div>
      {summary_html}
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">02</span>
        <span class="sec-title">{sec["experience"]}</span>
        <div class="sec-rule"></div>
      </div>
      {exp_html}
    </div>

    <div class="section section-skills">
      <div class="sec-hdr">
        <span class="sec-num">03</span>
        <span class="sec-title">{sec["skills"]}</span>
        <div class="sec-rule"></div>
      </div>
      <div class="skills-grid">
        <div class="skill-panel">{core_rows}</div>
        <div class="skill-panel">{tools_rows}</div>
      </div>
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">04</span>
        <span class="sec-title">{sec["education"]}</span>
        <div class="sec-rule"></div>
      </div>
      {edu_html}
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">05</span>
        <span class="sec-title">{sec["languages"]}</span>
        <div class="sec-rule"></div>
      </div>
      {lang_rows}
    </div>

  </div>

  <div class="cv-footer">
    <div class="cv-footer-line">{footer_ident}</div>
    {footer_html}
  </div>

</body>
</html>"""


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

async def _render_pdf(html: str, output: pathlib.Path) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        await page.evaluate("document.fonts.ready")
        await page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
        )
        await browser.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PDF CV from index.html")
    parser.add_argument(
        "--lang",
        choices=sorted(LOCALE),
        default="en",
        help="CV language: en reads index.html, de reads de/index.html (default: en)",
    )
    parser.add_argument(
        "--source",
        help="Path to the source page (default: derived from --lang)",
    )
    parser.add_argument(
        "--output",
        help="Output PDF path (default: derived from --lang)",
    )
    parser.add_argument(
        "--generic",
        action="store_true",
        help="Drop the sought-role line under the name and in the footer",
    )
    args = parser.parse_args()

    defaults = {
        ("en", False): (REPO_ROOT / "index.html", REPO_ROOT / "Arun-Murugan-CV-print.pdf"),
        ("en", True): (REPO_ROOT / "index.html", REPO_ROOT / "Arun-Murugan-CV-generic-print.pdf"),
        ("de", False): (REPO_ROOT / "de" / "index.html", REPO_ROOT / "Arun-Murugan-Lebenslauf-print.pdf"),
        ("de", True): (REPO_ROOT / "de" / "index.html", REPO_ROOT / "Arun-Murugan-Lebenslauf-generisch.pdf"),
    }
    default_source, default_output = defaults[(args.lang, args.generic)]

    source = pathlib.Path(args.source) if args.source else default_source
    output = pathlib.Path(args.output) if args.output else default_output

    if not source.exists():
        sys.exit(f"Error: source file not found: {source}")

    html_source = source.read_text(encoding="utf-8")
    data = extract(html_source)
    cv_html = render_html(data, args.lang, generic=args.generic)

    print(f"Rendering PDF → {output}")
    asyncio.run(_render_pdf(cv_html, output))
    print("Done.")


if __name__ == "__main__":
    main()
