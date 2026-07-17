from pacman_macos.package import Package

tree = Package(
    name="tree",
    version="2.2.1",
    description="Display directories as trees",
    license=["GPL"],
)

print(tree)
print()

hello = Package(
    name="hello",
    version="2.12.3",
    description="GNU Hello",
    license=["GPL-3.0-or-later"],
)

print(hello)
print()

git = Package(
    name="git",
    version="2.55.0",
    description="Distributed version control system",
    depends=[
        "curl",
        "gettext",
        "openssl",
        "pcre2",
    ],
)

print(git)
print()

print(git.to_json())
