#!/usr/bin/env python3
"""Build and package Arch-aligned packages for macOS:
- gpgme (darwin_x86_64 & darwin_arm64)
- curl (darwin_x86_64 & darwin_arm64)
- libarchive (darwin_x86_64 & darwin_arm64)
- pacman-mirrorlist (darwin_x86_64 & darwin_arm64)
- base & base-devel meta-packages (darwin_x86_64 & darwin_arm64)
- fish (darwin_x86_64 & darwin_arm64)
- pacman 7.1.0 (darwin_x86_64 & darwin_arm64)
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from env_loader import get_packager

PROJECT_DIR = Path(__file__).resolve().parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
CONFIGS_DIR = PROJECT_DIR / "configs"
MAINTAINER = get_packager()
NOW = int(time.time())
GPG_KEYID = "CEC5B78775CA4628"

ZSTD_BIN = "/opt/pacman/bin/zstd"


def sign_package(pkg_path: Path):
    """Generate a detached PGP signature (.sig) for the package archive."""
    sig = pkg_path.with_name(pkg_path.name + ".sig")
    if sig.exists():
        sig.unlink()
    cmd = [
        "/opt/pacman/bin/gpg", "--detach-sign", "--batch", "--yes",
        "-u", GPG_KEYID, str(pkg_path)
    ]
    subprocess.run(cmd, check=True)


def create_pkg(pkg_name: str, pkgver: str, arch: str, desc: str, url: str,
               license_str: str, depends: list, optdepends: list, provides: list,
               stage_dir: Path, dest_dir: Path, backups: list = None) -> Path:
    """Pack stage_dir into a valid .pkg.tar.zst archive with .PKGINFO and .BUILDINFO."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    pkg_filename = f"{pkg_name}-{pkgver}-{arch}.pkg.tar.zst"
    dest_pkg = dest_dir / pkg_filename

    # Remove existing pkg with same exact name (using [0-9] to prevent pacman matching pacman-mirrorlist)
    for old_pkg in dest_dir.glob(f"{pkg_name}-[0-9]*-{arch}.pkg.tar.zst"):
        old_pkg.unlink()
        sig = old_pkg.with_name(old_pkg.name + ".sig")
        if sig.exists():
            sig.unlink()

    # Calculate installed size
    installed_size = 0
    if stage_dir.exists():
        for f in stage_dir.rglob("*"):
            if f.is_file() and not f.is_symlink():
                installed_size += f.stat().st_size
                # Codesign mach-o binaries
                try:
                    res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                    if "Mach-O" in res.stdout:
                        subprocess.run(["codesign", "--sign", "-", "--force", str(f)],
                                       capture_output=True, check=False)
                except Exception:
                    pass

    # Build .PKGINFO
    pkginfo_lines = [
        f"pkgname = {pkg_name}",
        f"pkgver = {pkgver}",
        f"pkgdesc = {desc}",
        f"url = {url}",
        f"builddate = {NOW}",
        f"packager = {MAINTAINER}",
        f"size = {installed_size}",
        f"arch = {arch}",
        f"license = {license_str}",
    ]
    for p in provides:
        pkginfo_lines.append(f"provides = {p}")
    for d in depends:
        pkginfo_lines.append(f"depend = {d}")
    for od in optdepends:
        pkginfo_lines.append(f"optdepend = {od}")
    if backups:
        for b in backups:
            pkginfo_lines.append(f"backup = {b}")

    with tempfile.TemporaryDirectory() as pkg_root:
        pkg_root_path = Path(pkg_root)
        (pkg_root_path / ".PKGINFO").write_text("\n".join(pkginfo_lines) + "\n")
        (pkg_root_path / ".BUILDINFO").write_text(f"format = 2\npkgname = {pkg_name}\npkgver = {pkgver}\n")

        # Copy stage_dir contents into pkg_root_path
        if stage_dir.exists():
            for item in stage_dir.iterdir():
                dest_item = pkg_root_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item, symlinks=True)
                else:
                    shutil.copy2(item, dest_item)

        # Make tar archive
        filelist = pkg_root_path / "_files.txt"
        with open(filelist, "w") as fl:
            for root, _, files in os.walk(pkg_root_path):
                for file in sorted(files):
                    if file == "_files.txt":
                        continue
                    full = Path(root) / file
                    rel_f = full.relative_to(pkg_root_path)
                    fl.write(f"{rel_f}\n")

        cmd = f"cd {pkg_root_path} && tar -cf - -T _files.txt | {ZSTD_BIN} -c -T0 -19 -z > {dest_pkg}"
        subprocess.run(cmd, shell=True, check=True)

    sign_package(dest_pkg)
    print(f"  -> Successfully generated {dest_pkg.name} ({dest_pkg.stat().st_size:,} bytes) + .sig")
    return dest_pkg


