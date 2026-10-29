"""
Repository Manager module.
Wraps pacman's repo-add and repo-remove commands.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pacman_macos.constants import REPO_ADD_BIN, OUTPUT_DIR, DARWIN_ARCH


class RepoManager:
    """Manages the local pacman repository database."""

    def __init__(self, db_name: str = "pacman.db.tar.gz"):
        self.db_name = db_name
        self.db_path = OUTPUT_DIR / self.db_name

    def update_repo(self, package_paths: list[Path | str] | None = None) -> bool:
        """
        Add packages to the repository database.
        If package_paths is None, adds all .pkg.tar.zst files in OUTPUT_DIR
        matching the current DARWIN_ARCH (or 'any').
        """
        if not REPO_ADD_BIN.exists():
            print(f"Error: repo-add not found at {REPO_ADD_BIN}")
            return False

        if package_paths is None:
            # Find all packages in OUTPUT_DIR matching current DARWIN_ARCH or 'any'
            package_paths = [
                p for p in OUTPUT_DIR.glob("*.pkg.tar.*")
                if not p.name.endswith(".sig")
                and (f"-{DARWIN_ARCH}.pkg.tar." in p.name or "-any.pkg.tar." in p.name)
            ]

        if not package_paths:
            print("No packages found to add to repository.")
            return True

        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [str(REPO_ADD_BIN)]
        if shutil.which("gpg"):
            gpg_check = subprocess.run(
                ["gpg", "--list-secret-keys"],
                capture_output=True,
                text=True,
            )
            if gpg_check.returncode == 0 and gpg_check.stdout.strip():
                cmd.append("--sign")
        cmd.extend([str(self.db_path)] + [str(p) for p in package_paths])

        print(f"==> Updating repository database: {self.db_name}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error updating repository: {result.stderr}")
            return False

        # Save arch-specific pre-built DB and convert symlinks to real files for GitHub Pages
        base_prefix = self.db_name.split(".db")[0]
        db_link = OUTPUT_DIR / f"{base_prefix}.db"
        files_tar = OUTPUT_DIR / f"{base_prefix}.files.tar.gz"
        files_link = OUTPUT_DIR / f"{base_prefix}.files"

        if self.db_path.exists():
            shutil.copy2(self.db_path, OUTPUT_DIR / f"{base_prefix}-{DARWIN_ARCH}.db.tar.gz")
            if db_link.is_symlink() or db_link.exists():
                db_link.unlink()
            shutil.copy2(self.db_path, db_link)

        if files_tar.exists():
            shutil.copy2(files_tar, OUTPUT_DIR / f"{base_prefix}-{DARWIN_ARCH}.files.tar.gz")
            if files_link.is_symlink() or files_link.exists():
                files_link.unlink()
            shutil.copy2(files_tar, files_link)

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
