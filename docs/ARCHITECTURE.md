                      User

                        │
                        ▼

               converter/main.py
                      (CLI)

                        │
                        ▼

                PackageBuilder
              (builder/main.py)

                        │
 ┌──────────────┬─────────────┬──────────────┐
 ▼              ▼             ▼              ▼
Formula      Parser     Dependencies     Bottle
(Homebrew)                Normalize      Download

                        │
                        ▼

                   Package

                        │
            ┌───────────┴────────────┐
            ▼                        ▼
      RepositoryBuilder        PKGBUILDBuilder
            │                        │
            └───────────┬────────────┘
                        ▼
                     stage/

                        │
                        ▼
                    makepkg

                        │
                        ▼
                 .pkg.tar.zst

                        │
                        ▼
                    repo-add

                        │
                        ▼
                packages.db.tar.zst

                        │
                        ▼
                 GitHub Repository
