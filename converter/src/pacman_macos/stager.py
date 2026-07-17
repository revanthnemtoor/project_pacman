"""
Stage files for package building.

Supports two modes:

1. Bottle mode (preferred)
   Downloads a pre-built bottle from GHCR and extracts it.

2. Cellar mode (fallback)
   Copies files from the local Homebrew Cellar.
   Only works if the formula is already installed via Homebrew.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from pacman_macos.formula import Formula
from pacman_macos.bottle import BottleDownloader, BottleError


class StageBuilder:

    def __init__(self, formula: Formula):
        self.formula = formula

    # ----------------------------------------------------------

    def stage(
        self,
        destination: Path,
        mode: str = "bottle",
    ) -> Path:
        """
        Stage package files into destination.

        mode:
            "bottle" - Download from GHCR (preferred)
            "cellar" - Copy from local Homebrew Cellar
            "auto"   - Try bottle, fall back to cellar
        """
        destination = Path(destination)

        if mode == "bottle":
            return self._stage_bottle(destination)

        elif mode == "cellar":
            return self._stage_cellar(destination)

        elif mode == "auto":
            try:
                return self._stage_bottle(destination)
            except BottleError as e:
                print(f"  -> Bottle failed: {e}")
                print("  -> Falling back to cellar mode")
                return self._stage_cellar(destination)

        else:
            raise ValueError(f"Unknown staging mode: {mode}")

    # ----------------------------------------------------------

    def _stage_bottle(self, destination: Path) -> Path:
        """Download and extract bottle from GHCR."""
        downloader = BottleDownloader()

        return downloader.download_and_stage(
            self.formula.name,
            destination,
        )

    # ----------------------------------------------------------

    def _stage_cellar(self, destination: Path) -> Path:
        """Copy from local Homebrew Cellar."""
        cellar = self.formula.cellar()

        if not cellar.exists():
            raise RuntimeError(
                f"Cellar not found: {cellar}"
            )

        versions = sorted(
            d for d in cellar.iterdir()
            if d.is_dir()
        )

        if not versions:
            raise RuntimeError(
                f"No versions found in {cellar}"
            )

        latest = versions[-1]

        destination.mkdir(parents=True, exist_ok=True)

        shutil.copytree(
            latest,
            destination,
            dirs_exist_ok=True,
            symlinks=True,
        )

        file_count = sum(
            1 for _ in destination.rglob("*")
            if _.is_file()
        )

        print(f"  -> Staged {file_count} files from Cellar")

        return destination
