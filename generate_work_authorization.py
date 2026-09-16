#!/usr/bin/env python3
"""
Work-authorization overview for arun-website.

Renders a one-page A4 enclosure (not the cover letter itself) that answers the
question employers actually ask: what does hiring a Chancenkarte holder cost?
It corrects the common assumption that a non-EU hire carries a EUR 48,000
salary requirement (that is the EU Blue Card threshold, a different route) and
that the employer must sponsor a visa (Germany has no sponsorship fee), then
explains the conversion path to unrestricted full-time work and the two-week
full-time trial. Same visual language as the cover letter, and meant to travel
with it as an enclosure.

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
        "doc_title": "What hiring me costs you",
        "kicker": "Chancenkarte · §20a AufenthG",
        "subtitle": "Nothing beyond the salary — no sponsorship, no fee, no visa procedure",
        "intro": (
            "Hiring someone from outside the EU is widely assumed to be expensive and slow. In "
            "my case it is neither. I already live in {city} and already hold a permit "
            "that lets me work, so there is no visa procedure, no sponsorship and no fee — Germany "
            "levies no employer charge of the kind the UK and the US do."
        ),
        "myths_label": "The four things employers usually assume",
        "myths": [
            {
                "myth": "\u201cI would have to pay you €48,000.\u201d",
                "fact": "That is the minimum salary for the <strong>EU Blue Card</strong> — a "
                "different permit, which I am not applying for. It does not apply to me. You pay "
                "the market rate for the role, exactly as you would any other candidate.",
            },
            {
                "myth": "\u201cI would have to sponsor your visa.\u201d",
                "fact": "Germany has no employer sponsorship system and charges no sponsorship "
                "fee. Your cost here is <strong>€0</strong>. This is the point most often "
                "confused with UK sponsor licences or the US H-1B.",
            },
            {
                "myth": "\u201cThere would be a lot of paperwork.\u201d",
                "fact": "One standard form — the <strong>EzB</strong>, used for every non-EU hire "
                "in Germany, blank copy enclosed. Role, hours, pay, start date. Nothing bespoke "
                "and nothing drafted by you.",
            },
            {
                "myth": "\u201cYou could not start until it is approved.\u201d",
                "fact": "I can start <strong>immediately</strong> — up to 20 hours a week right "
                "now, plus a two-week full-time trial, and I keep working throughout the "
                "conversion.",
            },
        ],
        "stages_label": "How I get to full-time",
        "stages": [
            {
                "num": "1",
                "title": "Job search — where I am now",
                "detail": "Permit active. Up to 20h/week now, plus the full-time trial below.",
            },
            {
                "num": "2",
                "title": "You fill in one standard form",
                "detail": "The EzB: role, hours, pay, start date. No signed contract needed yet.",
            },
            {
                "num": "3",
                "title": "Permit converted",
                "detail": "Usually weeks, rarely over three months — and I keep working throughout.",
            },
            {
                "num": "4",
                "title": "Full-time, for good",
                "detail": "Unrestricted hours — an entirely standard employment relationship.",
            },
        ],
        "trial_label": "Try me before you commit",
        "trial_title": "A risk-free, two-week full-time trial (Probebeschäftigung)",
        "trial_text": (
            "My permit already allows full-time work for up to two weeks at a stretch, as often "
            "as useful. No permit change and no paperwork on your side — just normal pay for "
            "those two weeks (a genuine employment relationship under §611a BGB, not unpaid "
            "work), and a direct way to see how I work before committing."
        ),
        "sources_label": "Sources",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "§ 18b Abs. 2 AufenthG — EU Blue Card, the route the €48,000 figure belongs to",
                "https://www.gesetze-im-internet.de/aufenthg_2004/__18b.html",
            ),
            (
                "§ 19c Abs. 2 AufenthG and § 6 BeschV — employment on the basis of professional experience",
                "https://www.gesetze-im-internet.de/beschv_2013/__6.html",
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
        "footnote": "Enclosed with my application, current as of September 2026 (§§18, 18b, 19c, 20a AufenthG, §6 BeschV, §611a BGB) — for orientation, not legal advice.",
    },
    "de": {
        "doc_lang": "de",
        "doc_title": "Was meine Einstellung Sie kostet",
        "kicker": "Chancenkarte · §20a AufenthG",
        "subtitle": "Nichts außer dem Gehalt — kein Sponsoring, keine Gebühr, kein Visumverfahren",
        "intro": (
            "Eine Einstellung aus einem Drittstaat gilt als teuer und langwierig. In meinem Fall "
            "ist sie weder das eine noch das andere. Ich lebe bereits in {city} und "
            "besitze einen Aufenthaltstitel, der mir das Arbeiten erlaubt — kein Visumverfahren, kein "
            "Sponsoring, keine Gebühr. Eine Arbeitgeberabgabe wie im Vereinigten Königreich oder "
            "in den USA gibt es hier nicht."
        ),
        "myths_label": "Die vier häufigsten Annahmen",
        "myths": [
            {
                "myth": "\u201eIch müsste Ihnen 48.000 € zahlen.\u201c",
                "fact": "Das ist die Mindestvergütung für die <strong>Blaue Karte EU</strong> — "
                "ein anderer Aufenthaltstitel, den ich nicht beantrage. Für mich gilt sie nicht. "
                "Sie zahlen das marktübliche Gehalt der Stelle, wie bei jeder anderen "
                "Bewerberin und jedem anderen Bewerber.",
            },
            {
                "myth": "\u201eIch müsste Ihr Visum sponsern.\u201c",
                "fact": "Deutschland kennt kein Arbeitgeber-Sponsoring und erhebt keine solche "
                "Gebühr. Ihre Kosten: <strong>0 €</strong>. Dieser Punkt wird meist mit der "
                "britischen Sponsor Licence oder dem US-Visum H-1B verwechselt.",
            },
            {
                "myth": "\u201eDas wäre ein großer Verwaltungsaufwand.\u201c",
                "fact": "Ein einziges Standardformular — die <strong>EzB</strong>, bei jeder "
                "Drittstaats-Einstellung üblich; Blankoexemplar liegt bei. Rolle, Stunden, "
                "Gehalt, Starttermin. Nichts, das Sie selbst aufsetzen müssten.",
            },
            {
                "myth": "\u201eSie könnten erst nach der Genehmigung anfangen.\u201c",
                "fact": "Ich kann <strong>sofort</strong> anfangen — bis zu 20 Stunden pro Woche, "
                "dazu die zweiwöchige Probebeschäftigung in Vollzeit, und ich arbeite während "
                "der Umwandlung durchgehend weiter.",
            },
        ],
        "stages_label": "Mein Weg zur Vollzeitbeschäftigung",
        "stages": [
            {
                "num": "1",
                "title": "Jobsuche — mein aktueller Stand",
                "detail": "Titel aktiv. Jetzt bis zu 20 Std./Woche, dazu die Probebeschäftigung unten.",
            },
            {
                "num": "2",
                "title": "Sie füllen ein Standardformular aus",
                "detail": "Die EzB: Rolle, Stunden, Gehalt, Starttermin. Noch kein Vertrag nötig.",
            },
            {
                "num": "3",
                "title": "Titel umgewandelt",
                "detail": "Meist Wochen, selten über drei Monate — ich arbeite durchgehend weiter.",
            },
            {
                "num": "4",
                "title": "Dauerhaft Vollzeit",
                "detail": "Uneingeschränkte Arbeitszeit — ein ganz normales Arbeitsverhältnis.",
            },
        ],
        "trial_label": "Testen Sie mich, bevor Sie sich entscheiden",
        "trial_title": "Risikofreie Probebeschäftigung in Vollzeit (zwei Wochen)",
        "trial_text": (
            "Mein Titel erlaubt bereits jetzt bis zu zwei Wochen Vollzeit am Stück, so oft es "
            "hilfreich ist. Ohne Änderung des Aufenthaltstitels, ohne Aufwand auf Ihrer Seite — "
            "nur die normale Vergütung für diese zwei Wochen (ein echtes Arbeitsverhältnis nach "
            "§611a BGB, keine unbezahlte Arbeit)."
        ),
        "sources_label": "Quellen",
        "sources": [
            ("§ 20a AufenthG — Chancenkarte", "https://www.gesetze-im-internet.de/aufenthg_2004/__20a.html"),
            (
                "§ 18b Abs. 2 AufenthG — Blaue Karte EU, auf die sich die Zahl 48.000 € bezieht",
                "https://www.gesetze-im-internet.de/aufenthg_2004/__18b.html",
            ),
            (
                "§ 19c Abs. 2 AufenthG und § 6 BeschV — Beschäftigung aufgrund berufspraktischer Erfahrung",
                "https://www.gesetze-im-internet.de/beschv_2013/__6.html",
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
        "footnote": "Anlage zu meiner Bewerbung, Stand September 2026 (§§18, 18b, 19c, 20a AufenthG, §6 BeschV, §611a BGB) — zur Orientierung, keine Rechtsberatung.",
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
  line-height: 1.5;
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
.wa-title-block { margin-top: 12pt; }

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
  margin-top: 7pt;
  text-align: justify;
  font-size: 9pt;
}

/* ── Myth vs fact ── */
.wa-myths-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-top: 10pt;
  margin-bottom: 5pt;
}

.wa-myth {
  display: flex;
  gap: 8pt;
  align-items: baseline;
  border-top: 1px solid var(--border);
  padding: 3.4pt 0;
}

.wa-myth:last-child { border-bottom: 1px solid var(--border); }

.wa-myth-claim {
  flex: 0 0 33%;
  font-size: 8.3pt;
  font-style: italic;
  color: var(--muted);
  line-height: 1.3;
}

.wa-myth-fact {
  flex: 1;
  font-size: 8.3pt;
  line-height: 1.35;
}

.wa-myth-fact strong { color: var(--gold); }

/* ── Stages ── */
.wa-stages-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-top: 10pt;
  margin-bottom: 5pt;
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
  padding: 6pt 8pt;
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
  font-size: 7pt;
  color: var(--muted);
  margin-top: 4pt;
  line-height: 1.35;
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
  margin-top: 8pt;
  border-left: 3pt solid var(--gold);
  background: rgba(107,78,0,0.06);
  padding: 7pt 11pt;
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
  font-size: 8.5pt;
  color: var(--muted);
  margin-top: 4pt;
  line-height: 1.4;
  text-align: justify;
}

/* ── Sources ── */
.wa-sources {
  margin-top: 6pt;
  padding-top: 6pt;
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
  font-size: 7pt;
  color: var(--muted);
  line-height: 1.3;
  padding-left: 11pt;
  position: relative;
  margin-bottom: 1.6pt;
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
  margin-top: 4pt;
  padding-top: 5pt;
  border-top: 1px solid var(--border);
  font-size: 7pt;
  color: #444;
  text-align: center;
  letter-spacing: 0.5px;
}
"""


