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
        "subtitle": "What the 20-hour limit really means for me — and the trial that removes the risk",
        "intro": (
            "You may have seen that my Chancenkarte limits me to 20 hours of work a week and "
            "wondered whether I could take on a full-time role. That limit — and the two-week "
            "trial option below — only applies while I'm still job-hunting. Under German law "
            "(§18 Abs. 2 AufenthG), a concrete job offer is enough to start converting my permit "
            "to full, unrestricted work authorization — I don't need a signed contract in hand "
            "yet. No sponsorship or visa procedure needed from you at any point."
        ),
        "stages_label": "How I get to full-time",
        "stages": [
            {
                "num": "1",
                "title": "Job search — where I am now",
                "detail": "My Chancenkarte is active. I can work up to 20h/week, plus take a "
                "two-week full-time trial (see below) as often as it's useful.",
            },
            {
                "num": "2",
                "title": "You fill in one standard form",
                "detail": "Just the basics — role, hours, pay, start date — on the EzB, the "
                "standard form for every non-EU hire (blank copy enclosed). No signed contract "
                "yet.",
            },
            {
                "num": "3",
                "title": "Permit converted",
                "detail": "Often just a few weeks, rarely more than three months — and I keep "
                "working the entire time: up to 20h/week, or full-time via the trial below.",
            },
            {
                "num": "4",
                "title": "Full-time, for good",
                "detail": "Unrestricted hours, from here on a completely standard employment "
                "relationship.",
            },
        ],
        "trial_label": "Try me before you commit",
        "trial_title": "A risk-free, two-week full-time trial (Probebeschäftigung)",
        "trial_text": (
            "My Chancenkarte already lets me work full-time for up to two weeks at a stretch, "
            "as many times as useful, alongside other steps. No change to my permit, no "
            "paperwork, no cost to you — just a straightforward way to see how I work before "
            "deciding to hire me."
        ),
        "sources_label": "Sources",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "§ 18 Abs. 2 AufenthG — concrete job offer requirement",
                "https://www.gesetze-im-internet.de/aufenthg_2004/__18.html",
            ),
            (
                "Erklärung zum Beschäftigungsverhältnis (EzB), Bundesagentur für Arbeit",
                "https://www.arbeitsagentur.de/datei/erklaerung-zum-beschaeftigungsverhaeltnis_ba047549.pdf",
            ),
            (
                "Make it in Germany — Employing Chancenkarte holders",
                "https://www.make-it-in-germany.com/en/companies/entry/employing-chancenkarte-holders",
            ),
        ],
        "footnote": "Prepared by me for your information, based on §§18, 20a AufenthG as of August 2026 — not legal advice.",
    },
    "de": {
        "doc_lang": "de",
        "doc_title": "Arbeitserlaubnis",
        "kicker": "Chancenkarte · §20a AufenthG",
        "subtitle": "Was die 20-Stunden-Grenze für mich wirklich bedeutet — und wie die Probebeschäftigung das Risiko nimmt",
        "intro": (
            "Vielleicht ist Ihnen aufgefallen, dass meine Chancenkarte mich auf 20 Stunden pro "
            "Woche beschränkt, und Sie haben sich gefragt, ob ich überhaupt Vollzeit arbeiten "
            "kann. Diese Grenze — und die unten beschriebene Probebeschäftigung — gilt nur, "
            "solange ich noch auf Jobsuche bin. Nach deutschem Recht (§18 Abs. 2 AufenthG) "
            "genügt ein konkretes Arbeitsplatzangebot, um die Umwandlung meines Aufenthaltstitels "
            "in eine uneingeschränkte Vollzeit-Arbeitserlaubnis anzustoßen — ein unterschriebener "
            "Arbeitsvertrag ist dafür noch nicht nötig. Weder Sponsorship noch ein Visumverfahren "
            "sind von Ihrer Seite erforderlich."
        ),
        "stages_label": "Mein Weg zur Vollzeitbeschäftigung",
        "stages": [
            {
                "num": "1",
                "title": "Jobsuche — mein aktueller Stand",
                "detail": "Meine Chancenkarte ist aktiv. Ich kann bis zu 20 Std./Woche arbeiten "
                "und zusätzlich eine Probebeschäftigung in Vollzeit von bis zu zwei Wochen "
                "antreten (siehe unten) — so oft es hilfreich ist.",
            },
            {
                "num": "2",
                "title": "Sie füllen ein Standardformular aus",
                "detail": "Nur die Basics — Rolle, Stunden, Gehalt, Starttermin — auf der EzB, "
                "dem Standardformular für jede Drittstaats-Einstellung (liegt bei). Noch kein "
                "unterschriebener Vertrag nötig.",
            },
            {
                "num": "3",
                "title": "Titel umgewandelt",
                "detail": "Oft nur wenige Wochen, selten mehr als drei Monate — und ich arbeite "
                "die ganze Zeit weiter: bis zu 20 Std./Woche oder in Vollzeit über die "
                "Probebeschäftigung unten.",
            },
            {
                "num": "4",
                "title": "Dauerhaft Vollzeit",
                "detail": "Uneingeschränkte Arbeitszeit — ab hier ein ganz normales "
                "Beschäftigungsverhältnis.",
            },
        ],
        "trial_label": "Testen Sie mich, bevor Sie sich entscheiden",
        "trial_title": "Risikofreie Probebeschäftigung in Vollzeit (zwei Wochen)",
        "trial_text": (
            "Meine Chancenkarte erlaubt es mir bereits jetzt, bis zu zwei Wochen am Stück in "
            "Vollzeit zu arbeiten — so oft es hilfreich ist, zusätzlich zu anderen Schritten. "
            "Ohne Änderung meines Aufenthaltstitels, ohne Verwaltungsaufwand und ohne Kosten für "
            "Sie — einfach eine unkomplizierte Möglichkeit zu sehen, wie ich arbeite, bevor Sie "
            "sich für eine Einstellung entscheiden."
        ),
        "sources_label": "Quellen",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "§ 18 Abs. 2 AufenthG — Erfordernis eines konkreten Arbeitsplatzangebots",
                "https://www.gesetze-im-internet.de/aufenthg_2004/__18.html",
            ),
            (
                "Erklärung zum Beschäftigungsverhältnis (EzB), Bundesagentur für Arbeit",
                "https://www.arbeitsagentur.de/datei/erklaerung-zum-beschaeftigungsverhaeltnis_ba047549.pdf",
            ),
            (
                "Make it in Germany — Beschäftigung von Chancenkarte-Inhabern",
                "https://www.make-it-in-germany.com/de/unternehmen/einreise/beschaeftigung-chancenkarte-inhabern",
            ),
        ],
        "footnote": "Von mir zur Information erstellt, Stand §§18, 20a AufenthG August 2026 — keine Rechtsberatung.",
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
  margin-top: 12pt;
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
  margin-top: 12pt;
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
  margin-top: 10pt;
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

.wa-sources-list {
  list-style: none;
}

.wa-source-line {
  font-family: var(--mono);
  font-size: 8pt;
  color: var(--muted);
  line-height: 1.6;
  padding-left: 11pt;
  position: relative;
  margin-bottom: 3pt;
}

.wa-source-line:last-child { margin-bottom: 0; }

.wa-source-line::before {
  content: "–";
  color: var(--gold);
  position: absolute;
  left: 0;
}

/* ── Footnote ── */
.wa-footnote {
  font-family: var(--mono);
  margin-top: 8pt;
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
        f'<li class="wa-source-line">{label} — {_link(url, url)}</li>'
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
    <ul class="wa-sources-list">{sources_html}</ul>
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