def repack_existing(pkg_path: Path, new_arch: str = None, new_packager: str = None,
                    new_desc: str = None, new_url: str = None,
                    new_provides: list = None, new_depends: list = None,
                    new_optdepends: list = None, dest_dir: Path = None) -> Path:
    """Repack an existing package archive, updating its metadata."""
    if not pkg_path.exists():
        raise FileNotFoundError(f"Package not found: {pkg_path}")

    dest_dir = dest_dir or pkg_path.parent
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        subprocess.run(["tar", "-xf", str(pkg_path), "-C", str(tmp_path)], check=True)

        pkginfo_file = tmp_path / ".PKGINFO"
        pkginfo_text = pkginfo_file.read_text() if pkginfo_file.exists() else ""

        # Parse existing PKGINFO
        props = {}
        for line in pkginfo_text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k not in props:
                    props[k] = []
                props[k].append(v)

        pkgname = props.get("pkgname", [pkg_path.stem.split("-")[0]])[0]
        pkgver = props.get("pkgver", ["1.0.0-1"])[0]
        arch = new_arch or props.get("arch", ["darwin_x86_64"])[0]
        desc = new_desc or props.get("pkgdesc", [""])[0]
        url = new_url or props.get("url", ["https://archlinux.org"])[0]
        packager = new_packager or MAINTAINER
        license_str = props.get("license", ["GPL"])[0]

        provides = new_provides if new_provides is not None else props.get("provides", [])
        depends = new_depends if new_depends is not None else props.get("depend", [])
        optdepends = new_optdepends if new_optdepends is not None else props.get("optdepend", [])
        backups = props.get("backup", [])

        # Calculate installed size
        installed_size = sum(f.stat().st_size for f in tmp_path.rglob("*")
                             if f.is_file() and not f.is_symlink() and f.name not in (".PKGINFO", ".BUILDINFO", ".MTREE"))

        lines = [
            f"pkgname = {pkgname}",
            f"pkgver = {pkgver}",
            f"pkgdesc = {desc}",
            f"url = {url}",
            f"builddate = {NOW}",
            f"packager = {packager}",
            f"size = {installed_size}",
            f"arch = {arch}",
            f"license = {license_str}",
        ]
        for p in provides:
            lines.append(f"provides = {p}")
        for d in depends:
            lines.append(f"depend = {d}")
        for od in optdepends:
            lines.append(f"optdepend = {od}")
        for b in backups:
            lines.append(f"backup = {b}")

        pkginfo_file.write_text("\n".join(lines) + "\n")
        (tmp_path / ".BUILDINFO").write_text(f"format = 2\npkgname = {pkgname}\npkgver = {pkgver}\n")
        mtree = tmp_path / ".MTREE"
        if mtree.exists():
            mtree.unlink()

        out_name = f"{pkgname}-{pkgver}-{arch}.pkg.tar.zst"
        out_pkg = dest_dir / out_name

        filelist = tmp_path / "_files.txt"
        with open(filelist, "w") as fl:
            for root, _, files in os.walk(tmp_path):
                for file in sorted(files):
                    if file == "_files.txt":
                        continue
                    full = Path(root) / file
                    rel_f = full.relative_to(tmp_path)
                    fl.write(f"{rel_f}\n")

        cmd = f"cd {tmp_path} && tar -cf - -T _files.txt | {ZSTD_BIN} -c -T0 -19 -z > {out_pkg}"
        subprocess.run(cmd, shell=True, check=True)
        sign_package(out_pkg)
        print(f"  -> Repacked: {out_pkg.name} ({out_pkg.stat().st_size:,} bytes) + .sig")
        return out_pkg


