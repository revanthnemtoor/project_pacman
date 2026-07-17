from pacman_macos.parser import Parser
from pacman_macos.dependencies import DependencyNormalizer
from pacman_macos.repository import RepositoryBuilder

pkg = Parser("git").parse()

DependencyNormalizer.normalize_package(pkg)

repo = RepositoryBuilder("packages")

path = repo.create(pkg)

print(path)
