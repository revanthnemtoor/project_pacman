"""
Canonical package model used throughout project_pacman.

Nothing outside the parser should need to know anything about Homebrew.

Homebrew Formula
        ↓
Parser
        ↓
Package
        ↓
PKGBUILD / Repository / Builder
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass(slots=True)
class Package:
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    name: str
    version: str

    release: int = 1
    epoch: int = 0
    base: str | None = None

    # ------------------------------------------------------------------
    # Description
    # ------------------------------------------------------------------

    description: str = ""
    homepage: str = ""
    license: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Platform
    # ------------------------------------------------------------------

    architecture: str = "arm64"
    platform: str = "darwin"
    repository: str = "extra"

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    depends: list[str] = field(default_factory=list)
    makedepends: list[str] = field(default_factory=list)
    checkdepends: list[str] = field(default_factory=list)
    optdepends: list[str] = field(default_factory=list)

    provides: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    replaces: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Bottle
    # ------------------------------------------------------------------

    bottle_url: str = ""
    bottle_sha256: str = ""

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    source_url: str = ""
    source_sha256: str = ""

    # ------------------------------------------------------------------
    # Size
    # ------------------------------------------------------------------

    installed_size: int = -1
    download_size: int = -1

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    build_type: str = "bottle"
    packager: str = ""
    build_date: datetime | None = None

    # ------------------------------------------------------------------
    # Package contents
    # ------------------------------------------------------------------

    files: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Origin
    # ------------------------------------------------------------------

    origin: str = "homebrew"

    metadata: dict = field(default_factory=dict)
    xdata: dict = field(default_factory=dict)

    # ================================================================

    @property
    def full_version(self) -> str:
        return f"{self.version}-{self.release}"

    # ================================================================

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Package name cannot be empty")

        if not self.version:
            raise ValueError("Package version cannot be empty")

        if self.release < 1:
            raise ValueError("Release must be >= 1")

        if self.architecture not in (
            "arm64",
            "darwin_arm64",
            "x86_64",
            "any",
        ):
            raise ValueError(
                f"Unsupported architecture: {self.architecture}"
            )

    # ================================================================

    def to_dict(self) -> dict:
        data = asdict(self)

        if self.build_date:
            data["build_date"] = self.build_date.isoformat()

        return data

    # ================================================================

    @classmethod
    def from_dict(cls, data: dict) -> "Package":
        if data.get("build_date"):
            data["build_date"] = datetime.fromisoformat(
                data["build_date"]
            )

        return cls(**data)

    # ================================================================

    def to_json(self, indent: int = 4) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            sort_keys=True,
        )

    # ================================================================

    @classmethod
    def from_json(cls, text: str) -> "Package":
        return cls.from_dict(json.loads(text))

    # ================================================================

    def summary(self) -> str:
        deps = ", ".join(self.depends) or "None"

        return (
            f"{self.name} {self.full_version}\n"
            f"Repository : {self.repository}\n"
            f"Platform   : {self.platform}\n"
            f"Arch       : {self.architecture}\n"
            f"Depends    : {deps}\n"
            f"Files      : {len(self.files)}"
        )

    # ================================================================

    def __str__(self) -> str:
        return self.summary()
