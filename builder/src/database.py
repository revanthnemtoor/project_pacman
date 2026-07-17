"""
Simple local package database.
"""

from __future__ import annotations

from pathlib import Path


class PackageDatabase:

    def __init__(self, root="packages"):
        self.root = Path(root)

    def exists(self, repository: str, package: str) -> bool:
        return (
            self.root /
            repository /
            package /
            "PKGBUILD"
        ).exists()

    def package_path(self, repository: str, package: str) -> Path:
        return self.root / repository / package
