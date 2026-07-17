"""
Homebrew bottle downloader and extractor.

Downloads pre-built bottles from the GitHub Container Registry (GHCR)
and extracts them into a staging directory ready for makepkg.

Bottle layout inside the tarball:
    <formula>/<version>/bin/...
    <formula>/<version>/lib/...
    <formula>/<version>/include/...

After extraction the Cellar prefix is stripped so the stage directory
contains just:
    bin/
    lib/
    include/
    ...
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from pacman_macos.constants import (
    CACHE_DIR,
    GHCR_DOMAIN,
    GHCR_TOKEN_URL,
    GHCR_PACKAGE_SCOPE,
)
from pacman_macos.formula import Formula


class BottleError(RuntimeError):
    pass


class BottleDownloader:
    """Download and extract Homebrew bottles from GHCR."""

    def __init__(self, cache_dir: str | Path | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    def download_and_stage(
        self,
        formula_name: str,
        stage_dir: str | Path,
    ) -> Path:
        """
        Download a bottle and extract it into stage_dir.

        Returns the path to the populated stage directory.
        """
        stage_dir = Path(stage_dir)
        stage_dir.mkdir(parents=True, exist_ok=True)

        formula = Formula(formula_name)

        url = formula.bottle_url()
        sha256 = formula.bottle_sha256()

        if not url or not sha256:
            raise BottleError(
                f"No bottle available for '{formula_name}'"
            )

        print(f"  -> Bottle URL: {url}")
        print(f"  -> Expected SHA256: {sha256[:16]}...")

        archive = self.download(formula_name, url, sha256)

        self.extract(archive, stage_dir, formula_name)

        return stage_dir

    # ----------------------------------------------------------

    def download(
        self,
        formula_name: str,
        url: str,
        expected_sha256: str,
    ) -> Path:
        """
        Download a bottle archive from GHCR.

        Uses cached copy if checksum matches.
        Returns path to the downloaded .tar.gz.
        """
        cache_file = self.cache_dir / f"{formula_name}.tar.gz"

        # Use cache if valid
        if cache_file.exists():
            if self._verify_sha256(cache_file, expected_sha256):
                print("  -> Using cached bottle")
                return cache_file
            else:
                print("  -> Cache invalid, re-downloading")
                cache_file.unlink()

        # Get GHCR auth token
        token = self._get_ghcr_token(formula_name)

        # Download the blob
        print(f"  -> Downloading bottle for {formula_name}...")

        self._download_blob(url, cache_file, token)

        # Verify checksum
        if not self._verify_sha256(cache_file, expected_sha256):
            cache_file.unlink(missing_ok=True)
            raise BottleError(
                f"SHA256 mismatch for {formula_name} bottle"
            )

        print("  -> SHA256 verified ✓")

        return cache_file

    # ----------------------------------------------------------

    def extract(
        self,
        archive: Path,
        dest_dir: Path,
        formula_name: str,
    ) -> Path:
        """
        Extract a bottle tarball and flatten the Cellar prefix.

        Homebrew bottles contain files under:
            <formula>/<version>/...

        We strip that prefix so dest_dir contains:
            bin/
            lib/
            ...
        """
        print(f"  -> Extracting to {dest_dir}")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(path=tmp_path)

            # Find the formula directory
            # Structure: <formula>/<version>/ or just <formula>/
            formula_dir = tmp_path / formula_name

            if not formula_dir.exists():
                # Try to find it
                contents = list(tmp_path.iterdir())
                if len(contents) == 1 and contents[0].is_dir():
                    formula_dir = contents[0]
                else:
                    raise BottleError(
                        f"Unexpected bottle layout: {[c.name for c in contents]}"
                    )

            # Find the version directory
            version_dirs = [
                d for d in formula_dir.iterdir()
                if d.is_dir()
            ]

            if len(version_dirs) == 1:
                source = version_dirs[0]
            elif version_dirs:
                # Pick the latest version directory
                source = sorted(version_dirs)[-1]
            else:
                source = formula_dir

            # Copy contents to dest
            for item in source.iterdir():
                dest_item = dest_dir / item.name

                if item.is_dir():
                    shutil.copytree(
                        item,
                        dest_item,
                        dirs_exist_ok=True,
                        symlinks=True,
                    )
                else:
                    shutil.copy2(item, dest_item)

        file_count = sum(
            1 for _ in dest_dir.rglob("*")
            if _.is_file()
        )
        print(f"  -> Staged {file_count} files")

        return dest_dir

    # ----------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------

    @staticmethod
    def _get_ghcr_token(formula_name: str) -> str:
        """Fetch an anonymous auth token from GHCR."""
        scope = f"repository:homebrew/core/{formula_name}:pull"

        proc = subprocess.run(
            [
                "curl",
                "-fsSL",
                f"{GHCR_TOKEN_URL}?service={GHCR_DOMAIN}&scope={scope}",
            ],
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise BottleError(
                f"Failed to get GHCR token: {proc.stderr}"
            )

        data = json.loads(proc.stdout)

        return data["token"]

    @staticmethod
    def _download_blob(
        url: str,
        dest: Path,
        token: str,
    ) -> None:
        """Download a blob from GHCR using curl."""
        proc = subprocess.run(
            [
                "curl",
                "-fsSL",
                "-o", str(dest),
                "-H", f"Authorization: Bearer {token}",
                url,
            ],
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise BottleError(
                f"Failed to download bottle: {proc.stderr}"
            )

    @staticmethod
    def _verify_sha256(path: Path, expected: str) -> bool:
        """Verify SHA256 checksum of a file."""
        sha256 = hashlib.sha256()

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        actual = sha256.hexdigest()

        return actual == expected
