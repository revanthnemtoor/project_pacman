"""
Dependency resolver.
"""

from __future__ import annotations

from collections import deque

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

        pkg = Parser(name).parse()
        DependencyNormalizer.normalize_package(pkg)

        for dep in pkg.depends:
            self._visit(dep)

        self._order.append(name)

    def resolve(self, package: str):

        self._visited.clear()
        self._order.clear()

        self._visit(package)

        return self._order.copy()
