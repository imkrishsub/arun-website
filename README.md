# arun-website

Arun Murugan's personal site (`index.html`, German at `de/index.html`), plus the
document generators that turn it into print-ready PDFs.

## Setup

Python 3.9+ and a Chromium for Playwright. The same environment covers every
generator below.

```bash
python3 -m pip install -r requirements-cv.txt
python3 -m playwright install chromium
```

The commands work the same on macOS, Linux and Windows — use `python` instead of
`python3` on Windows, and run the `python3 generate_*.py` commands directly if
you have no `make` (Windows has none by default).

> **Build the PDFs on macOS.** The pipeline runs anywhere, but on Linux the
> rendered PDF comes out with a corrupted text layer — the pages look right and
> the extracted text is garbage, which means an ATS scanner reads nothing. That
> is why there is no CI workflow for it.

## CV / Lebenslauf

`generate_cv.py` reads a source page and renders a two-page A4 PDF that keeps the
site's aesthetic (IBM Plex Mono, gold accents) on a white background.

| Command | Source | Output |
| --- | --- | --- |
| `make cv` | `index.html` | `Arun-Murugan-CV-print.pdf` |
| `make cv-de` | `de/index.html` | `Arun-Murugan-Lebenslauf-print.pdf` |
| `make cv-de-generic` | `de/index.html` | `Arun-Murugan-Lebenslauf-generisch.pdf` |
| `make cv-all` | both | all three |

`--generic` drops the sought-role line under the name and in the footer, for
applications outside reconciliation.

The CV content lives in the HTML pages — edit `index.html` / `de/index.html` and
re-run the build. Nothing is duplicated in the Python.

## Cover letter / Anschreiben

`generate_cover_letter.py` renders a one-page A4 letter in the same visual
language as the CV, but it is a standalone document: the text lives in the
script's `LOCALE` table and nothing is read from the site.

| Command | Output |
| --- | --- |
| `make letter` | `Arun-Murugan-Cover-Letter.pdf` |
| `make letter-de` | `Arun-Murugan-Anschreiben.pdf` |
| `make letter-all` | both |

The default is a speculative application (Initiativbewerbung). For a named
vacancy, pass the details:

```bash
python3 generate_cover_letter.py --lang de \
    --company 'Muster GmbH' \
    --recipient 'Musterstr. 1|50667 Köln' \
    --role 'Sachbearbeiter Back-Office' \
    --name 'Frau Schmidt'
```

- `--recipient` takes `|`-separated address lines.
- `--role` replaces the generic subject line.
- `--name` replaces the generic salutation. In German, give the honorific
  (`Frau Schmidt`, `Herr Müller`) — the adjective ending follows from it.
- `--photo` adds the portrait to the header. Off by default: in a German
  Bewerbung the photo belongs on the Lebenslauf (or a Deckblatt), not on the
  Anschreiben.
- `--date` overrides the date, `--output` the file path.

## Work authorization overview

`generate_work_authorization.py` renders a one-page A4 enclosure — sent
alongside the CV and cover letter — that explains the Chancenkarte (§20a
AufenthG) for a reader who only knows the "20 hours per week" headline: the
search-phase hour limit, the two-week full-time trial-employment option, and
the conversion path to unrestricted full-time work, which a concrete job
offer is enough to start — no signed contract required yet.

| Command | Output |
| --- | --- |
| `make authorization` | `Arun-Murugan-Work-Authorization.pdf` |
| `make authorization-de` | `Arun-Murugan-Arbeitserlaubnis.pdf` |
| `make authorization-all` | both |

Like the cover letter, the text lives in the script's `LOCALE` table.
`--output` overrides the file path.

The overview names and links the **Erklärung zum Beschäftigungsverhältnis
(EzB)** — the standard Bundesagentur für Arbeit form used for every non-EU
hire in Germany, and the actual document an employer files to give proof of
a "concrete job offer" (§18 Abs. 2 AufenthG) without needing a signed
contract yet. A blank copy is checked into the repo as
`Erklaerung-zum-Beschaeftigungsverhaeltnis-EzB.pdf`, downloadable from the
site's Work authorization section and listed as a cover-letter enclosure.
It is the official form as published at arbeitsagentur.de (version EzB
02/2024 at the time it was added) — re-download it from the source link in
the overview's Sources section if a newer version is needed.

## Desktop launcher

`make desktop-build`, `desktop-icons`, `desktop-install`, `desktop-quit` build a
macOS `.app` that opens the site locally. See `docs/desktop-launcher.md`.
