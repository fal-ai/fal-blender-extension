# Blender extension: download wheels for every platform on one machine, sync manifest, package.
# https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html

# Python versions handled in build_wheels.sh (3.11 for Blender 4.x, 3.13 for Blender 5.x)
DIST_DIR       ?= dist
WHEEL_DIR      ?= wheels

# Non-login shells (e.g. `make`) do not expand the interactive `blender` alias; prefer a concrete path on macOS.
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
else
BLENDER ?= blender
endif

.PHONY: help wheels sync-manifest all clean package package-split

help:
	@echo "Targets:"
	@echo "  make wheels         — pip-download pure + platform wheels into $(WHEEL_DIR)/"
	@echo "  make sync-manifest  — blender_manifest.toml from template + ./$(WHEEL_DIR)/*.whl"
	@echo "  make all            — wheels + sync-manifest"
	@echo "  make package        — one .zip with all wheels (requires $(BLENDER) on PATH)"
	@echo "  make package-split  — per-platform .zips (requires $(BLENDER); smaller uploads)"
	@echo "  make clean          — remove $(WHEEL_DIR)/ and $(DIST_DIR)/"
	@echo ""
	@echo "Variables: PYTHON_VERSION=$(PYTHON_VERSION) BLENDER=$(BLENDER)"
	@echo "Set PYTHON_VERSION to match Blender's embedded Python (e.g. 3.11 vs 3.13)."
	@echo "WHEEL_FRESH=1 make wheels  — clear $(WHEEL_DIR)/* before downloading"

wheels:
	WHEEL_DIR=$(WHEEL_DIR) PYTHON_VERSION=$(PYTHON_VERSION) bash scripts/build_wheels.sh

sync-manifest:
	python3 scripts/sync_manifest_wheels.py

all: wheels sync-manifest

clean:
	rm -rf $(WHEEL_DIR) $(DIST_DIR)

package: all
	mkdir -p $(DIST_DIR)
	$(BLENDER) --background --command extension build \
		--source-dir . --output-dir $(DIST_DIR)

package-split: all
	mkdir -p $(DIST_DIR)
	$(BLENDER) --background --command extension build --split-platforms \
		--source-dir . --output-dir $(DIST_DIR)
