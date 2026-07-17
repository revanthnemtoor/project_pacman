from resolver import DependencyResolver

resolver = DependencyResolver()

for pkg in resolver.resolve("git"):
    print(pkg)