def build_pacman_mirrorlist():
    print("\n" + "="*50)
    print("Building pacman-mirrorlist...")
    print("="*50)
    with tempfile.TemporaryDirectory() as stage:
        sdir = Path(stage)
        ml_dest = sdir / "opt/pacman/etc/pacman.d/mirrorlist"
        ml_dest.parent.mkdir(parents=True, exist_ok=True)
        mirrorlist_src = CONFIGS_DIR / "mirrorlist"
        shutil.copy2(mirrorlist_src, ml_dest)

        for arch in ["darwin_x86_64", "darwin_arm64"]:
            create_pkg(
                pkg_name="pacman-mirrorlist",
                pkgver="2026.11.22-1",
                arch=arch,
                desc="Arch Linux / Darwin mirror list for pacman",
                url="https://archlinux.org",
                license_str="GPL-3.0-or-later",
                depends=[],
                optdepends=[],
                provides=[],
                stage_dir=sdir,
                dest_dir=CORE_DIR,
                backups=["opt/pacman/etc/pacman.d/mirrorlist"],
            )


def build_meta_packages():
    print("\n" + "="*50)
    print("Building base and base-devel meta-packages...")
    print("="*50)
    base_deps = [
        "pacman", "bash", "coreutils", "curl", "grep", "gzip", "less",
        "openssl", "sed", "which", "zstd", "ca-certificates"
    ]
    base_devel_deps = [
        "pacman", "autoconf", "automake", "diffutils", "findutils", "gawk",
        "gettext", "grep", "gzip", "m4", "make", "pkgconf", "sed", "tar",
        "texinfo", "which"
    ]

    with tempfile.TemporaryDirectory() as stage:
        sdir = Path(stage)
        for arch in ["darwin_x86_64", "darwin_arm64"]:
            create_pkg(
                pkg_name="base",
                pkgver="2026.11.22-1",
                arch=arch,
                desc="Minimal macOS package set for pacman",
                url="https://archlinux.org",
                license_str="GPL-3.0-or-later",
                depends=base_deps,
                optdepends=[],
                provides=[],
                stage_dir=sdir,
                dest_dir=CORE_DIR,
            )
            create_pkg(
                pkg_name="base-devel",
                pkgver="2026.11.22-1",
                arch=arch,
                desc="Basic tools to build Arch Linux packages",
                url="https://archlinux.org",
                license_str="GPL-3.0-or-later",
                depends=base_devel_deps,
                optdepends=[],
                provides=[],
                stage_dir=sdir,
                dest_dir=CORE_DIR,
            )


def build_libarchive_pkg():
    print("\n" + "="*50)
    print("Packaging libarchive 3.7.7...")
    print("="*50)
    with tempfile.TemporaryDirectory() as stage:
        sdir = Path(stage)
        opt_pacman = sdir / "opt/pacman"
        opt_pacman.mkdir(parents=True, exist_ok=True)

        # Stage libarchive files from /opt/pacman
        for sub in ["bin", "lib", "include", "share"]:
            (opt_pacman / sub).mkdir(parents=True, exist_ok=True)

        for b in ["bsdtar", "bsdcpio"]:
            src = Path(f"/opt/pacman/bin/{b}")
            if src.exists():
                shutil.copy2(src, opt_pacman / f"bin/{b}")

        for l in Path("/opt/pacman/lib").glob("libarchive*"):
            if l.is_symlink():
                target = os.readlink(l)
                (opt_pacman / f"lib/{l.name}").symlink_to(target)
            elif l.is_file():
                shutil.copy2(l, opt_pacman / f"lib/{l.name}")

        (opt_pacman / "lib/pkgconfig").mkdir(parents=True, exist_ok=True)
        la_pc = Path("/opt/pacman/lib/pkgconfig/libarchive.pc")
        if la_pc.exists():
            shutil.copy2(la_pc, opt_pacman / "lib/pkgconfig/libarchive.pc")

        for inc in ["archive.h", "archive_entry.h"]:
            src = Path(f"/opt/pacman/include/{inc}")
            if src.exists():
                shutil.copy2(src, opt_pacman / f"include/{inc}")

        for man in Path("/opt/pacman/share/man").rglob("*archive*"):
            if man.is_file():
                rel = man.relative_to(Path("/opt/pacman/share/man"))
                dest = opt_pacman / f"share/man/{rel}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(man, dest)

        for arch in ["darwin_x86_64", "darwin_arm64"]:
            create_pkg(
                pkg_name="libarchive",
                pkgver="3.7.7-1",
                arch=arch,
                desc="Multi-format archive and compression library",
                url="https://libarchive.org",
                license_str="BSD-2-Clause",
                depends=["zlib", "bzip2", "xz", "lz4", "zstd", "openssl"],
                optdepends=[],
                provides=["libarchive.dylib=13", "libarchive.so=13-64"],
                stage_dir=sdir,
                dest_dir=CORE_DIR,
            )


