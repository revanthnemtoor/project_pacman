"""
Pacman query wrapper.
"""

from __future__ import annotations

import subprocess


class Query:

    def __init__(
        self,
        pacman="pacman",
        config=None,
    ):
        self.pacman = pacman
        self.config = config

    def installed(self, package):

        cmd = [self.pacman]

        if self.config:
            cmd += [
                "--config",
                self.config,
            ]

        cmd += [
            "-Q",
            package,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        print("Command:", " ".join(cmd))
        print("Return code:", result.returncode)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)

        return result.returncode == 0