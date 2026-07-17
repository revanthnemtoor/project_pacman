from remove import Remover

Remover(
    pacman="/opt/pacman/bin/pacman",
    config="/opt/pacman/etc/pacman.conf",
).remove("tree")
