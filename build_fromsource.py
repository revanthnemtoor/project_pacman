#!/usr/bin/env python3
"""
build_fromsource.py - Build all packages from source.

This script orchestrates the full from-source build pipeline:
    1. Detects each source's build system (autotools, cmake, cargo, go, etc.)
    2. Auto-generates an Arch-style PKGBUILD
    3. Compiles natively with makepkg
    4. Verifies the package structure & code signatures
    5. Adds to the pacman repository database

Usage:
    python3 build_fromsource.py
    python3 build_fromsource.py --detect-only
    python3 build_fromsource.py --packages git nano
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure fromsource module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fromsource.builder import SourceBuilder
from fromsource.detector import BuildDetector


# -----------------------------------------------------------------
# Package registry
#
# Each entry defines a package to build from source. The source_dir
# points to the pre-cloned git repository under fromsource/*-src.
# -----------------------------------------------------------------

FROMSOURCE_DIR = Path(__file__).resolve().parent / "fromsource"

PACKAGES = [
    {
        "name": "ncurses",
        "version": "6.4",
        "source_dir": FROMSOURCE_DIR / "ncurses-src",
        "description": "System V Release 4.0 curses emulation library",
        "url": "https://invisible-island.net/ncurses/",
        "license": "MIT",
        "depends": [],
    },
    {
        "name": "nano",
        "version": "9.1",
        "source_dir": FROMSOURCE_DIR / "nano-release",
        "description": "Pico editor clone with enhancements",
        "url": "https://www.nano-editor.org/",
        "license": "GPL3",
        "depends": ["ncurses"],
    },
    {
        "name": "git",
        "version": "2.55.0",
        "source_dir": FROMSOURCE_DIR / "git-src",
        "description": "The fast distributed version control system",
        "url": "https://git-scm.com/",
        "license": "GPL2",
        "depends": [],
        "build_override": "make",  # git has meson.build + Cargo.toml but builds via Make
    },
]


def detect_all():
    """Print detected build systems for all registered packages."""

    print("=" * 60)
    print("  Build System Detection Report")
    print("=" * 60)

    for pkg in PACKAGES:
        print(f"\n--- {pkg['name']} ---")
        src = pkg["source_dir"]
        if not src.exists():
            print(f"  Source not found: {src}")
            continue

        profile = BuildDetector.detect(src)
        print(f"  Source:     {src}")
        print(f"  Detected:  {profile.name}")


def build_all(filter_packages: list[str] | None = None):
    """Build all or filtered packages."""

    builder = SourceBuilder()

    pkgs = PACKAGES
    if filter_packages:
        pkgs = [p for p in PACKAGES if p["name"] in filter_packages]

    builder.build_all(pkgs)


def main():
    parser = argparse.ArgumentParser(
        description="Build packages from source for project_pacman"
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect build systems, don't compile",
    )
    parser.add_argument(
        "--packages",
        nargs="*",
        help="Only build these packages (by name)",
    )

    args = parser.parse_args()

    if args.detect_only:
        detect_all()
    else:
        build_all(args.packages)


if __name__ == "__main__":
    main()
