"""
PKGBUILD generator.

Converts an internal Package object into a PKGBUILD.
"""

from __future__ import annotations

from pathlib import Path

from pacman_macos.package import Package


class PKGBUILDBuilder:

    def __init__(self, package: Package):
        self.package = package

    # ---------------------------------------------------------

    def _array(self, values: list[str]) -> str:
        if not values:
            return "()"

        return "(\n" + "".join(f"    '{v}'\n" for v in values) + ")"

    # ---------------------------------------------------------

    def text(self) -> str:

        p = self.package

        lines = []

        lines.append(f"pkgname={p.name}")
        lines.append(f"pkgver={p.version}")
        lines.append(f"pkgrel={p.release}")
        lines.append(f'pkgdesc="{p.description}"')
        lines.append("")

        lines.append(f'url="{p.homepage}"')

        lines.append(
            f"arch={self._array([p.architecture])}"
        )

        lines.append(
            f"license={self._array(p.license)}"
        )

        if p.depends:
            lines.append(
                f"depends={self._array(p.depends)}"
            )

        if p.makedepends:
            lines.append(
                f"makedepends={self._array(p.makedepends)}"
            )

        if p.checkdepends:
            lines.append(
                f"checkdepends={self._array(p.checkdepends)}"
            )

        if p.optdepends:
            lines.append(
                f"optdepends={self._array(p.optdepends)}"
            )

        if p.conflicts:
            lines.append(
                f"conflicts={self._array(p.conflicts)}"
            )

        if p.source_url:
            lines.append(
                f"source={self._array([p.source_url])}"
            )

        if p.source_sha256:
            lines.append(
                f"sha256sums={self._array([p.source_sha256])}"
            )

        lines.append("")

        lines.append("package() {")

        if p.build_type == "bottle":
            lines.append('    cp -a "$srcdir/stage/"* "$pkgdir/usr/"')
        else:
            lines.append("    :")
            lines.append("    # TODO")

        lines.append("}")

        return "\n".join(lines)

    # ---------------------------------------------------------

    def write(self, path: str | Path):

        Path(path).write_text(
            self.text(),
            encoding="utf-8",
        )
