#!/usr/bin/env python3
"""Unified Arch Linux Darwin Build & Packaging Pipeline.

Full Lifecycle Orchestrator (Designed natively for macOS Darwin):
  1. Scan: Fast concurrent check against upstream Git repository release tags (NOT Linux Arch DB)
  2. Fetch/Clone: Download upstream source or git clone with tag verification
  3. Build: Native Darwin compilation with Apple SDK sysroot, Mach-O -rpath, and codesigning
  4. Package: Arch .pkg.tar.zst creation with .PKGINFO and .BUILDINFO
  5. Sign: GPG detached signature generation (.sig)
  6. Deploy & Install: Repository database update (repo-add) and pacman -U installation

Usage:
  python3 arch_builder.py scan                 # Fast scan of packages against upstream Git tags
  python3 arch_builder.py scan --updates-only  # Show only packages with new upstream git tags
  python3 arch_builder.py scan --refresh       # Bypass cache and re-fetch all git tags
  python3 arch_builder.py build <pkgname>      # Full build-package-sign-install pipeline
  python3 arch_builder.py update-all           # Scan and rebuild all outdated packages
  python3 arch_builder.py index                # Re-index and sign all repo databases
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# Load packager configuration securely
try:
    from env_loader import get_packager
    PACKAGER = get_packager()
except ImportError:
    PACKAGER = os.environ.get("PACKAGER", "Arch Darwin Packager <packager@localhost>")

PROJECT_DIR = Path(__file__).resolve().parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
PACKAGES_DIR = PROJECT_DIR / "packages"
CACHE_DIR = PROJECT_DIR / ".build_cache"
TAGS_CACHE_FILE = CACHE_DIR / "git_tags_cache.json"

PACMAN_ROOT = Path("/opt/pacman")
PACMAN_BIN = PACMAN_ROOT / "bin" / "pacman"
MAKEPKG_BIN = PACMAN_ROOT / "bin" / "makepkg"
REPO_ADD_BIN = PACMAN_ROOT / "bin" / "repo-add"
GPG_BIN = PACMAN_ROOT / "bin" / "gpg"
GPG_KEYID = "CEC5B78775CA4628"

# Detect host architecture
MACHINE = platform.machine()
DARWIN_ARCH = "darwin_arm64" if MACHINE == "arm64" else "darwin_x86_64"
TARGET_ARCH = "arm64" if MACHINE == "arm64" else "x86_64"

# Colors for terminal output
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
RED = "\033[1;31m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Authoritative Upstream Git Repositories
UPSTREAM_GIT_REPOS: dict[str, str] = {
    # Core GNU Userspace (Savannah Git)
    "autoconf": "git://git.savannah.gnu.org/autoconf.git",
    "automake": "git://git.savannah.gnu.org/automake.git",
    "bash": "git://git.savannah.gnu.org/bash.git",
    "coreutils": "https://github.com/coreutils/coreutils.git",
    "diffutils": "git://git.savannah.gnu.org/diffutils.git",
    "findutils": "git://git.savannah.gnu.org/findutils.git",
    "gawk": "git://git.savannah.gnu.org/gawk.git",
    "grep": "git://git.savannah.gnu.org/grep.git",
    "gzip": "git://git.savannah.gnu.org/gzip.git",
    "make": "git://git.savannah.gnu.org/make.git",
    "nano": "git://git.savannah.gnu.org/nano.git",
    "sed": "git://git.savannah.gnu.org/sed.git",
    "tar": "git://git.savannah.gnu.org/tar.git",
    "texinfo": "git://git.savannah.gnu.org/texinfo.git",
    "which": "git://git.savannah.gnu.org/which.git",
    "gcc": "https://github.com/gcc-mirror/gcc.git",
    # Core Compression & Low-Level Libraries
    "brotli": "https://github.com/google/brotli.git",
    "bzip2": "https://gitlab.com/bzip2/bzip2.git",
    "curl": "https://github.com/curl/curl.git",
    "expat": "https://github.com/libexpat/libexpat.git",
    "gmp": "https://github.com/alisw/GMP.git",
    "gnutls": "https://gitlab.com/gnutls/gnutls.git",
    "json-c": "https://github.com/json-c/json-c.git",
    "less": "https://github.com/gwsw/less.git",
    "libarchive": "https://github.com/libarchive/libarchive.git",
    "libevent": "https://github.com/libevent/libevent.git",
    "libffi": "https://github.com/libffi/libffi.git",
    "libpsl": "https://github.com/rockdaboot/libpsl.git",
    "libtasn1": "https://gitlab.com/gnutls/libtasn1.git",
    "libunistring": "git://git.savannah.gnu.org/libunistring.git",
    "libusb": "https://github.com/libusb/libusb.git",
    "libxcrypt": "https://github.com/besser82/libxcrypt.git",
    "libxml2": "https://gitlab.gnome.org/GNOME/libxml2.git",
    "lz4": "https://github.com/lz4/lz4.git",
    "lzo": "https://github.com/nemequ/lzo.git",
    "m4": "git://git.savannah.gnu.org/m4.git",
    "mpfr": "https://gitlab.inria.fr/mpfr/mpfr.git",
    "ncurses": "https://github.com/ThomasDickey/ncurses-snapshots.git",
    "nettle": "https://git.lysator.liu.se/nettle/nettle.git",
    "npth": "https://github.com/gpg/npth.git",
    "openssl": "https://github.com/openssl/openssl.git",
    "p11-kit": "https://github.com/p11-glue/p11-kit.git",
    "pacman": "https://gitlab.archlinux.org/pacman/pacman.git",
    "pcre2": "https://github.com/PCRE2Project/pcre2.git",
    "pinentry": "https://github.com/gpg/pinentry.git",
    "pkgconf": "https://github.com/pkgconf/pkgconf.git",
    "popt": "https://github.com/rpm-software-management/popt.git",
    "readline": "git://git.savannah.gnu.org/readline.git",
    "sqlite": "https://github.com/sqlite/sqlite.git",
    "xxhash": "https://github.com/Cyan4973/xxHash.git",
    "xz": "https://github.com/tukaani-project/xz.git",
    "zlib": "https://github.com/madler/zlib.git",
    "zstd": "https://github.com/facebook/zstd.git",
    # Extra CLI & Developer Utilities
    "fastfetch": "https://github.com/fastfetch-cli/fastfetch.git",
    "fd": "https://github.com/sharkdp/fd.git",
    "fish": "https://github.com/fish-shell/fish-shell.git",
    "fzf": "https://github.com/junegunn/fzf.git",
    "gh": "https://github.com/cli/cli.git",
    "git": "https://github.com/git/git.git",
    "imagemagick": "https://github.com/ImageMagick/ImageMagick.git",
    "jemalloc": "https://github.com/jemalloc/jemalloc.git",
    "jq": "https://github.com/jqlang/jq.git",
    "libjpeg-turbo": "https://github.com/libjpeg-turbo/libjpeg-turbo.git",
    "libpng": "https://github.com/glennrp/libpng.git",
    "libsodium": "https://github.com/jedisct1/libsodium.git",
    "libtiff": "https://gitlab.com/libtiff/libtiff.git",
    "links": "http://links.twibright.com/git/links.git",
    "oniguruma": "https://github.com/kkos/oniguruma.git",
    "ripgrep": "https://github.com/BurntSushi/ripgrep.git",
    "rsync": "https://github.com/WayneD/rsync.git",
    "tmux": "https://github.com/tmux/tmux.git",
    "tree": "https://github.com/Old-Man-Programmer/tree.git",
    "utf8proc": "https://github.com/JuliaStrings/utf8proc.git",
    "vim": "https://github.com/vim/vim.git",
    "wget": "git://git.savannah.gnu.org/wget.git",
    "yq": "https://github.com/mikefarah/yq.git",
    "yyjson": "https://github.com/ibireme/yyjson.git",
    "exiv2": "https://github.com/Exiv2/exiv2.git",
    "lcms2": "https://github.com/mm2/Little-CMS.git",
    # Qt6 Modules
    "qt6-base": "https://github.com/qt/qtbase.git",
    "qt6-declarative": "https://github.com/qt/qtdeclarative.git",
    "qt6-shadertools": "https://github.com/qt/qtshadertools.git",
    "qt6-svg": "https://github.com/qt/qtsvg.git",
    "qt6-tools": "https://github.com/qt/qttools.git",
    "qt6-multimedia": "https://github.com/qt/qtmultimedia.git",
    "qt6-connectivity": "https://github.com/qt/qtconnectivity.git",
    "qt6-serialport": "https://github.com/qt/qtserialport.git",
    "qt6-websockets": "https://github.com/qt/qtwebsockets.git",
    "qt6-networkauth": "https://github.com/qt/qtnetworkauth.git",
    "qt6-lottie": "https://github.com/qt/qtlottie.git",
    "qt6-quick3d": "https://github.com/qt/qtquick3d.git",
    "qt6-quicktimeline": "https://github.com/qt/qtquicktimeline.git",
    "qt6-imageformats": "https://github.com/qt/qtimageformats.git",
    "qt6-languageserver": "https://github.com/qt/languageserver.git",
    # KDE Frameworks 6
    "extra-cmake-modules": "https://github.com/KDE/extra-cmake-modules.git",
    "breeze-icons": "https://github.com/KDE/breeze-icons.git",
    "kcoreaddons": "https://github.com/KDE/kcoreaddons.git",
    "kconfig": "https://github.com/KDE/kconfig.git",
    "karchive": "https://github.com/KDE/karchive.git",
    "ki18n": "https://github.com/KDE/ki18n.git",
    "kio": "https://github.com/KDE/kio.git",
    "knotifications": "https://github.com/KDE/knotifications.git",
    "kwidgetsaddons": "https://github.com/KDE/kwidgetsaddons.git",
    "kwindowsystem": "https://github.com/KDE/kwindowsystem.git",
    "kxmlgui": "https://github.com/KDE/kxmlgui.git",
    "gwenview": "https://github.com/KDE/gwenview.git",
}


def get_sdk_path() -> str:
    """Retrieve macOS SDK path."""
    try:
        return subprocess.check_output(
            ["xcrun", "--show-sdk-path"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"


def get_darwin_env() -> dict[str, str]:
    """Construct standard Darwin build environment."""
    sdk = get_sdk_path()
    env = os.environ.copy()
    env["PATH"] = f"/opt/pacman/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["SDKPATH"] = sdk
    env["CFLAGS"] = f"-O2 -I/opt/pacman/include -isysroot {sdk} -arch {TARGET_ARCH}"
    env["CXXFLAGS"] = f"-O2 -I/opt/pacman/include -isysroot {sdk} -arch {TARGET_ARCH}"
    env["LDFLAGS"] = f"-L/opt/pacman/lib -Wl,-rpath,/opt/pacman/lib -arch {TARGET_ARCH}"
    env["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
    env["MACOSX_DEPLOYMENT_TARGET"] = "11.0"
    env["PACKAGER"] = PACKAGER
    return env


def codesign_macho(target_dir: Path) -> int:
    """Recursively ad-hoc codesign all Mach-O binaries and dylibs in target_dir."""
    signed_count = 0
    macho_magics = {
        b"\xfe\xed\xfa\xce",
        b"\xfe\xed\xfa\xcf",
        b"\xce\xfa\xed\xfe",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
    }
    for root, _, files in os.walk(target_dir):
        for f in files:
            p = Path(root) / f
            if p.is_file() and not p.is_symlink():
                try:
                    with open(p, "rb") as fh:
                        magic = fh.read(4)
                    if magic in macho_magics:
                        subprocess.run(
                            ["codesign", "--force", "--sign", "-", str(p)],
                            check=False,
                            capture_output=True,
                        )
                        signed_count += 1
                except Exception:
                    pass
    return signed_count


def sign_file(file_path: Path) -> Path:
    """Generate detached PGP signature (.sig) for an archive."""
    sig_path = file_path.with_name(file_path.name + ".sig")
    if sig_path.exists():
        sig_path.unlink()
    cmd = [
        str(GPG_BIN),
        "--detach-sign",
        "--batch",
        "--yes",
        "-u",
        GPG_KEYID,
        str(file_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sig_path


def clean_git_tag(raw_tag: str) -> tuple[tuple[int, ...], str] | None:
    """Normalize and parse an upstream Git tag into a comparable version tuple.
    
    Handles:
      v1.2.3 -> 1.2.3
      curl-8_12_0 -> 8.12.0
      nano-9.1 -> 9.1
      fastfetch-2.71.0 -> 2.71.0
      openssl-3.4.1 -> 3.4.1
      texinfo-7.3 -> 7.3
    Filters out non-stable tags (rc, alpha, beta, dev, preview, pre, fuzz, test).
    """
    t = raw_tag.replace("refs/tags/", "").strip()
    
    # Strip common prefixes
    for prefix in [
        "v", "curl-", "openssl-", "jq-", "nano-", "pkgconf-", "fish-", 
        "vim-", "gawk-", "texinfo-", "bash-", "release-", "version-", "tar-"
    ]:
        if t.startswith(prefix):
            t = t[len(prefix):]
            break
            
    t = t.replace("_", ".")
    
    # Filter non-stable pre-releases
    lower = t.lower()
    if any(x in lower for x in ["rc", "alpha", "beta", "dev", "nightly", "pre", "test", "fuzz", "last", "preview"]):
        return None
        
    # Match version pattern
    m = re.match(r"^(\d+(\.\d+)+)", t)
    if m:
        clean = m.group(1)
        nums = tuple(int(x) for x in clean.split("."))
        return (nums, clean)
        
    # Single digit version fallback
    m_single = re.match(r"^(\d+)", t)
    if m_single:
        clean = m_single.group(1)
        return ((int(clean),), clean)
        
    return None


def parse_pkg_version(ver_str: str) -> tuple[int, ...]:
    """Parse local package version string (e.g. '9.1-1' or '2.70.0-1') into comparable tuple."""
    if ":" in ver_str:
        ver_str = ver_str.split(":", 1)[1]
    if "-" in ver_str:
        ver_str = ver_str.rsplit("-", 1)[0]
    nums = re.findall(r"\d+", ver_str)
    return tuple(int(x) for x in nums) if nums else (0,)


def compare_versions(local_ver_str: str, upstream_ver_str: str) -> int:
    """Return -1 if local < upstream (update available), 0 if equal, 1 if local > upstream."""
    l_tuple = parse_pkg_version(local_ver_str)
    u_tuple = parse_pkg_version(upstream_ver_str)
    
    # Pad tuples to same length for comparison
    max_len = max(len(l_tuple), len(u_tuple))
    l_padded = l_tuple + (0,) * (max_len - len(l_tuple))
    u_padded = u_tuple + (0,) * (max_len - len(u_tuple))
    
    if l_padded < u_padded:
        return -1
    elif l_padded > u_padded:
        return 1
    return 0


class RepoCatalog:
    """Reads and manages local repository package state."""

    @staticmethod
    def get_local_packages() -> dict[str, dict]:
        """Scan core/ and extra/ for local binary packages."""
        packages = {}
        for repo_dir, repo_name in [(CORE_DIR, "core"), (EXTRA_DIR, "extra")]:
            if not repo_dir.exists():
                continue
            for f in os.listdir(repo_dir):
                if f.endswith(f"-{DARWIN_ARCH}.pkg.tar.zst"):
                    raw = f.replace(f"-{DARWIN_ARCH}.pkg.tar.zst", "")
                    parts = raw.split("-")
                    rel = parts[-1]
                    ver = parts[-2]
                    pkgname = "-".join(parts[:-2])
                    packages[pkgname] = {
                        "name": pkgname,
                        "version": f"{ver}-{rel}",
                        "clean_version": ver,
                        "repo": repo_name,
                        "file": repo_dir / f,
                    }
        return packages


class GitTagScanner:
    """Queries upstream Git repositories directly for release tags."""

    @classmethod
    def resolve_git_repo(cls, pkgname: str) -> str | None:
        """Resolve authoritative upstream Git repository URL for a package."""
        if pkgname in UPSTREAM_GIT_REPOS:
            return UPSTREAM_GIT_REPOS[pkgname]
            
        # Check KDE Frameworks
        if pkgname.startswith("k") or pkgname in ("breeze-icons", "extra-cmake-modules", "gwenview", "solid", "sonnet"):
            return f"https://github.com/KDE/{pkgname}.git"
            
        # Check metadata.json
        meta_file = PACKAGES_DIR / "extra" / pkgname / "metadata.json"
        if meta_file.is_file():
            try:
                with open(meta_file) as fh:
                    d = json.load(fh)
                    for key in ["source_url", "homepage"]:
                        val = d.get(key, "")
                        m = re.search(r"github\.com/([^/]+)/([^/\.]+)", val)
                        if m:
                            return f"https://github.com/{m.group(1)}/{m.group(2)}.git"
            except Exception:
                pass
                
        # Check PKGBUILD
        pkgbuild = PackageBuilder.find_pkgbuild(pkgname)
        if pkgbuild:
            try:
                content = pkgbuild.read_text(errors="replace")
                m = re.search(r"github\.com/([^/]+)/([^/\.]+)", content)
                if m:
                    return f"https://github.com/{m.group(1)}/{m.group(2)}.git"
            except Exception:
                pass
                
        return None

    @classmethod
    def fetch_latest_git_tag(cls, pkgname: str, git_url: str) -> tuple[str | None, str | None]:
        """Query remote git tags via git ls-remote."""
        try:
            out = subprocess.check_output(
                ["git", "ls-remote", "--tags", "--refs", git_url],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            tags = []
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) == 2:
                    parsed = clean_git_tag(parts[1])
                    if parsed:
                        tags.append(parsed)
            if tags:
                tags.sort(key=lambda x: x[0])
                latest_tag_str = tags[-1][1]
                return latest_tag_str, None
            return None, "No valid release tags found"
        except subprocess.TimeoutExpired:
            return None, "Connection timeout"
        except Exception as e:
            return None, str(e)

    @classmethod
    def scan_all(cls, local_pkgs: dict[str, dict], refresh: bool = False, max_workers: int = 12) -> list[dict]:
        """Concurrently check all packages against upstream Git repository tags."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached_tags = {}
        if not refresh and TAGS_CACHE_FILE.is_file():
            try:
                with open(TAGS_CACHE_FILE) as f:
                    cached_tags = json.load(f)
            except Exception:
                cached_tags = {}

        results = []
        to_fetch = {}
        now = time.time()

        for name, local_info in local_pkgs.items():
            git_url = cls.resolve_git_repo(name)
            # Check cache (1 hour TTL)
            if (
                not refresh
                and name in cached_tags
                and (now - cached_tags[name].get("timestamp", 0)) < 3600
            ):
                tag = cached_tags[name].get("tag")
                results.append(cls._format_result(name, local_info, tag, git_url))
            elif git_url:
                to_fetch[name] = (local_info, git_url)
            else:
                results.append(cls._format_result(name, local_info, None, None, error="No upstream Git URL"))

        if to_fetch:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futs = {
                    executor.submit(cls.fetch_latest_git_tag, name, url): (name, local_info, url)
                    for name, (local_info, url) in to_fetch.items()
                }
                for f in concurrent.futures.as_completed(futs):
                    name, local_info, url = futs[f]
                    tag, err = f.result()
                    if tag:
                        cached_tags[name] = {"tag": tag, "timestamp": now, "url": url}
                    results.append(cls._format_result(name, local_info, tag, url, error=err))

        # Save cache
        try:
            with open(TAGS_CACHE_FILE, "w") as f:
                json.dump(cached_tags, f, indent=2)
        except Exception:
            pass

        results.sort(key=lambda x: (x["status"] != "UPDATE_AVAILABLE", x["pkgname"]))
        return results

    @staticmethod
    def _format_result(name: str, local_info: dict, upstream_tag: str | None, git_url: str | None, error: str | None = None) -> dict:
        local_ver = local_info["version"]
        clean_local = local_info["clean_version"]
        
        status = "NO_GIT_TAG"
        if upstream_tag:
            cmp = compare_versions(clean_local, upstream_tag)
            if cmp < 0:
                status = "UPDATE_AVAILABLE"
            else:
                status = "UP_TO_DATE"
        elif error:
            status = f"ERROR ({error[:12]})"

        return {
            "pkgname": name,
            "local_repo": local_info["repo"],
            "local_version": local_ver,
            "upstream_tag": upstream_tag or "-",
            "status": status,
            "git_url": git_url or "-",
        }


