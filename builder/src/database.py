"""
Simple local package database.
"""

from __future__ import annotations

from pathlib import Path
from pacman_macos.constants import OUTPUT_DIR, DARWIN_ARCH


class PackageDatabase:

    def __init__(self, root="packages"):
        self.root = Path(root)

    def exists(self, repository: str, package: str) -> bool:
        pkgbuild_exists = (
            self.root /
            repository /
            package /
            "PKGBUILD"
        ).exists()
        built_for_arch = any(
            OUTPUT_DIR.glob(f"{package}-*-{DARWIN_ARCH}.pkg.tar.zst")
        ) or any(
            OUTPUT_DIR.glob(f"{package}-*-any.pkg.tar.zst")
        )
        return pkgbuild_exists and built_for_arch

    def package_path(self, repository: str, package: str) -> Path:
        return self.root / repository / package
