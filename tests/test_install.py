from install import Installer

Installer(
    pacman="/opt/pacman/bin/pacman",
    config="/opt/pacman/etc/pacman.conf",
).install(
    "packages/extra/tree/tree-2.2.1-1-arm64.pkg.tar.zst"
)
