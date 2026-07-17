from query import Query


class Verifier:

    def __init__(
        self,
        pacman="pacman",
        config=None,
    ):
        self.query = Query(
            pacman=pacman,
            config=config,
        )

    def installed(self, package):
        return self.query.installed(package)