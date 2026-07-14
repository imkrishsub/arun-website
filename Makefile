.PHONY: cv cv-de cv-de-generic cv-all desktop-build desktop-icons desktop-install desktop-quit

cv:
	python3 generate_cv.py --lang en

cv-de:
	python3 generate_cv.py --lang de

cv-de-generic:
	python3 generate_cv.py --lang de --generic

cv-all: cv cv-de cv-de-generic

desktop-build:
	./scripts/desktop-build.sh

desktop-icons:
	APP_NAME='Arun.mur' APP_SLUG='arun-mur' ./scripts/desktop-icons.sh

desktop-install:
	./scripts/desktop-install.sh

desktop-quit:
	./scripts/desktop-quit.sh