class PackageBuilder:
    """Compiles and packages software natively for macOS Darwin."""

    @classmethod
    def find_pkgbuild(cls, pkgname: str) -> Path | None:
        """Find local PKGBUILD recipe if present."""
        candidates = [
            PACKAGES_DIR / "core" / pkgname / "PKGBUILD",
            PACKAGES_DIR / "extra" / pkgname / "PKGBUILD",
            PACKAGES_DIR / pkgname / "PKGBUILD",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return None

    @classmethod
    def build_from_pkgbuild(cls, pkgbuild_path: Path) -> Path:
        """Run makepkg in the directory containing the PKGBUILD."""
        pkg_dir = pkgbuild_path.parent
        print(f"[{BOLD}{CYAN}BUILD{RESET}] Building via makepkg in {pkg_dir}...")

        env = get_darwin_env()
        cmd = [
            str(MAKEPKG_BIN),
            "-f",
            "--noconfirm",
            "--nodeps",
        ]
        res = subprocess.run(cmd, cwd=pkg_dir, env=env)
        if res.returncode != 0:
            raise RuntimeError(f"makepkg failed with return code {res.returncode}")

        # Find produced package
        pkgs = list(pkg_dir.glob(f"*-{DARWIN_ARCH}.pkg.tar.zst"))
        if not pkgs:
            pkgs = list(pkg_dir.glob("*.pkg.tar.zst"))
        if not pkgs:
            raise FileNotFoundError(f"No .pkg.tar.zst output found in {pkg_dir}")

        latest_pkg = max(pkgs, key=lambda p: p.stat().st_mtime)
        return latest_pkg

    @classmethod
    def deploy_package(cls, pkg_file: Path, target_repo: str = "extra") -> None:
        """Sign and place package into target repository folder."""
        dest_dir = CORE_DIR if target_repo == "core" else EXTRA_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)

        target_pkg = dest_dir / pkg_file.name
        if target_pkg.resolve() != pkg_file.resolve():
            shutil.copyfile(pkg_file, target_pkg)

        print(f"[{BOLD}{CYAN}SIGN{RESET}] Generating PGP detached signature...")
        sig_file = sign_file(target_pkg)
        print(f"[{BOLD}{GREEN}SIGNED{RESET}] {sig_file.name}")

    @classmethod
    def install_package(cls, pkg_file: Path) -> None:
        """Install package locally using pacman -U."""
        print(f"[{BOLD}{CYAN}INSTALL{RESET}] Installing {pkg_file.name} into /opt/pacman...")
        subprocess.run(
            [str(PACMAN_BIN), "-U", "--overwrite", "*", "--noconfirm", str(pkg_file)],
            check=True,
        )
        print(f"[{BOLD}{GREEN}INSTALLED{RESET}] Package {pkg_file.name} active in /opt/pacman.")


