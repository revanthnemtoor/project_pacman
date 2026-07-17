"""
Dependency normalizer.

Converts Homebrew package names into project_pacman names.

Examples

openssl@3  -> openssl
python@3.13 -> python
icu4c@78 -> icu
"""

from __future__ import annotations

import re

from pacman_macos.package import Package


class DependencyNormalizer:

    # Exact package mappings
    PACKAGE_MAP = {
        "openssl@3": "openssl",
        "python@3.13": "python",
        "python@3.14": "python",
        "llvm@20": "llvm",
        "icu4c@78": "icu",
        "icu4c": "icu",
        "pkgconf": "pkgconf",
    }

    # macOS system libraries we do not package
    SYSTEM_DEPENDENCIES = {
        "curl",
        "expat",
        "zlib",
        "libiconv",
    }

    @classmethod
    def normalize_name(cls, name: str) -> str:
        if name in cls.PACKAGE_MAP:
            return cls.PACKAGE_MAP[name]

        # Strip version suffix
        name = re.sub(r"@[0-9.]+$", "", name)

        return name

    @classmethod
    def normalize_list(cls, deps: list[str]) -> list[str]:

        result: list[str] = []

        for dep in deps:

            dep = cls.normalize_name(dep)

            if dep in cls.SYSTEM_DEPENDENCIES:
                continue

            if dep not in result:
                result.append(dep)

        result.sort()

        return result

    @classmethod
    def normalize_package(cls, pkg: Package) -> Package:
        
        # Normalize the package's own name (e.g. openssl@3 -> openssl)
        pkg.name = cls.normalize_name(pkg.name)

        pkg.depends = cls.normalize_list(pkg.depends)
        pkg.makedepends = cls.normalize_list(pkg.makedepends)
        pkg.checkdepends = cls.normalize_list(pkg.checkdepends)
        pkg.optdepends = cls.normalize_list(pkg.optdepends)

        return pkg
