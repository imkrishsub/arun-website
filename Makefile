.PHONY: cv cv-de cv-de-generic cv-all letter letter-de letter-all desktop-build desktop-icons desktop-install desktop-quit

cv:
	python3 generate_cv.py --lang en

cv-de:
	python3 generate_cv.py --lang de

cv-de-generic:
	python3 generate_cv.py --lang de --generic

cv-all: cv cv-de cv-de-generic

# Speculative cover letters. For a named vacancy pass the details through, e.g.
#   python3 generate_cover_letter.py --lang de --company 'Muster GmbH' \
#       --recipient 'Musterstr. 1|50667 Köln' --role 'Sachbearbeiter Back-Office'
letter:
	python3 generate_cover_letter.py --lang en

letter-de:
	python3 generate_cover_letter.py --lang de

letter-all: letter letter-de

desktop-build:
	./scripts/desktop-build.sh

desktop-icons:
	APP_NAME='Arun.mur' APP_SLUG='arun-mur' ./scripts/desktop-icons.sh

desktop-install:
	./scripts/desktop-install.sh

desktop-quit:
	./scripts/desktop-quit.sh
