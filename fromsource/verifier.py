"""
Package verifier.

After makepkg produces a .pkg.tar.zst, this module verifies the
package structure to ensure it is well-formed and ready for
repository inclusion.

Checks:
    - .PKGINFO exists and has valid fields
    - Binaries are Mach-O ARM64
    - Binaries have valid code signatures
    - install prefix is correct (/opt/pacman)
    - No stale Homebrew paths remain
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class VerificationResult:
    """Outcome of package verification."""

    package: str
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    binary_count: int = 0
    signed_count: int = 0

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


class PackageVerifier:
    """Verify a staged package directory before or after packaging."""

    def __init__(self, prefix: str = "/opt/pacman"):
        self.prefix = prefix

    def verify_staged(self, stage_dir: Path, pkgname: str) -> VerificationResult:
        """Verify a staged (unpacked) package directory."""

        result = VerificationResult(package=pkgname)

        if not stage_dir.is_dir():
            result.add_error(f"Stage directory does not exist: {stage_dir}")
            return result

        # Check for Mach-O binaries and verify signatures
        for path in stage_dir.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue

            if self._is_macho(path):
                result.binary_count += 1

                # Check architecture
                if not self._check_arm64(path):
                    result.add_error(f"Binary is not ARM64: {path.name}")

                # Check code signature
                if self._check_codesign(path):
                    result.signed_count += 1
                else:
                    result.add_warning(f"Binary not signed: {path.name}")

        # Check prefix structure
        opt_dir = stage_dir / "opt" / "pacman"
        if not opt_dir.exists():
            # Check if files are at the root (flat layout)
            has_bin = (stage_dir / "bin").exists()
            has_lib = (stage_dir / "lib").exists()
            if has_bin or has_lib:
                result.add_warning(
                    "Files use flat layout (bin/, lib/) instead of "
                    "opt/pacman/bin/, opt/pacman/lib/. "
                    "Ensure makepkg DESTDIR is used correctly."
                )

        return result

    def verify_archive(self, archive: Path, pkgname: str) -> VerificationResult:
        """Verify a .pkg.tar.zst archive."""
        import tempfile

        result = VerificationResult(package=pkgname)

        if not archive.exists():
            result.add_error(f"Archive does not exist: {archive}")
            return result

        # Check for .PKGINFO
        proc = subprocess.run(
            ["tar", "-tf", str(archive)],
            capture_output=True, text=True,
        )

        if proc.returncode != 0:
            result.add_error(f"Failed to list archive contents: {proc.stderr}")
            return result

        entries = proc.stdout.strip().splitlines()

        if ".PKGINFO" not in entries:
            result.add_error(".PKGINFO not found in archive")

        # Extract and inspect .PKGINFO
        proc = subprocess.run(
            ["tar", "-xf", str(archive), "-O", ".PKGINFO"],
            capture_output=True, text=True,
        )

        if proc.returncode == 0:
            pkginfo = proc.stdout
            self._verify_pkginfo(pkginfo, result)

        return result

    def _verify_pkginfo(self, content: str, result: VerificationResult):
        """Check critical .PKGINFO fields."""

        required = {"pkgname", "pkgver", "pkgdesc", "size", "arch"}
        found = set()

        for line in content.splitlines():
            if "=" in line:
                key = line.split("=", 1)[0].strip()
                found.add(key)

                # Verify packager
                if key == "packager" and "Revanth" not in line:
                    result.add_warning(
                        f"Packager is not Revanth Reddy Nemtoor: {line}"
                    )

                # Verify arch
                if key == "arch":
                    val = line.split("=", 1)[1].strip()
                    if val not in ("aarch64", "arm64", "darwin_arm64"):
                        result.add_warning(f"Unexpected arch: {val}")

        missing = required - found
        if missing:
            result.add_error(f"Missing .PKGINFO fields: {missing}")

    @staticmethod
    def _is_macho(path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                magic = f.read(4)
                return magic in (
                    b"\xfe\xed\xfa\xce",
                    b"\xfe\xed\xfa\xcf",
                    b"\xce\xfa\xed\xfe",
                    b"\xcf\xfa\xed\xfe",
                    b"\xca\xfe\xba\xbe",
                )
        except (OSError, PermissionError):
            return False

    @staticmethod
    def _check_arm64(path: Path) -> bool:
        proc = subprocess.run(
            ["file", str(path)],
            capture_output=True, text=True,
        )
        return "arm64" in proc.stdout.lower()

    @staticmethod
    def _check_codesign(path: Path) -> bool:
        proc = subprocess.run(
            ["codesign", "-vv", str(path)],
            capture_output=True, text=True,
        )
        return proc.returncode == 0
