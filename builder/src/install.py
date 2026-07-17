"""
Pacman installer.

Installs .pkg.tar.zst packages using pacman -U.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "converter" / "src"),
)

from pacman_macos.constants import PACMAN_BIN, PACMAN_CONF


class Installer:

    def __init__(
        self,
        pacman: str | Path | None = None,
        config: str | Path | None = None,
    ):
        self.pacman = str(pacman or PACMAN_BIN)
        self.config = str(config or PACMAN_CONF)

    def install(
        self,
        package: str | Path,
    ):
        """Install a .pkg.tar.zst with pacman -U."""

        cmd = [
            self.pacman,
            "--config", self.config,
            "-U",
            "--noconfirm",
            str(package),
        ]

        print(f"  -> Running: {' '.join(cmd)}")

        subprocess.run(
            cmd,
            check=True,
        )

        print(f"  -> Installed ✓")
