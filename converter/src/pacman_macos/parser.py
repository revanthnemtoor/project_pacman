"""
Convert Homebrew formula metadata into the internal Package model.
"""

from __future__ import annotations

from pacman_macos.formula import Formula
from pacman_macos.package import Package


class Parser:

    def __init__(self, formula_name: str):
        self.formula = Formula(formula_name)

    def parse(self) -> Package:

        f = self.formula.formula()

        pkg = Package(
            name=f["name"],
            version=f["versions"]["stable"].replace("-", "."),
            release=f.get("revision", 0) + 1,
            description=f.get("desc", ""),
            homepage=f.get("homepage", ""),
            architecture="darwin_arm64",
            platform="darwin",
            repository="extra",
            depends=list(f.get("dependencies", [])),
            makedepends=list(f.get("build_dependencies", [])),
            checkdepends=list(f.get("test_dependencies", [])),
            optdepends=list(f.get("optional_dependencies", [])),
            conflicts=list(f.get("conflicts_with", [])),
            license=[f["license"]] if f.get("license") else [],
            bottle_url=self.formula.bottle_url() or "",
            bottle_sha256=self.formula.bottle_sha256() or "",
            source_url=f["urls"]["stable"]["url"],
            source_sha256=f["urls"]["stable"]["checksum"],
            origin="homebrew",
        )

        pkg.metadata["tap"] = f.get("tap")
        pkg.metadata["ruby_source"] = f.get("ruby_source_path")
        pkg.metadata["uses_from_macos"] = f.get("uses_from_macos", [])
        pkg.metadata["runtime_dependencies"] = (
            f.get("installed", [{}])[0].get("runtime_dependencies", [])
            if f.get("installed")
            else []
        )

        return pkg