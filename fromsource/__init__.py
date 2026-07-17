"""
fromsource - Native From-Source Build System for project_pacman

Modular build system that auto-detects project build systems
(autotools, cmake, meson, cargo, python, go, make) and generates
Arch-style PKGBUILDs to compile packages natively on macOS ARM64.

Architecture:
    SourcePackage → BuildDetector → PKGBUILDGenerator → makepkg → .pkg.tar.zst
"""
