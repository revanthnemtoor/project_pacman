"""
Arch makepkg wrapper.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class MakepkgBuilder:

    def __init__(self, makepkg="makepkg"):
        self.makepkg = makepkg

    def build(
        self,
        package_dir: str | Path,
        force: bool = True,
        install: bool = False,
    ):

        package_dir = Path(package_dir)

        cmd = [
            self.makepkg,
            "--nosign",
        ]

        if force:
            cmd.append("-f")

        if install:
            cmd.append("-i")

        subprocess.run(
            cmd,
            cwd=package_dir,
            check=True,
        )
