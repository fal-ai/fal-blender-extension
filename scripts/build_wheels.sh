#!/usr/bin/env bash
# Download fal-client and dependencies as wheels for bundling.
# Run from the repo root: bash scripts/build_wheels.sh
# Cross-platform downloads use pip's --platform (see Blender manual: Python Wheels).
# Downloads wheels for BOTH Python 3.11 (Blender 4.x) and Python 3.13 (Blender 5.x).
set -euo pipefail

WHEEL_DIR="${WHEEL_DIR:-wheels}"
mkdir -p "$WHEEL_DIR"
# For a clean download directory: `make clean` (removes wheels/) or WHEEL_FRESH=1.
if [ "${WHEEL_FRESH:-0}" != 0 ]; then
    rm -rf "${WHEEL_DIR:?}/"*
fi

# Python versions to support:
# - 3.11 for Blender 4.2 - 4.x
# - 3.13 for Blender 5.0+
PYTHON_VERSIONS=("3.11" "3.13")

# Pip platform tags for binary wheels.
# manylinux_2_28 matches the Blender docs example; PyPI may emit a compound manylinux tag on the filename.
PLATFORMS=(
    "manylinux_2_28_x86_64"
    "macosx_11_0_arm64"
    "macosx_11_0_x86_64"
    "win_amd64"
    "win_arm64"
)

# Universal wheels (py3-none-any) only need to be downloaded once.
echo "=== Downloading universal wheels (py3-none-any) ==="
# Omit --platform so pip still prefers py3-none-any for these. Do not list packages here that
# only publish per-platform wheels (e.g. websockets) — those go in the platform loop below.
pip download \
    --dest "$WHEEL_DIR" \
    --only-binary :all: \
    --python-version 3.11 \
    --no-deps \
    fal-client httpx httpx-sse httpcore certifi idna sniffio anyio h11

echo ""
echo "=== Downloading platform-specific wheels (msgpack, Pillow, websockets) ==="
for pyver in "${PYTHON_VERSIONS[@]}"; do
    echo "--- Python $pyver ---"
    for plat in "${PLATFORMS[@]}"; do
        echo "  → $plat (cp${pyver//./})"
        pip download \
            --dest "$WHEEL_DIR" \
            --only-binary :all: \
            --platform "$plat" \
            --python-version "$pyver" \
            --no-deps \
            msgpack Pillow websockets || echo "    (skipped $plat for Python $pyver)"
    done
    echo ""
done

echo ""
echo "=== Wheels downloaded ==="
ls -la "$WHEEL_DIR"/*.whl 2>/dev/null || echo "(no wheels found)"

echo ""
echo "=== Generating manifest wheel entries ==="
echo "# Run: make sync-manifest  (uses blender_manifest.toml.template)"
echo 'wheels = ['
for whl in "$WHEEL_DIR"/*.whl; do
    [ -f "$whl" ] && echo "  \"./$whl\","
done
echo ']'
