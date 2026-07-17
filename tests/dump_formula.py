# tests/dump_formula.py

import json
from pacman_macos.formula import Formula

f = Formula("git")

print(json.dumps(f.formula(), indent=4))
