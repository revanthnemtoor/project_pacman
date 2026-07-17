"""
project_pacman

Homebrew -> Pacman package converter
"""

from __future__ import annotations

import argparse

from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer
from pacman_macos.repository import RepositoryBuilder


def convert(package_name: str) -> None:

    print(f"==> Parsing {package_name}")

    package = Parser(package_name).parse()

    print("==> Normalizing dependencies")

    DependencyNormalizer.normalize_package(package)

    print("==> Creating package repository")

    repo = RepositoryBuilder("packages")

    path = repo.create(package)

    print()

    print("Package created")

    print(path)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "package",
        help="Homebrew formula name",
    )

    args = parser.parse_args()

    convert(args.package)


if __name__ == "__main__":
    main()