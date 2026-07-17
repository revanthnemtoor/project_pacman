from pacman_macos.formula import Formula

formula = Formula("git")

print("Exists:")
print(formula.exists())

print()

print("Version:")
print(formula.version())

print()

print("Description:")
print(formula.description())

print()

print("Homepage:")
print(formula.homepage())

print()

print("Dependencies:")
print(formula.dependencies())

print()

print("License:")
print(formula.license())

print()

print("Bottle URL:")
print(formula.bottle_url())

print()

print("Bottle SHA:")
print(formula.bottle_sha256())

print()

print("Cellar:")
print(formula.cellar())
