"""
Build system auto-detector.

Inspects a source directory and determines which build system it uses.
Returns a BuildProfile with the detected type and configuration hints.

Supported build systems:
    - autotools  (configure / configure.ac / autogen.sh)
    - cmake      (CMakeLists.txt)
    - meson      (meson.build)
    - cargo      (Cargo.toml)        → Rust
    - go         (go.mod)            → Go
    - python     (setup.py / pyproject.toml)
    - make       (Makefile / GNUmakefile)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class BuildSystem(Enum):
    AUTOTOOLS = auto()
    CMAKE = auto()
    MESON = auto()
    CARGO = auto()
    GO = auto()
    PYTHON = auto()
    MAKE = auto()
    UNKNOWN = auto()


@dataclass
class BuildProfile:
    """Result of build system detection."""

    system: BuildSystem
    source_dir: Path
    has_configure: bool = False
    has_autogen: bool = False
    has_cmake: bool = False
    has_meson: bool = False
    cargo_toml: Path | None = None
    go_mod: Path | None = None
    makefile: Path | None = None
    extra_hints: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.system.name.lower()


class BuildDetector:
    """
    Inspects a source tree and returns a BuildProfile.

    Detection priority (highest to lowest):
        1. Cargo.toml   → Rust / Cargo
        2. go.mod       → Go
        3. meson.build  → Meson
        4. CMakeLists   → CMake
        5. configure    → Autotools (pre-generated)
        6. configure.ac → Autotools (needs autoreconf)
        7. autogen.sh   → Autotools (needs autogen)
        8. setup.py / pyproject.toml → Python
        9. Makefile     → Plain Make
    """

    @staticmethod
    def detect(source_dir: Path) -> BuildProfile:
        source_dir = Path(source_dir)

        if not source_dir.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        profile = BuildProfile(
            system=BuildSystem.UNKNOWN,
            source_dir=source_dir,
        )

        # Scan the top-level directory for build markers
        children = {p.name for p in source_dir.iterdir()}

        # --- Meson ---
        if "meson.build" in children:
            profile.system = BuildSystem.MESON
            profile.has_meson = True
            return profile

        # --- CMake ---
        if "CMakeLists.txt" in children:
            profile.system = BuildSystem.CMAKE
            profile.has_cmake = True
            return profile

        # --- Autotools ---
        if "configure" in children:
            profile.system = BuildSystem.AUTOTOOLS
            profile.has_configure = True
            return profile

        if "configure.ac" in children or "configure.in" in children:
            profile.system = BuildSystem.AUTOTOOLS
            profile.has_autogen = "autogen.sh" in children
            return profile

        if "autogen.sh" in children:
            profile.system = BuildSystem.AUTOTOOLS
            profile.has_autogen = True
            return profile

        # --- Rust (only if no configure/Makefile) ---
        if "Cargo.toml" in children:
            # Check if there's also a Makefile — if so, the project
            # likely uses Make as its primary build and Cargo for a
            # small helper (e.g., git has Cargo.toml for gitcore).
            has_makefile = any(
                m in children for m in ("GNUmakefile", "Makefile", "makefile")
            )
            if not has_makefile:
                profile.system = BuildSystem.CARGO
                profile.cargo_toml = source_dir / "Cargo.toml"
                return profile

        # --- Go (only if no configure/Makefile) ---
        if "go.mod" in children:
            has_makefile = any(
                m in children for m in ("GNUmakefile", "Makefile", "makefile")
            )
            if not has_makefile:
                profile.system = BuildSystem.GO
                profile.go_mod = source_dir / "go.mod"
                return profile




        # --- Python ---
        if "pyproject.toml" in children or "setup.py" in children:
            profile.system = BuildSystem.PYTHON
            return profile

        # --- Plain Makefile ---
        for mf in ("GNUmakefile", "Makefile", "makefile"):
            if mf in children:
                profile.system = BuildSystem.MAKE
                profile.makefile = source_dir / mf
                return profile

        return profile
