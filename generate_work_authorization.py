#!/usr/bin/env python3
"""
Work-authorization overview for arun-website.

Renders a one-page A4 enclosure (not the cover letter itself) that explains
the Chancenkarte (§20a AufenthG) to a reader who may only know the "20 hours
per week" headline: the search-phase hour limits, the two-week full-time
trial-employment option, and the conversion path to unrestricted full-time
work once an offer is signed. Same visual language as the cover letter, and
meant to travel with it as an enclosure.

Requirements:
    pip install -r requirements-cv.txt
    playwright install chromium

Usage:
    python generate_work_authorization.py [--lang en|de] [--output PDF]
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit(
        "Error: playwright not installed. Run:\n"
        "  pip install -r requirements-cv.txt\n"
        "  playwright install chromium"
    )

from generate_cover_letter import CITY, EMAIL, NAME, PHONE, STREET, WEBSITE, _tel_href
from generate_cv import _font_css

REPO_ROOT = pathlib.Path(__file__).parent

LOCALE = {
    "en": {
        "doc_lang": "en",
        "doc_title": "Work authorization",
        "kicker": "Chancenkarte · §20a AufenthG",
        "subtitle": "How the 20-hour limit and the two-week trial actually work",
        "intro": (
            "The Chancenkarte is often read as capping Arun at 20 hours of work per week. "
            "That limit — and the two-week trial-employment option below — applies only to the "
            "active job-search phase. Once an offer is signed, the permit is converted to "
            "unrestricted full-time work authorization. No employer sponsorship or visa "
            "procedure is required at any point."
        ),
        "stages_label": "The path to full-time employment",
        "stages": [
            {
                "num": "1",
                "title": "Job search — now",
                "detail": "Chancenkarte active. Up to 20h/week paid side work, plus a two-week "
                "full-time trial (see below), repeatable.",
            },
            {
                "num": "2",
                "title": "Offer signed",
                "detail": "Employer and Arun file a permit conversion at the local "
                "Ausländerbehörde — a paperwork step, not a new visa application.",
            },
            {
                "num": "3",
                "title": "Permit converted",
                "detail": "Typically 1–3 months. No employer sponsorship: the qualification "
                "check already happened for the Chancenkarte.",
            },
            {
                "num": "4",
                "title": "Full-time employment",
                "detail": "Unrestricted work hours. Standard employment relationship from this "
                "point on.",
            },
        ],
        "trial_label": "Risk-free before you commit",
        "trial_title": "Two-week full-time trial employment (Probebeschäftigung)",
        "trial_text": (
            "The Chancenkarte itself already permits a full-time trial period of up to two "
            "weeks per instance — repeatable or run in parallel with other steps. No permit "
            "change, no paperwork, no cost: an employer can simply try Arun full-time before "
            "deciding to hire."
        ),
        "sources_label": "Sources",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "Make it in Germany — Employing Chancenkarte holders",
                "https://www.make-it-in-germany.com/en/companies/entry/employing-chancenkarte-holders",
            ),
        ],
        "footnote": "Prepared for information only, based on §20a AufenthG as of August 2026 — not legal advice.",
    },
    "de": {
        "doc_lang": "de",
        "doc_title": "Arbeitserlaubnis",
        "kicker": "Chancenkarte · §20a AufenthG",
        "subtitle": "Wie die 20-Stunden-Grenze und die zweiwöchige Probebeschäftigung wirklich funktionieren",
        "intro": (
            "Die Chancenkarte wird oft so gelesen, als läge die Arbeitszeit dauerhaft bei "
            "20 Stunden pro Woche. Diese Grenze — und die unten beschriebene zweiwöchige "
            "Probebeschäftigung — gilt jedoch nur während der aktiven Jobsuche. Mit "
            "unterschriebenem Arbeitsvertrag wird der Aufenthaltstitel in eine uneingeschränkte "
            "Arbeitserlaubnis in Vollzeit umgewandelt. Weder Sponsorship noch ein Visumverfahren "
            "sind dafür erforderlich."
        ),
        "stages_label": "Der Weg zur Vollzeitbeschäftigung",
        "stages": [
            {
                "num": "1",
                "title": "Jobsuche — jetzt",
                "detail": "Chancenkarte aktiv. Bis zu 20 Std./Woche Nebenbeschäftigung, "
                "zusätzlich zweiwöchige Probebeschäftigung in Vollzeit (siehe unten), "
                "wiederholbar.",
            },
            {
                "num": "2",
                "title": "Arbeitsvertrag unterschrieben",
                "detail": "Arbeitgeber und Arun beantragen die Umwandlung des Aufenthaltstitels "
                "bei der zuständigen Ausländerbehörde — ein Verwaltungsschritt, kein neues "
                "Visumverfahren.",
            },
            {
                "num": "3",
                "title": "Titel umgewandelt",
                "detail": "In der Regel 1–3 Monate. Keine Sponsorship nötig: die "
                "Qualifikationsprüfung ist bereits für die Chancenkarte erfolgt.",
            },
            {
                "num": "4",
                "title": "Vollzeitbeschäftigung",
                "detail": "Uneingeschränkte Arbeitszeit. Ab hier ein normales "
                "Beschäftigungsverhältnis.",
            },
        ],
        "trial_label": "Risikofrei vor der Entscheidung",
        "trial_title": "Zweiwöchige Probebeschäftigung in Vollzeit",
        "trial_text": (
            "Die Chancenkarte erlaubt bereits jetzt eine Probebeschäftigung in Vollzeit von bis "
            "zu zwei Wochen je Einsatz — wiederholbar oder parallel zu anderen Schritten "
            "möglich. Ohne Titeländerung, ohne Verwaltungsaufwand, ohne Kosten: ein Arbeitgeber "
            "kann Arun einfach in Vollzeit testen, bevor er sich für eine Einstellung "
            "entscheidet."
        ),
        "sources_label": "Quellen",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "Make it in Germany — Beschäftigung von Chancenkarte-Inhabern",
                "https://www.make-it-in-germany.com/de/unternehmen/einreise/beschaeftigung-chancenkarte-inhabern",
            ),
        ],
        "footnote": "Nur zur Information erstellt, Stand §20a AufenthG August 2026 — keine Rechtsberatung.",
    },
}


_CSS = """
@page { size: A4; margin: 18mm 20mm 15mm 20mm; }

