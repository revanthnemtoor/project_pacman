#!/usr/bin/env bash
#
# build_and_install.sh - Build and install a pacman package from Homebrew
#
# Usage:
#   ./scripts/build_and_install.sh <formula_name> [--skip-deps]
#
# Examples:
#   ./scripts/build_and_install.sh tree
#   ./scripts/build_and_install.sh jq
#   ./scripts/build_and_install.sh git --skip-deps
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

PACMAN_BIN="$HOME/pacman/bin/pacman"
PACMAN_CONF="$PROJECT_DIR/configs/pacman.conf"

FORMULA="${1:?Usage: $0 <formula_name> [--skip-deps]}"
SKIP_DEPS="${2:-}"

echo "============================================"
echo "  project_pacman - Build & Install"
echo "============================================"
echo ""
echo "  Formula:  $FORMULA"
echo "  Project:  $PROJECT_DIR"
echo "  Config:   $PACMAN_CONF"
echo ""

# -------------------------------------------------------
# Step 1: Build
# -------------------------------------------------------

echo ">>> Step 1: Building package..."
echo ""

BUILD_ARGS="build $FORMULA --stage-mode bottle"
if [ "$SKIP_DEPS" = "--skip-deps" ]; then
    BUILD_ARGS="$BUILD_ARGS --skip-deps"
fi

cd "$PROJECT_DIR/builder/src"
PYTHONPATH="$PROJECT_DIR/converter/src:." python3 main.py $BUILD_ARGS

echo ""

# -------------------------------------------------------
# Step 2: Update Repository
# -------------------------------------------------------

echo ">>> Step 2: Updating repository..."
echo ""

cd "$PROJECT_DIR/builder/src"
PYTHONPATH="$PROJECT_DIR/converter/src:." python3 main.py repo update

echo ""

# -------------------------------------------------------
# Step 3: Install
# -------------------------------------------------------

echo ">>> Step 3: Installing with pacman -Sy..."

# Sync and install the package from the local repo
sudo "$PACMAN_BIN" --config "$PACMAN_CONF" -Sy --noconfirm "$FORMULA"

echo ""

# -------------------------------------------------------
# Step 4: Verify
# -------------------------------------------------------

echo ">>> Step 4: Verifying installation..."
echo ""

echo "--- pacman -Qi $FORMULA ---"
"$PACMAN_BIN" --config "$PACMAN_CONF" -Qi "$FORMULA"

echo ""
echo "--- pacman -Ql $FORMULA ---"
"$PACMAN_BIN" --config "$PACMAN_CONF" -Ql "$FORMULA"

echo ""
echo "============================================"
echo "  ✓ $FORMULA installed successfully"
echo "============================================"
