"""
Dependency resolver.
"""

from __future__ import annotations

import json
from collections import deque

from pacman_macos.constants import PACKAGES_DIR
from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer


class DependencyResolver:

    def __init__(self):
        self._visited = set()
        self._order = []

    def _visit(self, name: str):

        if name in self._visited:
            return

        self._visited.add(name)

        meta_file = PACKAGES_DIR / "extra" / name / "metadata.json"
        if meta_file.exists():
            try:
                data = json.loads(meta_file.read_text())
                deps = DependencyNormalizer.normalize_list(data.get("depends", []))
            except Exception:
                pkg = Parser(name).parse()
                DependencyNormalizer.normalize_package(pkg)
                deps = pkg.depends
        else:
            pkg = Parser(name).parse()
            DependencyNormalizer.normalize_package(pkg)
            deps = pkg.depends

        for dep in deps:
            self._visit(dep)

        self._order.append(name)

    def resolve(self, package: str):

        self._visited.clear()
        self._order.clear()

        self._visit(package)

        return self._order.copy()
