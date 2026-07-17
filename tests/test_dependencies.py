from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer

pkg = Parser("git").parse()

print("Before")
print(pkg.depends)
print(pkg.makedepends)

DependencyNormalizer.normalize_package(pkg)

print()

print("After")
print(pkg.depends)
print(pkg.makedepends)
