#!/usr/bin/env python3
"""
CV generation pipeline for arun-website.

Reads index.html, extracts structured CV data, and renders a print-optimised
A4 PDF using Playwright. The PDF keeps the site's financial-terminal aesthetic
(Courier New, gold accents, uppercase section labels) on a white background
suitable for recruiters and ATS scanners.

Requirements:
    pip install -r requirements-cv.txt
    playwright install chromium

Usage:
    python generate_cv.py [--source index.html] [--output Arun-Murugan-CV-print.pdf]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import pathlib
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
        if "email" in lbl:
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
        if "core" in title:
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
        if "academic" in _text(panel.select_one(".panel-title")).lower():
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


_CSS = """
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

.cv-contact-item { white-space: nowrap; }

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
.exp-item { margin-bottom: 11pt; }
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

.exp-bullets li::before {
  content: "▸";
  color: var(--gold);
  position: absolute;
  left: 0;
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


def render_html(data: dict) -> str:
    d = data
    contact = d["contact"]
    extra_css = _PRINT_CSS

    # ── Header ──
    # The site uses the ticker symbol "ARUN.MUR" as a design motif; the CV
    # must stand alone, so use the real name from .full-name instead.
    full_parts = [p.strip() for p in d["full_name"].split("·")]
    person_name = full_parts[0] or "Arun Murugan"
    role = full_parts[1] if len(full_parts) > 1 else ""

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

    contact_parts = []
    if email := contact.get("email"):
        contact_parts.append(f"&#9993; {email}")
    if li := contact.get("linkedin"):
        contact_parts.append(f"in {li}")
    if site := contact.get("website"):
        contact_parts.append(f"www {site}")
    if ph := contact.get("phone"):
        contact_parts.append(f"&#9742; {ph}")
    if addr := contact.get("address"):
        contact_parts.append(f"&#8962; {addr}")

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
        if i > 0 and i < len(d["education"]) - 1:
            edu_items.append('<div class="edu-divider"></div>')
        edu_items.append(f"""
        <div class="edu-item">
          <div class="edu-degree">{edu["degree"]}</div>
          <div class="edu-school">{edu["school"]}</div>
          <div class="edu-meta">{edu["meta"]}</div>
        </div>""")
    edu_html = "".join(edu_items)

    # ── Languages ──
    lang_rows = "".join(
        f'<div class="lang-row">'
        f'<span class="lang-name">{lang["name"]}</span>'
        f'{_dot_row(lang["filled"], lang["total"])}'
        f'<span class="lang-level">{lang["level"]}</span>'
        f'</div>'
        for lang in d["languages"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{person_name} — CV</title>
  <style>{_font_css()}{_CSS}{extra_css}</style>
</head>
<body>

  <!-- Header -->
  <div class="cv-header">
    <div class="cv-header-main">
      <div class="cv-name">{name_html}</div>
      <div class="cv-title">{role or d["full_name"]}</div>
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
        <span class="sec-title">Professional profile</span>
        <div class="sec-rule"></div>
      </div>
      {summary_html}
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">02</span>
        <span class="sec-title">Performance history</span>
        <div class="sec-rule"></div>
      </div>
      {exp_html}
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">03</span>
        <span class="sec-title">Skills</span>
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
        <span class="sec-title">Education &amp; awards</span>
        <div class="sec-rule"></div>
      </div>
      {edu_html}
    </div>

    <div class="section">
      <div class="sec-hdr">
        <span class="sec-num">05</span>
        <span class="sec-title">Languages</span>
        <div class="sec-rule"></div>
      </div>
      {lang_rows}
    </div>

  </div>

  <div class="cv-footer">
    {person_name} &nbsp;·&nbsp; {role or "Reconciliation Analyst / Financial Operations"} &nbsp;·&nbsp;
    Chancenkarte holder — right to work in Germany, no sponsorship required &nbsp;·&nbsp;
    Willing to relocate anywhere in Germany
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
        "--source",
        default=str(REPO_ROOT / "index.html"),
        help="Path to index.html (default: index.html next to this script)",
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "Arun-Murugan-CV-print.pdf"),
        help="Output PDF path (default: Arun-Murugan-CV-print.pdf)",
    )
    args = parser.parse_args()

    source = pathlib.Path(args.source)
    output = pathlib.Path(args.output)

    if not source.exists():
        sys.exit(f"Error: source file not found: {source}")

    html_source = source.read_text(encoding="utf-8")
    data = extract(html_source)
    cv_html = render_html(data)

    print(f"Rendering PDF → {output}")
    asyncio.run(_render_pdf(cv_html, output))
    print("Done.")


if __name__ == "__main__":
    main()
