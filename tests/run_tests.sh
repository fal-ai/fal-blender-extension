#!/bin/bash
# Run all fal.ai Blender extension tests
#
# Usage:
#   ./tests/run_tests.sh              # Run all tests
#   ./tests/run_tests.sh unit         # Run unit tests only (no Blender needed)
#   ./tests/run_tests.sh integration  # Run Blender integration tests only

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

run_unit_tests() {
    echo "=== Running Unit Tests (pytest) ==="
    # Run from temp dir to avoid bpy import issues
    cp tests/test_models.py /tmp/test_models_fal.py
    python3 -m pytest /tmp/test_models_fal.py -v
    rm /tmp/test_models_fal.py
}

run_integration_tests() {
    echo "=== Running Integration Tests (Blender) ==="
    echo "Note: For full testing, install the extension in Blender first."
    echo "      Extension-specific tests will be skipped if not installed."
    echo ""
    
    # Find Blender executable
    if command -v blender &> /dev/null; then
        BLENDER="blender"
    elif [ -d "/Applications/Blender.app" ]; then
        BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
    else
        echo "ERROR: Blender not found in PATH"
        echo "Please install Blender or add it to PATH"
        exit 1
    fi
    
    echo "Using Blender: $BLENDER"
    "$BLENDER" --background --python tests/test_blender_integration.py
}

case "${1:-all}" in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    all)
        run_unit_tests
        echo ""
        run_integration_tests
        ;;
    *)
        echo "Usage: $0 [unit|integration|all]"
        exit 1
        ;;
esac

echo ""
echo "All tests passed!"
