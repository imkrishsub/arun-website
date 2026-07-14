#!/usr/bin/env python3
"""
Cover letter generation for arun-website.

Renders a one-page A4 cover letter (Anschreiben) in the same visual language as
the CV — IBM Plex Mono name/contact header, gold rule, uppercase section label —
but the letter is a standalone document: it is not published on the site and
reads none of its content from index.html.

The default is a speculative application (Initiativbewerbung) addressed to a
hiring team. Pass --company/--recipient/--role to target a named vacancy.

Requirements:
    pip install -r requirements-cv.txt
    playwright install chromium

Usage:
    python generate_cover_letter.py [--lang en|de] [--company NAME]
        [--recipient LINES] [--role TITLE] [--date TEXT] [--output PDF]
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import pathlib
import re
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    sys.exit(
        "Error: playwright not installed. Run:\n"
        "  pip install -r requirements-cv.txt\n"
        "  playwright install chromium"
    )

from generate_cv import _font_css, _photo_data_uri

REPO_ROOT = pathlib.Path(__file__).parent


def _tel_href(value: str) -> str:
    """tel: URI for a displayed number.

    The number is written the way a German reader expects to read it —
    "+49 (0)1737950101" — but the trunk zero is an alternative to the country
    code, not part of it, and dialling it would fail. Drop the parenthesised
    parts, then keep the digits.
    """
    bare = re.sub(r"\(.*?\)", "", value)
    return "tel:+" + "".join(c for c in bare if c.isdigit())


NAME = "Arun Murugan"
STREET = "Heinrich-Imbusch-Str. 12"
CITY = "52499 Baesweiler"
EMAIL = "arunmuruganmail@gmail.com"
PHONE = "+49 (0)1737950101"
WEBSITE = "arun-murugan-six.vercel.app"

# German month names — strftime("%B") is locale-dependent and would print
# English months on a machine without de_DE installed.
_DE_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _default_date(lang: str) -> str:
    today = dt.date.today()
    if lang == "de":
        return f"Baesweiler, {today.day}. {_DE_MONTHS[today.month - 1]} {today.year}"
    return f"Baesweiler, {today:%d %B %Y}".replace(" 0", " ")


LOCALE = {
    "en": {
        "doc_lang": "en",
        "doc_title": "Cover letter",
        "recipient_label": "To",
        "default_recipient": ["Hiring Team"],
        "subject_label": "Subject",
        "subject": "Application for an open position",
        "subject_role": "Application for the position of {role}",
        "salutation_generic": "Dear Hiring Team,",
        "salutation_named": "Dear {recipient},",
        "body": [
            "Thank you for the opportunity to submit my details. I am writing to express my "
            "interest in joining your organisation in a role within management or back-office "
            "operations and related support functions. I bring hands-on experience in "
            "reconciliation and financial operations, and I am motivated to contribute to a "
            "professional team in Germany.",
            "I currently live in Baesweiler and hold a Chancenkarte (§20a), which gives me full "
            "work authorisation in Germany — no employer sponsorship or visa procedure is "
            "required, so I am able to start without administrative delay.",
            "Alongside my work, I am progressing steadily with my German. I am preparing for "
            "telc A2 later this year and intend to continue to B1, and I am committed to "
            "ongoing learning and development on the job.",
            "I have attached my CV together with the requested personal and educational "
            "documents. I would be glad to discuss how I can support your team and contribute "
            "to your operational goals, and I am available for an interview at any time.",
        ],
        "closing": "Thank you for your time and consideration.",
        "signoff": "Kind regards,",
        "enclosures_label": "Enclosures",
        "enclosures": "CV · Certificates · Chancenkarte · Personal documents",
        "footer": [
            "Chancenkarte holder — right to work in Germany, no sponsorship required",
            "Willing to relocate anywhere in Germany",
        ],
    },
    "de": {
        "doc_lang": "de",
        "doc_title": "Anschreiben",
        "recipient_label": "An",
        "default_recipient": ["Personalabteilung"],
        "subject_label": "Betreff",
        "subject": "Initiativbewerbung",
        "subject_role": "Bewerbung als {role}",
        "salutation_generic": "Sehr geehrte Damen und Herren,",
        # Gendered adjective ending: resolved from the Frau/Herr prefix in
        # _salutation(), because "Sehr geehrte Herr Müller" is wrong German and
        # the "/r" workaround reads as a form letter.
        "salutation_named": "Sehr geehrte{ending} {recipient},",
        "body": [
            "vielen Dank für die Möglichkeit, Ihnen meine Unterlagen zu übersenden. Hiermit "
            "bewerbe ich mich um eine Position im Bereich Management, Back-Office bzw. "
            "kaufmännische Sachbearbeitung. Ich bringe praktische Erfahrung in der "
            "Kontenabstimmung und im Financial-Operations-Umfeld mit und möchte mich gerne in "
            "ein professionelles Team in Deutschland einbringen.",
            "Ich wohne derzeit in Baesweiler und besitze eine Chancenkarte (§20a). Damit liegt "
            "eine uneingeschränkte Arbeitserlaubnis vor — es ist weder eine Sponsorship noch ein "
            "Visumverfahren durch den Arbeitgeber erforderlich, sodass ich ohne "
            "Verwaltungsaufwand kurzfristig beginnen kann.",
            "Parallel dazu baue ich meine Deutschkenntnisse kontinuierlich aus: Für dieses Jahr "
            "ist die telc-Prüfung A2 geplant, anschließend strebe ich B1 an. Weiterbildung und "
            "Einarbeitung sind für mich selbstverständlich.",
            "Meinen Lebenslauf sowie die angeforderten persönlichen Unterlagen und Zeugnisse "
            "habe ich beigefügt. Über die Einladung zu einem persönlichen Gespräch würde ich "
            "mich sehr freuen — Termine kann ich jederzeit wahrnehmen.",
        ],
        "closing": "Vielen Dank für Ihre Zeit und Ihr Interesse.",
        "signoff": "Mit freundlichen Grüßen",
        "enclosures_label": "Anlagen",
        "enclosures": "Lebenslauf · Zeugnisse · Chancenkarte · Persönliche Unterlagen",
        "footer": [
            "Chancenkarte — Arbeitserlaubnis für Deutschland vorhanden, keine Sponsorship nötig",
            "Umzug innerhalb Deutschlands jederzeit möglich",
        ],
    },
}


# ---------------------------------------------------------------------------
# Styles — the CV palette and type scale, laid out as a letter (DIN 5008-ish:
# sender block, recipient block, date right, bold subject, body, signature).
# ---------------------------------------------------------------------------

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

/* ── Header: same name/contact motif as the CV ── */
.lt-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14pt;
  border-bottom: 2px solid var(--rule);
  padding-bottom: 9pt;
}

.lt-header-main { flex: 1; min-width: 0; }

.lt-name {
  font-family: var(--mono);
  font-size: 19pt;
  font-weight: 600;
  letter-spacing: 2px;
  line-height: 1.1;
  text-transform: uppercase;
}

.lt-name-accent { color: var(--gold); }

.lt-contact {
  font-family: var(--mono);
  display: flex;
  flex-wrap: wrap;
  gap: 3pt 13pt;
  margin-top: 7pt;
  font-size: 8pt;
  color: var(--muted);
}

.lt-contact-item { white-space: nowrap; }
.lt-link { color: inherit; text-decoration: none; }

.lt-photo img {
  width: 26mm;
  height: 33mm;
  object-fit: cover;
  object-position: top;
  border: 1.5pt solid var(--rule);
  display: block;
}

/* ── Recipient + date ── */
.lt-meta {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20pt;
  margin-top: 18pt;
}

.lt-recipient { font-size: 10pt; line-height: 1.5; }

.lt-block-label {
  font-family: var(--mono);
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 3pt;
}

.lt-date {
  font-family: var(--mono);
  font-size: 8.5pt;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
  padding-top: 11pt;
}

/* ── Subject ── */
.lt-subject {
  margin-top: 20pt;
  padding-bottom: 5pt;
  border-bottom: 1px solid var(--border);
}

.lt-subject-text {
  font-size: 10.5pt;
  font-weight: bold;
  letter-spacing: 0.2px;
}

/* ── Body ── */
.lt-body { margin-top: 14pt; }

.lt-salutation { margin-bottom: 9pt; }

.lt-body p { margin-bottom: 9pt; text-align: justify; }

.lt-closing { margin-top: 12pt; }

/* ── Signature ── */
.lt-sign { margin-top: 16pt; }

.lt-sign-name {
  font-family: var(--mono);
  font-weight: 600;
  font-size: 10pt;
  letter-spacing: 1px;
  margin-top: 16pt;
  padding-top: 4pt;
  border-top: 1px solid var(--border);
  display: inline-block;
  min-width: 150pt;
}

/* ── Enclosures ── */
.lt-enclosures {
  margin-top: 16pt;
  font-family: var(--mono);
  font-size: 8pt;
  color: var(--muted);
}

.lt-enclosures-label {
  font-size: 7pt;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 2pt;
}

/* ── Footer: identical strapline to the CV ── */
.lt-footer {
  font-family: var(--mono);
  margin-top: 22pt;
  padding-top: 7pt;
  border-top: 1px solid var(--border);
  font-size: 7.5pt;
  color: #444;
  text-align: center;
  letter-spacing: 1px;
}

.lt-footer-line { margin-bottom: 2.5pt; }
.lt-footer-line:last-child { margin-bottom: 0; }
"""


