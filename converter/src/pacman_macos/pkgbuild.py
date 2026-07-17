"""
PKGBUILD generator.

Converts an internal Package object into a PKGBUILD file
suitable for building with makepkg.

For bottle-based packages, the PKGBUILD assumes files are
pre-staged in $startdir/stage/ and copies them into $pkgdir.
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

        # -- Identity --

        lines.append(f"pkgname={p.name}")
        lines.append(f"pkgver={p.version}")
        lines.append(f"pkgrel={p.release}")
        lines.append(f'pkgdesc="{p.description}"')
        lines.append("")

        # -- Metadata --

        lines.append(f'url="{p.homepage}"')

        lines.append(
            f"arch={self._array([p.architecture])}"
        )

        lines.append(
            f"license={self._array(p.license)}"
        )

        # -- Dependencies --

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

        # -- Build options --
        # Disable stripping to preserve macOS code signatures
        lines.append("options=('!strip')")

        # -- Source --
        # For bottle-based packages we don't use source=()
        # because the bottle is pre-staged locally.
        if p.build_type == "bottle":
            lines.append("source=()")
            lines.append("sha256sums=()")
        else:
            if p.source_url:
                lines.append(
                    f"source={self._array([p.source_url])}"
                )
            if p.source_sha256:
                lines.append(
                    f"sha256sums={self._array([p.source_sha256])}"
                )

        lines.append("")

        # -- package() function --

        lines.append("package() {")

        if p.build_type == "bottle":
            # Copy only standard directories from the staged bottle.
            # Homebrew bottles include top-level metadata files
            # (AUTHORS, COPYING, README, sbom.spdx.json, .brew/)
            # that would conflict between packages if installed to
            # the root. We only copy the FHS directories.
            lines.append('    local _stage="$startdir/stage"')
            lines.append('    local _dest="$pkgdir"')
            lines.append('    mkdir -p "$_dest"')
            lines.append("")
            lines.append("    local _dirs=(bin sbin lib lib64 include share etc var libexec)")
            lines.append("    for _d in \"${_dirs[@]}\"; do")
            lines.append("        if [ -d \"$_stage/$_d\" ]; then")
            lines.append('            cp -a "$_stage/$_d" "$_dest/"')
            lines.append("        fi")
            lines.append("    done")
        else:
            lines.append("    :")
            lines.append("    # TODO: source build")

        lines.append("}")

        return "\n".join(lines)

    # ---------------------------------------------------------

    def write(self, path: str | Path):

        Path(path).write_text(
            self.text(),
            encoding="utf-8",
        )
