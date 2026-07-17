from query import Query

query = Query(
    pacman="/opt/pacman/bin/pacman",
    config="/opt/pacman/etc/pacman.conf",
)

print(query.installed("tree"))
print(query.installed("git"))
print(query.installed("does-not-exist"))
