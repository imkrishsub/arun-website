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
    python generate_cv.py [--source index.html] [--output Arun-Murugan-CV.pdf]
"""

from __future__ import annotations

import argparse
import asyncio
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
        elif "phone" in lbl:
            contact["phone"] = val

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

_CSS = """
@page { size: A4; margin: 13mm 15mm 13mm 15mm; }

:root {
  --gold: #b08000;
  --gold-bg: rgba(176,128,0,0.10);
  --muted: #555;
  --border: #d4d4d4;
  --text: #1a1a1a;
  --rule: #c8a000;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Courier New', Courier, monospace;
  font-size: 9pt;
  color: var(--text);
  line-height: 1.5;
  background: #fff;
}

/* ── Header ── */
.cv-header {
  border-bottom: 2px solid var(--rule);
  padding-bottom: 9pt;
  margin-bottom: 11pt;
}

.cv-name {
  font-size: 21pt;
  font-weight: bold;
  letter-spacing: 4px;
  line-height: 1.1;
}

.cv-name-accent { color: var(--gold); }

.cv-title {
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
  display: flex;
  gap: 13pt;
  margin-top: 6pt;
  font-size: 8.5pt;
  color: var(--muted);
}

/* ── Two-column body ── */
.cv-body {
  display: grid;
  grid-template-columns: 42% 1fr;
  gap: 15pt;
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
  font-size: 7.5pt;
  font-weight: bold;
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

.exp-period { font-size: 8pt; color: var(--muted); }

.exp-role {
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

.lang-level { font-size: 8pt; color: var(--muted); margin-left: auto; }

/* ── Footer ── */
.cv-footer {
  margin-top: 12pt;
  padding-top: 7pt;
  border-top: 1px solid var(--border);
  font-size: 7.5pt;
  color: #aaa;
  text-align: center;
  letter-spacing: 1px;
}
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


def render_html(data: dict) -> str:
    d = data
    contact = d["contact"]

    # ── Header ──
    raw_name = d["name"]
    if "." in raw_name:
        prefix, suffix = raw_name.split(".", 1)
        name_html = f'{prefix}<span class="cv-name-accent">.{suffix}</span>'
    else:
        name_html = raw_name

    tag_html = " ".join(
        f'<span class="tag{"  hi" if t["highlight"] else ""}">{t["text"]}</span>'
        for t in d["tags"]
    )

    contact_parts = []
    if email := contact.get("email"):
        contact_parts.append(f"&#9993; {email}")
    if li := contact.get("linkedin"):
        contact_parts.append(f"in {li}")
    if ph := contact.get("phone"):
        contact_parts.append(f"&#9742; {ph}")

    contact_html = " &nbsp;|&nbsp; ".join(contact_parts)

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
  <style>{_CSS}</style>
</head>
<body>

  <!-- Header -->
  <div class="cv-header">
    <div class="cv-name">{name_html}</div>
    <div class="cv-title">{d["full_name"]}</div>
    <div class="cv-tags">{tag_html}</div>
    <div class="cv-contact">{contact_html}</div>
  </div>

  <!-- Sidebar layout: left = skills + edu + languages, right = summary + experience -->
  <div class="cv-body">

    <!-- Left sidebar -->
    <div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">01</span>
          <span class="sec-title">Core competencies</span>
          <div class="sec-rule"></div>
        </div>
        <div class="skill-panel">{core_rows}</div>
      </div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">02</span>
          <span class="sec-title">Tools &amp; soft skills</span>
          <div class="sec-rule"></div>
        </div>
        <div class="skill-panel">{tools_rows}</div>
      </div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">03</span>
          <span class="sec-title">Education &amp; awards</span>
          <div class="sec-rule"></div>
        </div>
        {edu_html}
      </div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">04</span>
          <span class="sec-title">Languages</span>
          <div class="sec-rule"></div>
        </div>
        {lang_rows}
      </div>

    </div>

    <!-- Main column -->
    <div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">05</span>
          <span class="sec-title">Professional profile</span>
          <div class="sec-rule"></div>
        </div>
        {summary_html}
      </div>

      <div class="section">
        <div class="sec-hdr">
          <span class="sec-num">06</span>
          <span class="sec-title">Performance history</span>
          <div class="sec-rule"></div>
        </div>
        {exp_html}
      </div>

    </div>

  </div>

  <div class="cv-footer">
    ARUN.MUR &nbsp;·&nbsp; Financial Analyst &nbsp;·&nbsp;
    Chancenkarte holder — right to work in Germany, no sponsorship required
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
        default=str(REPO_ROOT / "Arun-Murugan-CV.pdf"),
        help="Output PDF path (default: Arun-Murugan-CV.pdf)",
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
