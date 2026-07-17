from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer
from pacman_macos.pkgbuild import PKGBUILDBuilder

pkg = Parser("git").parse()

DependencyNormalizer.normalize_package(pkg)

builder = PKGBUILDBuilder(pkg)

print(builder.text())

builder.write("PKGBUILD")
