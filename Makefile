.PHONY: dev dev-windows test quality wheel linux install-linux windows images-sync images-verify

ifeq ($(OS),Windows_NT)
dev:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/development/dev-windows.ps1
else
dev:
	bash scripts/development/dev.sh
endif

dev-windows:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/development/dev-windows.ps1

test:
	mvn -f backend/pom.xml $(if $(MAVEN_REPO),-Dmaven.repo.local=$(MAVEN_REPO),) verify
	python3 -m unittest discover -s desktop/tests

quality:
	bash scripts/quality/quality.sh

wheel:
	bash scripts/build/build-wheel.sh

linux:
	bash scripts/build/build-linux.sh

install-linux:
	bash scripts/install/install-linux.sh

windows:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build/build-windows.ps1

images-sync:
	python3 scripts/images/import_local_recipe_images.py
	python3 scripts/images/verify_recipe_images.py

images-verify:
	python3 scripts/images/verify_recipe_images.py
