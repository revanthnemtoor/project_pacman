from pathlib import Path

from pacman_macos.formula import Formula
from pacman_macos.stager import StageBuilder

builder = StageBuilder(
    Formula("git")
)

builder.stage(
    Path("staging/git")
)

print("Done")
