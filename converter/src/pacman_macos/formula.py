"""
Homebrew Formula Interface

This module communicates directly with Homebrew.

It does NOT know anything about our Package class.

Responsibilities

- Read formula metadata
- Read bottle metadata
- Read dependencies
- Read versions

Nothing else.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class FormulaError(RuntimeError):
    pass


class Formula:

    def __init__(self, name: str):
        self.name = name

    # ----------------------------------------------------------

    def exists(self) -> bool:
        result = subprocess.run(
            ["brew", "info", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return result.returncode == 0

    # ----------------------------------------------------------

    def json(self) -> dict:
        proc = subprocess.run(
            [
                "brew",
                "info",
                "--json=v2",
                self.name,
            ],
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise FormulaError(proc.stderr.strip())

        return json.loads(proc.stdout)

    # ----------------------------------------------------------

    def formula(self) -> dict:
        data = self.json()

        formulas = data.get("formulae", [])

        if not formulas:
            raise FormulaError(
                f"No formula named '{self.name}'"
            )

        return formulas[0]

    # ----------------------------------------------------------

    def bottle(self) -> dict:
        return self.formula().get("bottle", {})

    # ----------------------------------------------------------

    def dependencies(self) -> list[str]:
        return self.formula().get("dependencies", [])

    # ----------------------------------------------------------

    def build_dependencies(self) -> list[str]:
        return self.formula().get("build_dependencies", [])

    # ----------------------------------------------------------

    def optional_dependencies(self) -> list[str]:
        return self.formula().get("optional_dependencies", [])

    # ----------------------------------------------------------

    def version(self) -> str:
        return self.formula()["versions"]["stable"]

    # ----------------------------------------------------------

    def homepage(self) -> str:
        return self.formula().get("homepage", "")

    # ----------------------------------------------------------

    def description(self) -> str:
        return self.formula().get("desc", "")

    # ----------------------------------------------------------

    def license(self):
        return self.formula().get("license", "")

    # ----------------------------------------------------------

    def revision(self) -> int:
        return self.formula().get("revision", 0)

    # ----------------------------------------------------------

    def bottle_info(self) -> dict | None:
        files = (
            self.bottle()
            .get("stable", {})
            .get("files", {})
        )

        if not files:
            return None

        # Prefer Apple Silicon bottle
        for tag, info in files.items():
            if tag.startswith("arm64"):
                return info

        # Otherwise return first bottle
        return next(iter(files.values()), None)


    def bottle_url(self) -> str | None:
        info = self.bottle_info()
        return info.get("url") if info else None


    def bottle_sha256(self) -> str | None:
        info = self.bottle_info()
        return info.get("sha256") if info else None


    # ----------------------------------------------------------

    def cellar(self) -> Path:

        proc = subprocess.run(
            [
                "brew",
                "--cellar",
                self.name,
            ],
            capture_output=True,
            text=True,
        )

        return Path(proc.stdout.strip())
