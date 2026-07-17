#!/usr/bin/env python3
import subprocess
import shutil
import os
from pathlib import Path

packages = [
    "git",
    "tree",
    "wget",
    "vim",
    "nano",
    "jq",
    "yq",
    "fastfetch",
    "rsync",
    "ripgrep",
    "fd",
    "fzf",
    "tmux"
]

project_dir = Path("/Users/revanthnemtoo/project_pacman")
output_dir = project_dir / "output"
new_packages_dir = project_dir / "new_packages"

new_packages_dir.mkdir(exist_ok=True)

# Build all packages
for pkg in packages:
    print(f"==========================================")
    print(f"Building {pkg}...")
    print(f"==========================================")
    subprocess.run(
        ["python3", "builder/src/main.py", "build", pkg],
        cwd=project_dir,
        env={**os.environ, "PYTHONPATH": "converter/src:."}
    )

# Update the repo
print(f"==========================================")
print(f"Updating repository...")
print(f"==========================================")
subprocess.run(
    ["python3", "builder/src/main.py", "repo", "update"],
    cwd=project_dir,
    env={**os.environ, "PYTHONPATH": "converter/src:."}
)

# Copy to new_packages
print(f"==========================================")
print(f"Copying packages to new_packages folder...")
print(f"==========================================")
for file_path in output_dir.glob("*.pkg.tar.gz"):
    dest = new_packages_dir / file_path.name
    print(f"Copying {file_path.name}")
    shutil.copy2(file_path, dest)

print("Done!")
