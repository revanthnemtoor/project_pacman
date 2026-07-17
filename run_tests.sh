#!/usr/bin/env bash
set -e

echo "=== Cleaning state ==="
rm -rf staging packages output repo cache logs git.json
mkdir -p staging packages output repo cache logs

echo "=== Running Converter Tests ==="
PYTHONPATH=converter/src python3 tests/test_package.py
PYTHONPATH=converter/src python3 tests/test_formula.py
PYTHONPATH=converter/src python3 tests/dump_formula.py > git.json
PYTHONPATH=converter/src python3 tests/test_parser.py
PYTHONPATH=converter/src python3 tests/test_dependencies.py
PYTHONPATH=converter/src python3 tests/test_pkgbuild.py
PYTHONPATH=converter/src python3 tests/test_repository.py
PYTHONPATH=converter/src python3 tests/test_stage.py

echo "=== Running Builder Tests ==="
PYTHONPATH="builder/src:converter/src" python3 tests/test_resolver.py
PYTHONPATH="builder/src:converter/src" python3 tests/test_makepkg.py
# Skipping test_artifact.py as it doesn't exist
PYTHONPATH="builder/src:converter/src" python3 tests/test_install.py
PYTHONPATH="builder/src:converter/src" python3 tests/test_query.py
PYTHONPATH="builder/src:converter/src" python3 tests/test_verify.py
PYTHONPATH="builder/src:converter/src" python3 tests/test_remove.py

echo "=== Running Pacman Commands ==="
/opt/pacman/bin/pacman --config /opt/pacman/etc/pacman.conf -Q
/opt/pacman/bin/pacman --config /opt/pacman/etc/pacman.conf -Qi tree
/opt/pacman/bin/pacman --config /opt/pacman/etc/pacman.conf -Ql tree

# Find actual tree package since version/path might differ
TREE_PKG=$(ls output/tree-*.pkg.tar.zst 2>/dev/null | head -n 1)
if [ -n "$TREE_PKG" ]; then
    echo "Installing $TREE_PKG..."
    /opt/pacman/bin/pacman --config /opt/pacman/etc/pacman.conf -U --noconfirm "$TREE_PKG"
else
    echo "Tree package not found in output/"
fi
