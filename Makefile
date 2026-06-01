.PHONY: desktop-build desktop-icons desktop-install desktop-quit

desktop-build:
	./scripts/desktop-build.sh

desktop-icons:
	APP_NAME='Arun.mur' APP_SLUG='arun-mur' ./scripts/desktop-icons.sh

desktop-install:
	./scripts/desktop-install.sh

desktop-quit:
	./scripts/desktop-quit.sh
