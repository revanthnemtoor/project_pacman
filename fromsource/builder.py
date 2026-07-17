"""
Source build orchestrator.

This is the main entry point for the fromsource build system.
It ties together the detector, generator, verifier, and makepkg
to build packages from source with a single command.

Usage:
    python3 -m fromsource.builder build <source_dir> --name <pkgname> --version <ver>
    python3 -m fromsource.builder build-all
    python3 -m fromsource.builder detect <source_dir>
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fromsource.detector import BuildDetector, BuildSystem
from fromsource.generator import PKGBUILDGenerator
from fromsource.verifier import PackageVerifier, VerificationResult


# -----------------------------------------------------------------
# Constants
# -----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROMSOURCE_DIR = PROJECT_ROOT / "fromsource"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPO_DIR = PROJECT_ROOT / "repo"

PACMAN_ROOT = Path("/opt/pacman")
MAKEPKG_BIN = PACMAN_ROOT / "bin" / "makepkg"
MAKEPKG_CONF = PACMAN_ROOT / "etc" / "makepkg.conf"
REPO_ADD_BIN = PACMAN_ROOT / "bin" / "repo-add"

REPO_DB = OUTPUT_DIR / "pacman.db.tar.gz"


class SourceBuilder:
    """
    Orchestrates the from-source build pipeline.

    For each source directory:
        1. Detect build system
        2. Generate PKGBUILD
        3. Run makepkg
        4. Verify package
        5. Add to repository database
    """

    def __init__(self):
        self.verifier = PackageVerifier()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def detect(self, source_dir: Path) -> None:
        """Detect and display the build system for a source directory."""

        profile = BuildDetector.detect(source_dir)

        print(f"  Source:      {source_dir}")
        print(f"  Build Type:  {profile.name}")

        if profile.system == BuildSystem.AUTOTOOLS:
            print(f"  configure:   {'yes' if profile.has_configure else 'no (needs autoreconf)'}")
            print(f"  autogen.sh:  {'yes' if profile.has_autogen else 'no'}")
        elif profile.system == BuildSystem.CARGO:
            print(f"  Cargo.toml:  {profile.cargo_toml}")
        elif profile.system == BuildSystem.GO:
            print(f"  go.mod:      {profile.go_mod}")

    def build(
        self,
        source_dir: Path,
        name: str,
        version: str,
        description: str = "",
        url: str = "",
        license: str = "custom",
        depends: list[str] | None = None,
        skip_verify: bool = False,
        build_override: str | None = None,
    ) -> Path | None:
        """
        Full pipeline: detect → generate → makepkg → verify → output.

        Returns the path to the built .pkg.tar.zst or None on failure.
        """

        source_dir = Path(source_dir).resolve()

        print()
        print("=" * 60)
        print(f"  Building {name} {version} from source")
        print("=" * 60)

        # Step 1: Detect
        print(f"\n==> Detecting build system")
        profile = BuildDetector.detect(source_dir)
        print(f"  -> Auto-detected: {profile.name}")

        # Allow explicit build system override
        if build_override:
            override_map = {s.name.lower(): s for s in BuildSystem}
            if build_override.lower() in override_map:
                profile.system = override_map[build_override.lower()]
                print(f"  -> Override:  {profile.name}")
            else:
                print(f"  -> WARNING: Unknown override '{build_override}', using auto-detected")

        if profile.system == BuildSystem.UNKNOWN:
            print(f"  -> ERROR: Could not detect build system in {source_dir}")
            return None

        # Step 2: Generate PKGBUILD
        print(f"\n==> Generating PKGBUILD")
        gen = PKGBUILDGenerator(
            name=name,
            version=version,
            description=description,
            url=url,
            license=license,
            depends=depends,
            source_dir=source_dir,
        )
        pkgbuild_content = gen.generate(profile)

        # Write PKGBUILD to a build directory
        build_dir = FROMSOURCE_DIR / name
        build_dir.mkdir(parents=True, exist_ok=True)

        pkgbuild_path = build_dir / "PKGBUILD"
        pkgbuild_path.write_text(pkgbuild_content)
        print(f"  -> Written to {pkgbuild_path}")

        # Step 3: Run makepkg
        print(f"\n==> Running makepkg")

        env = os.environ.copy()
        env["PKGDEST"] = str(OUTPUT_DIR)

        cmd = [
            str(MAKEPKG_BIN),
            "--config", str(MAKEPKG_CONF),
            "--sign",
            "--skipchecksums",
            "--skipinteg",
            "--nodeps",
            "-f",
        ]

        print(f"  -> Command: {' '.join(cmd)}")
        print(f"  -> Working dir: {build_dir}")

        result = subprocess.run(
            cmd,
            cwd=str(build_dir),
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  -> makepkg FAILED (exit {result.returncode})")
            print(f"  -> stdout: {result.stdout[-500:]}")
            print(f"  -> stderr: {result.stderr[-500:]}")
            return None

        print(f"  -> makepkg succeeded ✓")

        # Find the built package
        pkg_file = self._find_package(name, version)
        if not pkg_file:
            print(f"  -> ERROR: Could not find built package in {OUTPUT_DIR}")
            return None

        print(f"  -> Package: {pkg_file.name}")

        # Step 4: Verify
        if not skip_verify:
            print(f"\n==> Verifying package")
            vresult = self.verifier.verify_archive(pkg_file, name)
            self._print_verification(vresult)

            if not vresult.passed:
                print(f"  -> WARNING: Package has verification errors")

        # Step 5: Codesign all Mach-O binaries in the built package
        print(f"\n==> Codesigning binaries")
        self._codesign_package(pkg_file)

        return pkg_file

    def build_all(self, packages: list[dict]) -> list[Path]:
        """
        Build multiple packages in dependency order.

        Each entry in packages should be a dict with keys:
            source_dir, name, version, description, url, license, depends
        """

        built = []

        for pkg in packages:
            result = self.build(**pkg)
            if result:
                built.append(result)
            else:
                print(f"\n  !! FAILED to build {pkg['name']}")

        # Update repository database
        if built:
            print(f"\n==> Updating repository database")
            self._update_repo(built)

        print()
        print("=" * 60)
        print(f"  Build complete: {len(built)}/{len(packages)} packages")
        print("=" * 60)

        for p in built:
            print(f"  ✓ {p.name}")

        return built

    def _find_package(self, name: str, version: str) -> Path | None:
        """Find the most recently built .pkg.tar.zst for the given package."""

        pattern = f"{name}-{version}-*"
        matches = sorted(
            OUTPUT_DIR.glob(f"{pattern}.pkg.tar.zst"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return matches[0] if matches else None

    def _update_repo(self, packages: list[Path]) -> None:
        """Add built packages to the pacman repository database."""

        for pkg in packages:
            cmd = [
                str(REPO_ADD_BIN),
                "--sign",
                str(REPO_DB),
                str(pkg),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"  -> Failed to add {pkg.name}: {result.stderr}")
            else:
                print(f"  -> Added {pkg.name}")

    def _codesign_package(self, pkg_file: Path) -> None:
        """Extract, codesign Mach-O binaries, and repack."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Extract
            subprocess.run(
                ["tar", "-xf", str(pkg_file), "-C", str(tmpdir)],
                capture_output=True,
            )

            # Sign all Mach-O binaries
            signed = 0
            for path in tmpdir.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    if self.verifier._is_macho(path):
                        result = subprocess.run(
                            ["codesign", "--sign", "-", "--force", str(path)],
                            capture_output=True,
                        )
                        if result.returncode == 0:
                            signed += 1

            if signed > 0:
                # Repack the archive correctly (no ./ prefix) and compress with zstd
                # Use sh -c to expand the glob properly in the tmpdir
                pack_cmd = (
                    f"cd {tmpdir} && "
                    f"tar -cf - .PKGINFO .BUILDINFO .MTREE * 2>/dev/null | "
                    f"/opt/pacman/bin/zstd -c -T0 -19 -z > {pkg_file.absolute()}"
                )
                subprocess.run(pack_cmd, shell=True, check=True)
                print(f"  -> Signed {signed} binaries")
                
                # Delete old signature as it's now invalid
                sig_file = pkg_file.with_name(pkg_file.name + ".sig")
                if sig_file.exists():
                    sig_file.unlink()
            else:
                print(f"  -> No Mach-O binaries found to sign")

    def _print_verification(self, result: VerificationResult) -> None:
        """Print verification results."""

        status = "PASSED ✓" if result.passed else "FAILED ✗"
        print(f"  -> Verification: {status}")

        if result.binary_count > 0:
            print(f"  -> Binaries: {result.binary_count} ({result.signed_count} signed)")

        for err in result.errors:
            print(f"  -> ERROR: {err}")

        for warn in result.warnings:
            print(f"  -> WARN: {warn}")


# -----------------------------------------------------------------
# CLI
# -----------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="fromsource",
        description="Build packages from source using Arch-style PKGBUILDs",
    )
    sub = parser.add_subparsers(dest="command")

    # detect
    detect_p = sub.add_parser("detect", help="Detect build system")
    detect_p.add_argument("source_dir", type=Path)

    # build
    build_p = sub.add_parser("build", help="Build a single package")
    build_p.add_argument("source_dir", type=Path)
    build_p.add_argument("--name", required=True)
    build_p.add_argument("--version", required=True)
    build_p.add_argument("--description", default="")
    build_p.add_argument("--url", default="")
    build_p.add_argument("--license", default="custom")
    build_p.add_argument("--depends", nargs="*", default=[])

    args = parser.parse_args()
    builder = SourceBuilder()

    if args.command == "detect":
        builder.detect(args.source_dir)
    elif args.command == "build":
        builder.build(
            source_dir=args.source_dir,
            name=args.name,
            version=args.version,
            description=args.description,
            url=args.url,
            license=args.license,
            depends=args.depends,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