def render_html(lang: str, city: str = CITY) -> str:
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
        f"addr {', '.join(p for p in (STREET, city) if p)}",
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

    myths_html = "".join(
        f'<div class="wa-myth">'
        f'<div class="wa-myth-claim">{m["myth"]}</div>'
        f'<div class="wa-myth-fact">{m["fact"]}</div>'
        f"</div>"
        for m in loc["myths"]
    )

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

  <p class="wa-intro">{loc["intro"].format(city=city)}</p>

  <div class="wa-myths-label">{loc["myths_label"]}</div>
  {myths_html}

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
    parser.add_argument(
        "--city",
        default=CITY,
        help=f"City in the header and intro, for a vacancy elsewhere (default: {CITY})",
    )
    parser.add_argument("--output", help="Output PDF path (default: derived from --lang)")
    args = parser.parse_args()

    defaults = {
        "en": REPO_ROOT / "Arun-Murugan-Work-Authorization.pdf",
        "de": REPO_ROOT / "Arun-Murugan-Arbeitserlaubnis.pdf",
    }
    output = pathlib.Path(args.output) if args.output else defaults[args.lang]

    html = render_html(args.lang, args.city)

    print(f"Rendering PDF → {output}")
    asyncio.run(_render_pdf(html, output))
    print("Done.")


if __name__ == "__main__":
    main()