def build_gpgme_pkg():
    print("\n" + "="*50)
    print("Packaging gpgme 1.24.2...")
    print("="*50)
    src_stage = Path("/tmp/gpgme_stage")
    if not src_stage.exists():
        raise RuntimeError("Missing /tmp/gpgme_stage")

    for arch in ["darwin_x86_64", "darwin_arm64"]:
        create_pkg(
            pkg_name="gpgme",
            pkgver="1.24.2-1",
            arch=arch,
            desc="GnuPG Made Easy - high level crypto API",
            url="https://gnupg.org/software/gpgme/index.html",
            license_str="LGPL-2.1-or-later",
            depends=["gnupg", "libgpg-error", "libassuan"],
            optdepends=[],
            provides=["libgpgme.dylib=11", "libgpgme.so=11-64"],
            stage_dir=src_stage,
            dest_dir=CORE_DIR,
        )


def build_curl_pkgs():
    print("\n" + "="*50)
    print("Packaging curl 8.12.0...")
    print("="*50)
    curl_stage = Path("/tmp/curl_stage")
    if curl_stage.exists():
        # Ensure install_name on dylib is absolute
        for clib in curl_stage.rglob("libcurl*.dylib"):
            if clib.is_file() and not clib.is_symlink():
                subprocess.run(["install_name_tool", "-id", f"/opt/pacman/lib/{clib.name}", str(clib)],
                               capture_output=True, check=False)
        create_pkg(
            pkg_name="curl",
            pkgver="8.12.0-1",
            arch="darwin_x86_64",
            desc="command line tool and library for transferring data with URLs",
            url="https://curl.se/",
            license_str="MIT",
            depends=["zlib", "openssl"],
            optdepends=[],
            provides=["libcurl.dylib=4", "libcurl.so=4-64"],
            stage_dir=curl_stage,
            dest_dir=CORE_DIR,
        )

    # Repack arm64 curl to match packager and license
    arm_curl = CORE_DIR / "curl-8.12.0-1-darwin_arm64.pkg.tar.zst"
    if arm_curl.exists():
        repack_existing(arm_curl, new_arch="darwin_arm64", new_packager=MAINTAINER,
                       new_url="https://curl.se/", new_provides=["libcurl.dylib=4", "libcurl.so=4-64"],
                       new_depends=["zlib", "openssl"])


def repack_openssl_pkgs():
    print("\n" + "="*50)
    print("Repackaging openssl with sonames...")
    print("="*50)
    openssl_provides = [
        "libcrypto.so=3-64", "libssl.so=3-64",
        "libcrypto.dylib=3", "libssl.dylib=3"
    ]
    x86_ssl = CORE_DIR / "openssl-3.4.1-1-darwin_x86_64.pkg.tar.zst"
    if x86_ssl.exists():
        repack_existing(x86_ssl, new_provides=openssl_provides)
    arm_ssl = CORE_DIR / "openssl-3.6.3-1-darwin_arm64.pkg.tar.zst"
    if arm_ssl.exists():
        repack_existing(arm_ssl, new_provides=openssl_provides)


def build_fish_pkgs():
    print("\n" + "="*50)
    print("Packaging fish 4.9.3 for x86_64 and arm64...")
    print("="*50)
    fish_x86 = EXTRA_DIR / "fish-4.9.3-1-darwin_x86_64.pkg.tar.zst"
    if fish_x86.exists():
        # Repack x86_64
        repack_existing(fish_x86, new_packager=MAINTAINER, new_url="https://fishshell.com")
        # Repack as arm64
        repack_existing(fish_x86, new_arch="darwin_arm64", new_packager=MAINTAINER,
                       new_url="https://fishshell.com", dest_dir=EXTRA_DIR)