def _salutation(loc: dict, lang: str, name: str) -> str:
    """Salutation for a named contact, falling back to the generic one.

    --name is expected to carry the German honorific ("Frau Schmidt",
    "Herr Müller"), which also fixes the adjective ending. Anything else — an
    English "Ms Schmidt", a bare surname — takes the feminine-plural "geehrte",
    which is the safe default when the form of address is unknown.
    """
    if not name:
        return loc["salutation_generic"]
    if lang != "de":
        return loc["salutation_named"].format(recipient=name)
    ending = "r" if name.strip().lower().startswith("herr ") else ""
    return loc["salutation_named"].format(ending=ending, recipient=name)


def render_html(
    lang: str,
    recipient: list[str],
    role: str = "",
    salutation_name: str = "",
    date: str = "",
) -> str:
    loc = LOCALE[lang]

    words = NAME.upper().split()
    name_html = (
        f'{" ".join(words[:-1])} <span class="lt-name-accent">{words[-1]}</span>'
        if len(words) > 1
        else NAME.upper()
    )

    def _link(href: str, label: str) -> str:
        return f'<a class="lt-link" href="{href}">{label}</a>'

    # Same lowercase word markers as the CV: the embedded Plex subsets are
    # latin-only, so ✉ ☎ ⌂ would fall back to a system font.
    contact_parts = [
        f"addr {STREET}, {CITY}",
        f"mail {_link(f'mailto:{EMAIL}', EMAIL)}",
        f"tel {_link(_tel_href(PHONE), PHONE)}",
        f"www {_link(f'https://{WEBSITE}', WEBSITE)}",
    ]
    contact_html = "".join(
        f'<span class="lt-contact-item">{p}</span>' for p in contact_parts
    )

    photo_uri = _photo_data_uri(REPO_ROOT / "arun.jpg")
    photo_html = (
        f'<div class="lt-photo"><img src="{photo_uri}" alt="{NAME}"></div>'
        if photo_uri
        else ""
    )

    recipient_html = "<br>".join(recipient)

    subject = (
        loc["subject_role"].format(role=role) if role else loc["subject"]
    )
    salutation = _salutation(loc, lang, salutation_name)

    body_html = "".join(f"<p>{p}</p>" for p in loc["body"])
    footer_html = "".join(
        f'<div class="lt-footer-line">{line}</div>' for line in loc["footer"]
    )

    return f"""<!DOCTYPE html>
<html lang="{loc["doc_lang"]}">
<head>
  <meta charset="UTF-8">
  <title>{NAME} — {loc["doc_title"]}</title>
  <style>{_font_css()}{_CSS}</style>
</head>
<body>

  <div class="lt-header">
    <div class="lt-header-main">
      <div class="lt-name">{name_html}</div>
      <div class="lt-contact">{contact_html}</div>
    </div>
    {photo_html}
  </div>

  <div class="lt-meta">
    <div class="lt-recipient">
      <div class="lt-block-label">{loc["recipient_label"]}</div>
      {recipient_html}
    </div>
    <div class="lt-date">{date or _default_date(lang)}</div>
  </div>

  <div class="lt-subject">
    <div class="lt-block-label">{loc["subject_label"]}</div>
    <div class="lt-subject-text">{subject}</div>
  </div>

  <div class="lt-body">
    <div class="lt-salutation">{salutation}</div>
    {body_html}
    <div class="lt-closing">{loc["closing"]}</div>
  </div>

  <div class="lt-sign">
    <div>{loc["signoff"]}</div>
    <div class="lt-sign-name">{NAME}</div>
  </div>

  <div class="lt-enclosures">
    <div class="lt-enclosures-label">{loc["enclosures_label"]}</div>
    {loc["enclosures"]}
  </div>

  <div class="lt-footer">
    {footer_html}
  </div>

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
    parser = argparse.ArgumentParser(description="Generate a PDF cover letter")
    parser.add_argument("--lang", choices=sorted(LOCALE), default="en")
    parser.add_argument(
        "--company",
        default="",
        help="Company name for the recipient block (default: none — speculative letter)",
    )
    parser.add_argument(
        "--recipient",
        default="",
        help="Extra recipient lines, '|'-separated (e.g. 'Musterstr. 1|50667 Köln')",
    )
    parser.add_argument("--role", default="", help="Job title, used in the subject line")
    parser.add_argument(
        "--name",
        default="",
        help="Contact person, used in the salutation instead of the generic one",
    )
    parser.add_argument("--date", default="", help="Override the letter date")
    parser.add_argument("--output", help="Output PDF path (default: derived from --lang)")
    args = parser.parse_args()

    loc = LOCALE[args.lang]
    lines = [args.company] if args.company else []
    lines += loc["default_recipient"] if not args.name else [args.name]
    if args.recipient:
        lines += [p.strip() for p in args.recipient.split("|") if p.strip()]

    defaults = {
        "en": REPO_ROOT / "Arun-Murugan-Cover-Letter.pdf",
        "de": REPO_ROOT / "Arun-Murugan-Anschreiben.pdf",
    }
    output = pathlib.Path(args.output) if args.output else defaults[args.lang]

    html = render_html(
        args.lang,
        recipient=lines,
        role=args.role,
        salutation_name=args.name,
        date=args.date,
    )

    print(f"Rendering PDF → {output}")
    asyncio.run(_render_pdf(html, output))
    print("Done.")


if __name__ == "__main__":
    main()
