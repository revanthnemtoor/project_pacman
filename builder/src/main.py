"""
project_pacman Builder

Arch-style build orchestrator.

Pipeline:
    Formula → Parser → Package → StageBuilder → PKGBUILD → makepkg → .pkg.tar.zst
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add converter/src to path so we can import pacman_macos
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / "converter" / "src"),
)

from pacman_macos.formula import Formula
from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer
from pacman_macos.repository import RepositoryBuilder
from pacman_macos.stager import StageBuilder
from pacman_macos.pathfix import rewrite_stage
from pacman_macos.constants import PACKAGES_DIR, OUTPUT_DIR, INSTALL_PREFIX

from resolver import DependencyResolver
from database import PackageDatabase
from makepkg import MakepkgBuilder
from install import Installer


class PackageBuilder:

    def __init__(
        self,
        output: str | Path = None,
        repository: str = "extra",
    ):
        self.output = Path(output or PACKAGES_DIR)
        self.repository = repository

        self.database = PackageDatabase(self.output)
        self.repo = RepositoryBuilder(self.output)
        self.makepkg = MakepkgBuilder()

    # -----------------------------------------------------

    def parse(self, name: str):

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

    def stage(self, name: str, root: Path, mode: str = "auto"):

        print("==> Staging files")

        StageBuilder(
            Formula(name)
        ).stage(
            root / "stage",
            mode=mode,
        )

    # -----------------------------------------------------

    def run_makepkg(self, root: Path) -> Path | None:

        print("==> Running makepkg")

        return self.makepkg.build(root)

    # -----------------------------------------------------

    def build(
        self,
        name: str,
        stage_mode: str = "auto",
        skip_deps: bool = False,
    ) -> list[Path]:
        """
        Build a package and all its dependencies.

        Returns a list of paths to built .pkg.tar.zst archives.
        """
        # Resolve dependency order
        if skip_deps:
            order = [name]
        else:
            resolver = DependencyResolver()
            order = resolver.resolve(name)

            print("Build order:")
            for pkg in order:
                print(f"  - {pkg}")

        built = []

        for pkgname in order:

            print(f"\n{'=' * 50}")
            print(f"  {pkgname}")
            print(f"{'=' * 50}\n")

            package = self.parse(pkgname)

            package = self.normalize(package)

            if self.database.exists(
                package.repository,
                package.name,
            ):
                print(f"Skipping {package.name} (already prepared)")
                continue

            root = self.prepare(package)

            self.stage(pkgname, root, mode=stage_mode)

            # Rewrite Homebrew placeholder paths in staged binaries
            print("==> Rewriting paths")
            rewrite_stage(
                stage_dir=root / "stage",
                install_root=str(INSTALL_PREFIX),
                formula_name=pkgname,
            )

            # makepkg
            pkg_archive = self.run_makepkg(root)

            if pkg_archive:
                built.append(pkg_archive)
                print(f"  -> Package: {pkg_archive.name}")
            else:
                print(f"  -> WARNING: makepkg did not produce a package")

        print()
        print("=" * 50)
        print("Build completed")
        print(f"Packages built: {len(built)}")
        for p in built:
            print(f"  - {p.name}")
        print("=" * 50)

        return built


# =============================================================
# CLI
# =============================================================

def cmd_build(args):
    builder = PackageBuilder(
        repository=args.repository,
    )

    built = builder.build(
        args.package,
        stage_mode=args.stage_mode,
        skip_deps=args.skip_deps,
    )

    if not built:
        print("\nNo new packages were built.")

    return 0 if built else 1


def cmd_install(args):
    installer = Installer()

    for pkg in args.packages:
        print(f"==> Installing {pkg}")
        installer.install(pkg)

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="builder",
        description="project_pacman package builder",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # -- build --

    build_parser = subparsers.add_parser(
        "build",
        help="Build a package from Homebrew formula",
    )
    build_parser.add_argument(
        "package",
        help="Homebrew formula name",
    )
    build_parser.add_argument(
        "--repository",
        default="extra",
        help="Target repository (default: extra)",
    )
    build_parser.add_argument(
        "--stage-mode",
        choices=["auto", "bottle", "cellar"],
        default="auto",
        help="Staging mode (default: auto)",
    )
    build_parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency resolution",
    )
    build_parser.set_defaults(func=cmd_build)

    # -- install --

    install_parser = subparsers.add_parser(
        "install",
        help="Install a .pkg.tar.zst with pacman -U",
    )
    install_parser.add_argument(
        "packages",
        nargs="+",
        help="Package archives to install",
    )
    install_parser.set_defaults(func=cmd_install)

    # -- parse --

    args = parser.parse_args()

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()