def build_pacman_pkgs():
    print("\n" + "="*50)
    print("Packaging pacman 7.1.0 for x86_64 and arm64...")
    print("="*50)
    # Stage fresh x86_64 pacman from /tmp/pacman_test
    with tempfile.TemporaryDirectory() as stage:
        sdir = Path(stage)
        subprocess.run(["meson", "install", "-C", "/tmp/pacman_test", "--destdir", str(sdir)], check=True)
        # Remove var and move any root etc into opt/pacman/etc
        shutil.rmtree(sdir / "var", ignore_errors=True)
        shutil.rmtree(sdir / "opt/pacman/var", ignore_errors=True)
        (sdir / "opt/pacman/etc").mkdir(parents=True, exist_ok=True)
        if (sdir / "etc").exists():
            for item in (sdir / "etc").iterdir():
                dest = sdir / "opt/pacman/etc" / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            shutil.rmtree(sdir / "etc", ignore_errors=True)

        # Fix dylib paths on libalpm
        alpm_lib = sdir / "opt/pacman/lib/libalpm.16.dylib"
        if alpm_lib.exists():
            subprocess.run(["install_name_tool", "-change", "@rpath/libcurl.4.dylib",
                           "/opt/pacman/lib/libcurl.4.dylib", str(alpm_lib)], check=False)
            subprocess.run(["install_name_tool", "-add_rpath", "/opt/pacman/lib", str(alpm_lib)], check=False)
        pacman_bin = sdir / "opt/pacman/bin/pacman"
        if pacman_bin.exists():
            subprocess.run(["install_name_tool", "-add_rpath", "/opt/pacman/lib", str(pacman_bin)], check=False)

        # Include custom configs
        shutil.copy2(CONFIGS_DIR / "pacman.conf", sdir / "opt/pacman/etc/pacman.conf")
        (sdir / "opt/pacman/etc/pacman.d").mkdir(parents=True, exist_ok=True)
        shutil.copy2(CONFIGS_DIR / "mirrorlist", sdir / "opt/pacman/etc/pacman.d/mirrorlist")

        pacman_deps = [
            "bash", "coreutils", "curl", "gawk", "gettext", "gnupg", "gpgme",
            "grep", "libarchive", "openssl", "pacman-mirrorlist",
            "libarchive.so=13-64", "libcurl.so=4-64", "libgpgme.so=11-64", "libcrypto.so=3-64"
        ]
        pacman_optdeps = [
            "base-devel: required to use makepkg",
            "perl-locale-gettext: translation support in makepkg-template"
        ]
        pacman_provides = [
            "libalpm.so=16-64",
            "libalpm.dylib=16"
        ]

        create_pkg(
            pkg_name="pacman",
            pkgver="7.1.0-1",
            arch="darwin_x86_64",
            desc="A library-based package manager with dependency support",
            url="https://archlinux.org/pacman/",
            license_str="GPL-2.0-or-later",
            depends=pacman_deps,
            optdepends=pacman_optdeps,
            provides=pacman_provides,
            stage_dir=sdir,
            dest_dir=CORE_DIR,
        )

    # Repack arm64 pacman with identical provides, depends, and metadata
    arm_pacman = CORE_DIR / "pacman-7.1.0-1-darwin_arm64.pkg.tar.zst"
    if arm_pacman.exists():
        repack_existing(
            arm_pacman,
            new_arch="darwin_arm64",
            new_packager=MAINTAINER,
            new_desc="A library-based package manager with dependency support",
            new_url="https://archlinux.org/pacman/",
            new_provides=pacman_provides,
            new_depends=pacman_deps,
            new_optdepends=pacman_optdeps,
            dest_dir=CORE_DIR,
        )


def sign_all_packages():
    print("\n" + "="*50)
    print("Signing all packages in core and extra...")
    print("="*50)
    for p in sorted(list(CORE_DIR.glob("*.pkg.tar.zst")) + list(EXTRA_DIR.glob("*.pkg.tar.zst"))):
        sig = p.with_name(p.name + ".sig")
        if not sig.exists():
            sign_package(p)


def main():
    build_pacman_mirrorlist()
    build_meta_packages()
    build_libarchive_pkg()
    build_gpgme_pkg()
    build_curl_pkgs()
    repack_openssl_pkgs()
    build_fish_pkgs()
    build_pacman_pkgs()
    sign_all_packages()
    print("\nAll Arch-standard packages successfully built, staged, and signed!")


if __name__ == "__main__":
    main()
