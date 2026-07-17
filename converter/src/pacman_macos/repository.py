"""
Repository layout manager.
"""

from __future__ import annotations

import json
from pathlib import Path

from pacman_macos.package import Package
from pacman_macos.pkgbuild import PKGBUILDBuilder


class RepositoryBuilder:

    def __init__(self, root: str | Path):
        self.root = Path(root)

    # ------------------------------------------------------

    def package_dir(self, package: Package) -> Path:
        return self.root / package.repository / package.name

    # ------------------------------------------------------

    def create(self, package: Package) -> Path:

        root = self.package_dir(package)

        root.mkdir(parents=True, exist_ok=True)

        (root / "stage").mkdir(exist_ok=True)
        (root / "src").mkdir(exist_ok=True)
        (root / "pkg").mkdir(exist_ok=True)
        (root / "logs").mkdir(exist_ok=True)

        PKGBUILDBuilder(package).write(root / "PKGBUILD")

        with open(root / "metadata.json", "w") as fp:
            json.dump(package.to_dict(), fp, indent=4)

        return root