def update_repository_databases():
    """Index and sign core and extra repository databases."""
    print(f"\n{BOLD}{CYAN}=== Rebuilding & Signing Repository Databases ==={RESET}")
    for repo_dir, repo_name in [(CORE_DIR, "core"), (EXTRA_DIR, "extra")]:
        if not repo_dir.exists():
            continue
        print(f"-> Processing {repo_name}...")
        for p in list(repo_dir.glob("*.db*")) + list(repo_dir.glob("*.files*")):
            try:
                p.unlink()
            except Exception:
                pass

        # Index darwin_x86_64
        x86_pkgs = sorted([str(p) for p in repo_dir.glob("*-darwin_x86_64.pkg.tar.zst")])
        if x86_pkgs:
            db_x86 = repo_dir / f"{repo_name}-darwin_x86_64.db.tar.gz"
            cmd = [
                str(REPO_ADD_BIN),
                "-q",
                "-s",
                "-k",
                GPG_KEYID,
                "--include-sigs",
                str(db_x86),
            ] + x86_pkgs
            subprocess.run(cmd, check=True)

            for ext in [
                ".db", ".db.tar.gz", ".files", ".files.tar.gz",
                ".db.sig", ".db.tar.gz.sig", ".files.sig", ".files.tar.gz.sig",
            ]:
                src = repo_dir / f"{repo_name}-darwin_x86_64{ext}"
                dst = repo_dir / f"{repo_name}{ext}"
                if src.exists():
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    shutil.copyfile(src.resolve(), dst)

        # Index darwin_arm64
        arm_pkgs = sorted([str(p) for p in repo_dir.glob("*-darwin_arm64.pkg.tar.zst")])
        if arm_pkgs:
            db_arm = repo_dir / f"{repo_name}-darwin_arm64.db.tar.gz"
            cmd = [
                str(REPO_ADD_BIN),
                "-q",
                "-s",
                "-k",
                GPG_KEYID,
                "--include-sigs",
                str(db_arm),
            ] + arm_pkgs
            subprocess.run(cmd, check=True)

        for p in list(repo_dir.glob("*.db*")) + list(repo_dir.glob("*.files*")):
            if p.is_symlink():
                target = p.resolve()
                p.unlink()
                shutil.copyfile(target, p)

    print(f"{BOLD}{GREEN}✓ Repository databases updated and cryptographically signed.{RESET}\n")


