from pacman_macos.parser import Parser

pkg = Parser("git").parse()

print(pkg.summary())

print()

print(pkg.to_json())
