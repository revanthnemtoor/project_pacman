"""
Repository Manager module.
Wraps pacman's repo-add and repo-remove commands.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pacman_macos.constants import REPO_ADD_BIN, OUTPUT_DIR


class RepoManager:
    """Manages the local pacman repository database."""

    def __init__(self, db_name: str = "pacman.db.tar.gz"):
        self.db_name = db_name
        self.db_path = OUTPUT_DIR / self.db_name

    def update_repo(self, package_paths: list[Path | str] | None = None) -> bool:
        """
        Add packages to the repository database.
        If package_paths is None, adds all .pkg.tar.zst files in OUTPUT_DIR.
        """
        if not REPO_ADD_BIN.exists():
            print(f"Error: repo-add not found at {REPO_ADD_BIN}")
            return False

        if package_paths is None:
            # Find all packages in OUTPUT_DIR
            package_paths = [p for p in OUTPUT_DIR.glob("*.pkg.tar.*") if not p.name.endswith(".sig")]

        if not package_paths:
            print("No packages found to add to repository.")
            return True

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [str(REPO_ADD_BIN), "--sign", str(self.db_path)] + [str(p) for p in package_paths]

        print(f"==> Updating repository database: {self.db_name}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error updating repository: {result.stderr}")
            return False

        print(f"  -> Added {len(package_paths)} packages to {self.db_name}")
        return True

    def remove_package(self, package_name: str) -> bool:
        """
        Remove a package from the repository database.
        Note: repo-remove is a symlink to repo-add, we can just call repo-add -R 
        or use the repo-remove symlink if it exists. We'll use repo-remove.
        """
        repo_remove = REPO_ADD_BIN.parent / "repo-remove"
        if not repo_remove.exists():
            print(f"Error: repo-remove not found at {repo_remove}")
            return False

        if not self.db_path.exists():
            print(f"Repository database {self.db_path} does not exist.")
            return False

        cmd = [str(repo_remove), str(self.db_path), package_name]

        print(f"==> Removing {package_name} from repository database...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error removing from repository: {result.stderr}")
            return False

        print(f"  -> Removed {package_name}")
        return True