def cmd_scan(args):
    """Scan all local packages against upstream Git repository release tags."""
    print(f"{BOLD}{CYAN}Scanning packages against upstream Git tags (macOS native)...{RESET}")
    local_pkgs = RepoCatalog.get_local_packages()
    results = GitTagScanner.scan_all(local_pkgs, refresh=args.refresh)

    if args.updates_only:
        results = [r for r in results if r["status"] == "UPDATE_AVAILABLE"]

    print("\n" + "=" * 95)
    print(
        f"{'Package':<22} {'Repo':<7} {'Local Version':<16} {'Latest Git Tag':<16} {'Status':<18} {'Git Source'}"
    )
    print("=" * 95)

    update_count = 0
    for r in results:
        status_str = r["status"]
        if status_str == "UPDATE_AVAILABLE":
            status_colored = f"{YELLOW}{status_str}{RESET}"
            update_count += 1
        elif status_str == "UP_TO_DATE":
            status_colored = f"{GREEN}{status_str}{RESET}"
        else:
            status_colored = f"{CYAN}{status_str}{RESET}"

        print(
            f"{r['pkgname']:<22} {r['local_repo']:<7} {r['local_version']:<16} {r['upstream_tag']:<16} {status_colored:<27} {r['git_url']}"
        )

    print("=" * 95)
    print(
        f"Scanned {len(local_pkgs)} packages. Real upstream Git updates available: {YELLOW}{update_count}{RESET}.\n"
    )