:root {
  --gold: #6b4e00;
  --muted: #3a3a3a;
  --border: #8a8a8a;
  --text: #000;
  --rule: #000;
  --mono: 'IBM Plex Mono', 'Courier New', Courier, monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
  font-size: 10pt;
  color: var(--text);
  line-height: 1.6;
  background: #fff;
}

/* ── Header: same name/contact motif as the CV and cover letter ── */
.wa-header {
  border-bottom: 2px solid var(--rule);
  padding-bottom: 9pt;
}

.wa-name {
  font-family: var(--mono);
  font-size: 15pt;
  font-weight: 600;
  letter-spacing: 2px;
  line-height: 1.1;
  text-transform: uppercase;
}

.wa-name-accent { color: var(--gold); }

.wa-contact {
  font-family: var(--mono);
  display: flex;
  flex-wrap: wrap;
  gap: 3pt 13pt;
  margin-top: 6pt;
  font-size: 8pt;
  color: var(--muted);
}

.wa-link { color: inherit; text-decoration: none; }

/* ── Title block ── */
.wa-title-block { margin-top: 16pt; }

.wa-kicker {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 4pt;
}

.wa-doc-title {
  font-size: 17pt;
  font-weight: bold;
}

.wa-subtitle {
  margin-top: 3pt;
  font-size: 10.5pt;
  color: var(--muted);
}

/* ── Intro ── */
.wa-intro {
  margin-top: 12pt;
  text-align: justify;
  font-size: 9.5pt;
}

/* ── Stages ── */
.wa-stages-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-top: 16pt;
  margin-bottom: 6pt;
}

.wa-stage-row {
  display: flex;
  align-items: stretch;
  gap: 5pt;
}

.wa-stage {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border);
  padding: 7pt 8pt;
}

.wa-stage-num {
  font-family: var(--mono);
  font-size: 7pt;
  color: var(--gold);
  letter-spacing: 1px;
}

.wa-stage-title {
  font-weight: 600;
  font-size: 9pt;
  margin-top: 2pt;
}

.wa-stage-detail {
  font-size: 7.3pt;
  color: var(--muted);
  margin-top: 4pt;
  line-height: 1.45;
}

.wa-stage-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 10pt;
  flex: none;
  font-size: 13pt;
  color: var(--gold);
}

/* ── Trial callout ── */
.wa-trial {
  margin-top: 16pt;
  border-left: 3pt solid var(--gold);
  background: rgba(107,78,0,0.06);
  padding: 10pt 12pt;
}

.wa-trial-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
}

.wa-trial-title {
  font-weight: 600;
  font-size: 10pt;
  margin-top: 3pt;
}

