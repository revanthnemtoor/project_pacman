"""
Arch makepkg wrapper.

Runs makepkg to build a .pkg.tar.zst archive from a PKGBUILD.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pacman_macos.constants import MAKEPKG_BIN, MAKEPKG_CONF, OUTPUT_DIR


class MakepkgBuilder:

    def __init__(
        self,
        makepkg: str | Path | None = None,
        config: str | Path | None = None,
        output_dir: str | Path | None = None,
    ):
        self.makepkg = str(makepkg or MAKEPKG_BIN)
        self.config = str(config or MAKEPKG_CONF)
        self.output_dir = Path(output_dir or OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        package_dir: str | Path,
        force: bool = True,
    ) -> Path | None:
        """
        Run makepkg in the given package directory.

        Returns path to the built .pkg.tar.zst, or None on failure.
        """
        package_dir = Path(package_dir)

        cmd = [
            self.makepkg,
            "--config", self.config,
            "--nosign",
            "--skipchecksums",
            "--skipinteg",
            "--nodeps",
        ]

        if force:
            cmd.append("-f")

        env = {
            "PKGDEST": str(self.output_dir),
            "SRCDEST": str(package_dir / "src"),
            "BUILDDIR": str(package_dir / "build"),
            "PATH": subprocess.check_output(
                ["bash", "-c", "echo $PATH"],
                text=True,
            ).strip(),
            "HOME": str(Path.home()),
        }

        print(f"  -> Running: {' '.join(cmd)}")
        print(f"  -> Working dir: {package_dir}")
        print(f"  -> PKGDEST: {self.output_dir}")

        result = subprocess.run(
            cmd,
            cwd=package_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  -> makepkg FAILED (exit {result.returncode})")
            print(result.stdout)
            print(result.stderr)
            return None

        print("  -> makepkg succeeded ✓")

        # Find the built package
        pkg_files = list(
            self.output_dir.glob("*.pkg.tar.*")
        )

        if not pkg_files:
            print("  -> WARNING: No .pkg.tar.* found in output")
            return None

        # Return the most recently modified package
        latest = max(pkg_files, key=lambda p: p.stat().st_mtime)

        print(f"  -> Built: {latest.name}")

        return latest