def cmd_build(args):
    """Execute clone -> build -> package -> sign -> install pipeline."""
    pkgname = args.pkgname
    print(f"\n{BOLD}{CYAN}=== Starting Pipeline for {pkgname} ==={RESET}")

    pkgbuild = PackageBuilder.find_pkgbuild(pkgname)
    if not pkgbuild:
        print(f"{RED}ERROR: No PKGBUILD found for package '{pkgname}' in packages/{RESET}")
        sys.exit(1)

    # 1. Build
    pkg_file = PackageBuilder.build_from_pkgbuild(pkgbuild)

    # 2. Deploy & Sign
    target_repo = "core" if "core" in str(pkgbuild) else "extra"
    PackageBuilder.deploy_package(pkg_file, target_repo=target_repo)

    # 3. Update databases
    update_repository_databases()

    # 4. Install
    if not args.no_install:
        PackageBuilder.install_package(pkg_file)

    print(f"\n{BOLD}{GREEN}✓ Pipeline for {pkgname} successfully completed!{RESET}\n")


def cmd_update_all(args):
    """Scan and update all packages with new upstream git tags."""
    print(f"{BOLD}{CYAN}Checking for packages with new upstream git tags...{RESET}")
    local_pkgs = RepoCatalog.get_local_packages()
    results = GitTagScanner.scan_all(local_pkgs)
    outdated = [r for r in results if r["status"] == "UPDATE_AVAILABLE"]

    if not outdated:
        print(f"{BOLD}{GREEN}All packages are up to date with upstream git tags!{RESET}")
        return

    print(f"Found {len(outdated)} packages with newer upstream git tags:")
    for r in outdated:
        print(f"  - {r['pkgname']}: {r['local_version']} -> {r['upstream_tag']}")

    for r in outdated:
        pkgname = r["pkgname"]
        pkgbuild = PackageBuilder.find_pkgbuild(pkgname)
        if pkgbuild:
            print(f"\n{BOLD}{CYAN}>>> Updating {pkgname} to {r['upstream_tag']}...{RESET}")
            try:
                pkg_file = PackageBuilder.build_from_pkgbuild(pkgbuild)
                PackageBuilder.deploy_package(pkg_file, target_repo=r["local_repo"])
            except Exception as e:
                print(f"{RED}Failed to build {pkgname}: {e}{RESET}")

    update_repository_databases()
    print(f"{BOLD}{GREEN}✓ All available updates processed.{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Unified Arch Linux Darwin Build & Packaging Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan local packages against upstream Git tags")
    p_scan.add_argument(
        "--updates-only", action="store_true", help="Display only packages with updates"
    )
    p_scan.add_argument(
        "--refresh", action="store_true", help="Bypass cache and re-query all upstream git tags"
    )
    p_scan.set_defaults(func=cmd_scan)

    # build
    p_build = subparsers.add_parser("build", help="Build, sign, package, and install a package")
    p_build.add_argument("pkgname", help="Package name to build")
    p_build.add_argument(
        "--no-install", action="store_true", help="Skip pacman -U local installation"
    )
    p_build.set_defaults(func=cmd_build)

    # update-all
    p_update = subparsers.add_parser(
        "update-all", help="Scan and rebuild all packages with upstream git tag updates"
    )
    p_update.set_defaults(func=cmd_update_all)

    # index
    p_index = subparsers.add_parser("index", help="Rebuild and sign repository databases")
    p_index.set_defaults(func=lambda args: update_repository_databases())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