.wa-trial-text {
  font-size: 9pt;
  color: var(--muted);
  margin-top: 4pt;
  line-height: 1.5;
  text-align: justify;
}

/* ── Sources ── */
.wa-sources {
  margin-top: 16pt;
  padding-top: 8pt;
  border-top: 1px solid var(--border);
}

.wa-sources-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 4pt;
}

.wa-source-line {
  font-family: var(--mono);
  font-size: 8pt;
  color: var(--muted);
  line-height: 1.7;
}

/* ── Footnote ── */
.wa-footnote {
  font-family: var(--mono);
  margin-top: 14pt;
  padding-top: 7pt;
  border-top: 1px solid var(--border);
  font-size: 7pt;
  color: #444;
  text-align: center;
  letter-spacing: 0.5px;
}
"""


def render_html(lang: str) -> str:
    loc = LOCALE[lang]

    words = NAME.upper().split()
    name_html = (
        f'{" ".join(words[:-1])} <span class="wa-name-accent">{words[-1]}</span>'
        if len(words) > 1
        else NAME.upper()
    )

    def _link(href: str, label: str) -> str:
        return f'<a class="wa-link" href="{href}">{label}</a>'

    contact_parts = [
        f"addr {STREET}, {CITY}",
        f"mail {_link(f'mailto:{EMAIL}', EMAIL)}",
        f"tel {_link(_tel_href(PHONE), PHONE)}",
        f"www {_link(f'https://{WEBSITE}', WEBSITE)}",
    ]
    contact_html = "".join(
        f'<span class="wa-contact-item">{p}</span>' for p in contact_parts
    )

    stage_html_parts = []
    for i, stage in enumerate(loc["stages"]):
        stage_html_parts.append(
            f'<div class="wa-stage">'
            f'<div class="wa-stage-num">{stage["num"]}</div>'
            f'<div class="wa-stage-title">{stage["title"]}</div>'
            f'<div class="wa-stage-detail">{stage["detail"]}</div>'
            f"</div>"
        )
        if i < len(loc["stages"]) - 1:
            stage_html_parts.append('<div class="wa-stage-arrow">&#8594;</div>')
    stages_html = "".join(stage_html_parts)

    sources_html = "".join(
        f'<div class="wa-source-line">{label} — {_link(url, url)}</div>'
        for label, url in loc["sources"]
    )

    return f"""<!DOCTYPE html>
<html lang="{loc["doc_lang"]}">
<head>
  <meta charset="UTF-8">
  <title>{NAME} — {loc["doc_title"]}</title>
  <style>{_font_css()}{_CSS}</style>
</head>
<body>

  <div class="wa-header">
    <div class="wa-name">{name_html}</div>
    <div class="wa-contact">{contact_html}</div>
  </div>

  <div class="wa-title-block">
    <div class="wa-kicker">{loc["kicker"]}</div>
    <div class="wa-doc-title">{loc["doc_title"]}</div>
    <div class="wa-subtitle">{loc["subtitle"]}</div>
  </div>

  <p class="wa-intro">{loc["intro"]}</p>

  <div class="wa-stages-label">{loc["stages_label"]}</div>
  <div class="wa-stage-row">{stages_html}</div>

  <div class="wa-trial">
    <div class="wa-trial-label">{loc["trial_label"]}</div>
    <div class="wa-trial-title">{loc["trial_title"]}</div>
    <div class="wa-trial-text">{loc["trial_text"]}</div>
  </div>

  <div class="wa-sources">
    <div class="wa-sources-label">{loc["sources_label"]}</div>
    {sources_html}
  </div>

  <div class="wa-footnote">{loc["footnote"]}</div>

</body>
</html>"""


async def _render_pdf(html: str, output: pathlib.Path) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        await page.evaluate("document.fonts.ready")
        await page.pdf(path=str(output), format="A4", print_background=True)
        await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the work-authorization overview PDF")
    parser.add_argument("--lang", choices=sorted(LOCALE), default="en")
    parser.add_argument("--output", help="Output PDF path (default: derived from --lang)")
    args = parser.parse_args()

    defaults = {
        "en": REPO_ROOT / "Arun-Murugan-Work-Authorization.pdf",
        "de": REPO_ROOT / "Arun-Murugan-Arbeitserlaubnis.pdf",
    }
    output = pathlib.Path(args.output) if args.output else defaults[args.lang]

    html = render_html(args.lang)

    print(f"Rendering PDF → {output}")
    asyncio.run(_render_pdf(html, output))
    print("Done.")


if __name__ == "__main__":
    main()
