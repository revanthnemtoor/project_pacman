"""
Copy an installed Homebrew package into stage/.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from pacman_macos.formula import Formula


class StageBuilder:

    def __init__(self, formula: Formula):
        self.formula = formula

    def stage(self, destination: Path):

        cellar = self.formula.cellar()

        versions = sorted(cellar.iterdir())

        if not versions:
            raise RuntimeError("Package is not installed.")

        latest = versions[-1]

        shutil.copytree(
            latest,
            destination,
            dirs_exist_ok=True,
        )
