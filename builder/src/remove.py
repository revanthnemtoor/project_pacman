"""
Pacman remove wrapper.
"""

from __future__ import annotations

import subprocess


class Remover:

    def __init__(
        self,
        pacman="pacman",
        config=None,
    ):
        self.pacman = pacman
        self.config = config

    def remove(self, package):

        cmd = [self.pacman]

        if self.config:
            cmd += [
                "--config",
                self.config,
            ]

        cmd += [
            "-R",
            "--noconfirm",
            package,
        ]

        subprocess.run(
            cmd,
            check=True,
        )
