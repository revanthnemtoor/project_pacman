"""
project_pacman Builder

Arch-style build orchestrator.
"""

from __future__ import annotations

from pathlib import Path

from pacman_macos.formula import Formula
from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer
from pacman_macos.repository import RepositoryBuilder
from pacman_macos.stager import StageBuilder
from resolver import DependencyResolver
from database import PackageDatabase


class PackageBuilder:

    def __init__(
        self,
        output: str | Path = "packages",
        repository: str = "extra",
        self.database = PackageDatabase(output)
    ):
        self.output = Path(output)
        self.repository = repository

        self.repo = RepositoryBuilder(self.output)

    # -----------------------------------------------------

    def parse(self, name):

        print(f"==> Parsing {name}")

        return Parser(name).parse()

    # -----------------------------------------------------

    def normalize(self, package):

        print("==> Normalizing dependencies")

        DependencyNormalizer.normalize_package(package)

        package.repository = self.repository

        return package

    # -----------------------------------------------------

    def prepare(self, package):

        print("==> Preparing package directory")

        return self.repo.create(package)

    # -----------------------------------------------------

    def stage(self, name, root):

        print("==> Staging files")

        StageBuilder(
            Formula(name)
        ).stage(
            root / "stage"
        )

    # -----------------------------------------------------

    def generate_pkgbuild(self, package):

        print("==> PKGBUILD generated")

        # RepositoryBuilder already generated it.
        # Later this becomes an explicit step.

    # -----------------------------------------------------

    def makepkg(self, root):

        print("==> makepkg")

        #
        # TODO
        #
        # subprocess.run(...)
        #

    # -----------------------------------------------------

    def repo_add(self):

        print("==> repo-add")

        #
        # TODO
        #

    # -----------------------------------------------------

    def publish(self):

        print("==> publish")

        #
        # TODO
        #

    # -----------------------------------------------------

    def build(self, name):

    resolver = DependencyResolver()

    order = resolver.resolve(name)

    print("Build order:")
    for pkg in order:
        print(f"  - {pkg}")

    roots = []

    for pkgname in order:

        print(f"\n==== {pkgname} ====\n")

        package = self.parse(pkgname)

        package = self.normalize(package)

        if self.database.exists(
            package.repository,
            package.name,
        ):
            print(f"Skipping {package.name} (already prepared)")
            continue

        root = self.prepare(package)

        self.stage(pkgname, root)

        self.generate_pkgbuild(package)

        # Phase 2
        # self.makepkg(root)

        roots.append(root)

    print()
    print("===================================")
    print("Package build completed")
    print("===================================")

    return roots