#!/usr/bin/env python3
"""Automated Apple Silicon (darwin_arm64) Source Builder, Signer & Checkpointer for GitHub Actions.

Detects all packages present for darwin_x86_64 in core/ and extra/ that either:
  1. Do not yet have a built darwin_arm64 archive, OR
  2. Have an older darwin_arm64 archive compiled for macOS > 15.0 (e.g. 26.0/27.0 _pipe2 ABI),
and compiles them natively on Apple Silicon macos-15 runners (MACOSX_DEPLOYMENT_TARGET=15.0)
in topological dependency order, signs them with PGP key CEC5B78775CA4628, updates
*-darwin_arm64.db.tar.gz, and checkpoints signed batches back to origin/main periodically.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
PACKAGES_DIR = PROJECT_DIR / "packages"

PACMAN_ROOT = Path("/opt/pacman")
PACMAN_BIN = PACMAN_ROOT / "bin" / "pacman"
MAKEPKG_BIN = PACMAN_ROOT / "bin" / "makepkg"
REPO_ADD_BIN = PACMAN_ROOT / "bin" / "repo-add"

GPG_KEYID = "CEC5B78775CA4628"
PACKAGER = os.environ.get(
    "PACKAGER", "Revanth Reddy Nemtoor <developerrevanth123@gmail.com>"
)
META_PACKAGES = {"base", "base-devel", "pacman-mirrorlist", "filesystem"}

# Full topological build order across [core] and [extra]
ORDERED_TIERS: list[str] = [
    # Tier 0A: Zero-dep compression, curses, FFI, XML/JSON & hashing libraries
    "ncurses", "zlib", "bzip2", "xz", "lz4", "lzo", "brotli", "zstd",
    "expat", "libffi", "libxcrypt", "popt", "xxhash", "yyjson", "utf8proc", "libsodium", "oniguruma", "json-c",
    # Tier 0B: Unicode, i18n, regex, readline, pkg-config, bignum math & OpenSSL (needed before coreutils)
    "libunistring", "libxml2", "gettext", "pcre2", "readline", "pkgconf",
    "gmp", "mpfr", "libmpc", "libisl", "openssl",
    # Tier 0C: Core UNIX shell, autotools & userland utilities
    "bash", "coreutils", "sed", "grep", "gawk", "diffutils", "findutils",
    "patch", "tar", "gzip", "make", "m4", "autoconf", "libtool", "bison", "flex",
    "file", "which", "fakeroot", "less", "nano", "texinfo", "tree", "groff",
    # Tier 0D: TLS, HTTP, Kerberos, SQLite, Libevent & GnuPG crypto stack
    "libidn2", "libpsl", "krb5", "libssh2", "libnghttp2", "libnghttp3",
    "curl", "sqlite", "libevent", "libusb", "libpipeline",
    "npth", "libgpg-error", "libassuan", "libgcrypt", "libksba", "pinentry", "gnupg",
    # Tier 1: Pure data, shells & modern build tools
    "iana-etc", "filesystem", "tzdata", "libedit", "dash",
    "ninja", "meson", "p11-kit", "ccache", "cmake", "pigz", "7zip",
    # Tier 2: ASN.1, TLS, DB/Network & System Libraries
    "nettle", "libtasn1", "gnutls", "libngtcp2",
    "gc", "gdbm", "jansson", "libinih", "libverto", "mpdecimal", "unixodbc",
    "libpcap", "ldns", "leancrypto", "libmicrohttpd",
    "libsasl", "openldap", "openssh",
    "nspr", "icu", "glib2", "libsecret", "nss",
    # Tier 3: Man/Doc Pipeline, Binutils & Language Runtimes
    "man-db", "inetutils", "logrotate", "s-nail",
    "binutils", "perl", "python", "guile",
    # Tier 4: Media Codec Stack & Image/PDF/Terminal Graphics
    "jemalloc", "freetype2", "libwebp", "openjpeg2",
    "libde265", "kvazaar", "dav1d", "aom", "libheif", "libraw",
    "imagemagick", "qpdf", "chafa",
    # Tier 5: C/C++/Go/Python/Rust CLI & Editor Suite
    "git", "vim", "tmux", "wget", "jq", "rsync", "fastfetch", "links",
    "htop", "entr", "yt-dlp", "mtr", "tcpdump", "tig", "aria2", "neovim", "gh",
    "bat", "eza", "zoxide", "starship", "git-delta", "hyperfine",
    "just", "procs", "dust", "sd", "tealdeer", "tokei", "bottom", "xh",
    # Tier 6: Heavy Toolchain (GCC last so all other packages checkpoint first)
    "gcc",
]


def resolve_gpg() -> str:
    """Find a working gpg binary (/opt/homebrew/bin/gpg preferred during bootstrap)."""
    for cand in ["/opt/homebrew/bin/gpg", "/opt/pacman/bin/gpg", shutil.which("gpg") or ""]:
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            try:
                subprocess.run([cand, "--version"], check=True, capture_output=True)
                return cand
            except Exception:
                continue
    return "gpg"


def get_arm64_env() -> dict[str, str]:
    """Build clean Apple Silicon darwin_arm64 environment targeting macOS 15.0+."""
    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    cargo_bin = str(Path.home() / ".cargo" / "bin")
    env = os.environ.copy()
    env["PATH"] = (
        f"/opt/pacman/bin:{cargo_bin}:/opt/homebrew/bin:/opt/homebrew/opt/gettext/bin:"
        "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    )
    env["CARCH"] = "darwin_arm64"
    env["CHOST"] = "arm64-apple-darwin"
    env["PKGEXT"] = ".pkg.tar.zst"
    env["PACKAGER"] = PACKAGER
    env["SDKROOT"] = sdk
    env["MACOSX_DEPLOYMENT_TARGET"] = "15.0"
    env["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    env["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig:/opt/pacman/share/pkgconfig"
    env["GPG_TTY"] = ""
    return env


def list_arch_packages(repo_dir: Path, arch: str) -> dict[str, Path]:
    """Map pkgname -> archive path for a given architecture in repo_dir."""
    out: dict[str, Path] = {}
    suffix = f"-{arch}.pkg.tar.zst"
    for p in sorted(repo_dir.glob(f"*{suffix}")):
        raw = p.name[: -len(suffix)]
        parts = raw.split("-")
        if len(parts) >= 3:
            pkgname = "-".join(parts[:-2])
            out[pkgname] = p
    return out


def archive_needs_rebuild(pkg_path: Path) -> bool:
    """Return True if Mach-O binaries target macOS > 15.0 or config scripts leak x86_64 flags."""
    bsdtar = "/opt/pacman/bin/bsdtar" if os.path.exists("/opt/pacman/bin/bsdtar") else "bsdtar"
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([bsdtar, "-xf", str(pkg_path), "-C", td], check=False, capture_output=True)
        cfg = Path(td) / "opt/pacman/bin/ncursesw6-config"
        if cfg.is_file() and "x86_64" in cfg.read_text(errors="ignore"):
            return True
        for sub in ("opt/pacman/bin", "opt/pacman/lib"):
            d = Path(td) / sub
            if not d.exists():
                continue
            for f in sorted(d.iterdir())[:8]:
                if f.is_symlink() or not f.is_file():
                    continue
                out = subprocess.run(["/usr/bin/otool", "-l", str(f)], capture_output=True, text=True)
                for m in re.finditer(r"minos\s+([0-9.]+)", out.stdout):
                    if float(m.group(1).split(".")[0]) > 15.0:
                        return True
    return False


def compute_missing_arm64(only_pkg: str = "") -> list[tuple[str, str, Path]]:
    """Return ordered list of (repo, pkgname, pkgbuild_path) needing darwin_arm64 builds."""
    if only_pkg and only_pkg != "all":
        for repo in ("core", "extra"):
            pb = PACKAGES_DIR / repo / only_pkg / "PKGBUILD"
            if pb.is_file():
                return [(repo, only_pkg, pb)]
        raise SystemExit(f"No PKGBUILD found for requested package '{only_pkg}'")

    core_x86 = list_arch_packages(CORE_DIR, "darwin_x86_64")
    core_arm = list_arch_packages(CORE_DIR, "darwin_arm64")
    extra_x86 = list_arch_packages(EXTRA_DIR, "darwin_x86_64")
    extra_arm = list_arch_packages(EXTRA_DIR, "darwin_arm64")

    missing_map: dict[str, tuple[str, Path]] = {}
    for repo_name, x86_map, arm_map in [("core", core_x86, core_arm), ("extra", extra_x86, extra_arm)]:
        for name in sorted(x86_map):
            pb = PACKAGES_DIR / repo_name / name / "PKGBUILD"
            if not pb.is_file():
                continue
            if name not in arm_map or archive_needs_rebuild(arm_map[name]):
                missing_map[name] = (repo_name, pb)

    ordered: list[tuple[str, str, Path]] = []
    seen = set()
    for name in ORDERED_TIERS:
        if name in missing_map:
            repo, pb = missing_map[name]
            ordered.append((repo, name, pb))
            seen.add(name)
    for name in sorted(missing_map):
        if name not in seen:
            repo, pb = missing_map[name]
            ordered.append((repo, name, pb))
    return ordered


def cleanup_dir(pkg_dir: Path) -> None:
    """Remove temporary makepkg directories and source archives."""
    keep = {"PKGBUILD", "metadata.json", "README.md", "LICENSE"}
    for item in pkg_dir.iterdir():
        if item.name in keep or item.suffix in (".c", ".h", ".1", ".install", ".patch", ".diff"):
            continue
        if item.name in ("src", "pkg", "build", "_build", "target", ".deps", "stage", "logs") or item.name.endswith(
            (".pkg.tar.zst", ".pkg.tar.zst.sig", ".tar.gz", ".tar.xz", ".tar.bz2", ".tar.lz", ".tgz", ".zip")
        ):
            subprocess.run(["chmod", "-R", "u+rwx", str(item)], check=False, capture_output=True)
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)


def sign_archive(pkg_path: Path, gpg_bin: str, env: dict[str, str]) -> Path:
    """Create detached PGP .sig signature for pkg_path."""
    sig_path = pkg_path.with_name(pkg_path.name + ".sig")
    sig_path.unlink(missing_ok=True)
    gpg_env = env.copy()
    gpg_env["PATH"] = f"/opt/homebrew/bin:{env['PATH']}"
    subprocess.run(
        [gpg_bin, "--detach-sign", "--batch", "--yes", "--pinentry-mode", "loopback", "-u", GPG_KEYID, str(pkg_path)],
        check=True,
        env=gpg_env,
    )
    return sig_path


def reindex_arm64_dbs(env: dict[str, str]) -> None:
    """Rebuild and sign core-darwin_arm64.db.tar.gz and extra-darwin_arm64.db.tar.gz."""
    print("\n=== Re-indexing & signing darwin_arm64 repository databases ===", flush=True)
    gpg_env = env.copy()
    gpg_env["PATH"] = f"/opt/homebrew/bin:{env['PATH']}"
    for repo_dir, repo_name in [(CORE_DIR, "core"), (EXTRA_DIR, "extra")]:
        for p in list(repo_dir.glob(f"{repo_name}-darwin_arm64.db*")) + list(
            repo_dir.glob(f"{repo_name}-darwin_arm64.files*")
        ):
            p.unlink(missing_ok=True)

        arm_pkgs = sorted(str(p) for p in repo_dir.glob("*-darwin_arm64.pkg.tar.zst"))
        if not arm_pkgs:
            continue

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
        subprocess.run(cmd, check=True, env=gpg_env)

        for p in list(repo_dir.glob(f"{repo_name}-darwin_arm64.db*")) + list(
            repo_dir.glob(f"{repo_name}-darwin_arm64.files*")
        ):
            if p.is_symlink():
                target = p.resolve()
                p.unlink()
                shutil.copyfile(target, p)


def checkpoint_push(built_names: list[str], env: dict[str, str]) -> None:
    """Index arm64 DBs, commit newly built darwin_arm64 packages, and push to origin/main."""
    if not built_names:
        return
    reindex_arm64_dbs(env)
    subprocess.run(["git", "add", "-A", "core/", "extra/"], cwd=PROJECT_DIR, check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROJECT_DIR)
    if diff.returncode == 0:
        return

    summary = ", ".join(built_names[:8])
    if len(built_names) > 8:
        summary += f" (+{len(built_names) - 8} more)"
    msg = f"ci(arm64): add {len(built_names)} signed darwin_arm64 packages ({summary}) [skip ci]"
    subprocess.run(["git", "commit", "-m", msg], cwd=PROJECT_DIR, check=True)
    for attempt in range(1, 4):
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=PROJECT_DIR, check=False)
        res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=PROJECT_DIR)
        if res.returncode == 0:
            print(f"✓ Pushed checkpoint ({len(built_names)} arm64 packages) to origin/main!", flush=True)
            return
        time.sleep(3 * attempt)
    raise RuntimeError("Failed to push arm64 checkpoint after 3 attempts")


def main() -> None:
    parser = argparse.ArgumentParser(description="CI builder for darwin_arm64 packages")
    parser.add_argument("--package", default="all", help="Specific package name or 'all'")
    parser.add_argument("--max-packages", type=int, default=0, help="Max packages to build in this run (0 = all)")
    parser.add_argument("--checkpoint-every", type=int, default=10, help="Commit & push every N built packages")
    parser.add_argument("--no-push", action="store_true", help="Build locally without git commit/push")
    args = parser.parse_args()

    env = get_arm64_env()
    gpg_bin = resolve_gpg()
    queue = compute_missing_arm64(args.package)
    if args.max_packages > 0:
        queue = queue[: args.max_packages]

    print(f"Found {len(queue)} darwin_arm64 package(s) queued to build.", flush=True)
    if not queue:
        return

    batch_built: list[str] = []
    all_succeeded: list[str] = []
    all_failed: list[str] = []
    start_ts = time.time()

    for idx, (repo, pkgname, pkgbuild) in enumerate(queue, 1):
        elapsed_min = (time.time() - start_ts) / 60.0
        if elapsed_min > 325:
            print(f"Reached {elapsed_min:.1f}m runtime safety mark; checkpointing and stopping cleanly.", flush=True)
            break

        print(f"\n[{idx}/{len(queue)}] >>> Building {repo}/{pkgname} for darwin_arm64...", flush=True)
        pkg_dir = pkgbuild.parent
        cleanup_dir(pkg_dir)
        try:
            res = subprocess.run(
                [str(MAKEPKG_BIN), "-f", "-C", "--noconfirm", "--nodeps"],
                cwd=pkg_dir,
                env=env,
            )
            if res.returncode != 0:
                raise RuntimeError(f"makepkg exited with {res.returncode}")

            built = sorted(
                list(pkg_dir.glob("*-darwin_arm64.pkg.tar.zst")) + list(pkg_dir.glob("*-any.pkg.tar.zst")),
                key=lambda p: p.stat().st_mtime,
            )
            if not built:
                raise FileNotFoundError(f"No .pkg.tar.zst produced in {pkg_dir}")
            pkg_file = built[-1]
            # Normalize -any.pkg.tar.zst to -darwin_arm64.pkg.tar.zst if needed so repo layout stays uniform
            final_name = pkg_file.name.replace("-any.pkg.tar.zst", "-darwin_arm64.pkg.tar.zst")
            sz = pkg_file.stat().st_size
            if pkgname not in META_PACKAGES and sz < 4096:
                raise RuntimeError(f"Archive too small ({sz} bytes)")
            if sz > 95 * 1024 * 1024:
                raise RuntimeError(f"Archive exceeds 95 MB GitHub safety limit ({sz / (1024*1024):.1f} MB)")

            dest_dir = CORE_DIR if repo == "core" else EXTRA_DIR
            for old in dest_dir.glob(f"{pkgname}-[0-9]*-darwin_arm64.pkg.tar.zst*"):
                old.unlink(missing_ok=True)

            target_pkg = dest_dir / final_name
            shutil.copyfile(pkg_file, target_pkg)
            sign_archive(target_pkg, gpg_bin, env)

            subprocess.run(
                [str(PACMAN_BIN), "-U", "-dd", "--overwrite", "*", "--noconfirm", str(target_pkg)],
                check=True,
                env=env,
            )
            if pkgname == "expat":
                for la_pkg in CORE_DIR.glob("libarchive-*-darwin_arm64.pkg.tar.zst"):
                    subprocess.run(
                        [str(PACMAN_BIN), "-U", "-dd", "--overwrite", "*", "--noconfirm", str(la_pkg)],
                        check=False,
                        env=env,
                    )
            elif pkgname == "gnupg":
                for gp_pkg in CORE_DIR.glob("gpgme-*-darwin_arm64.pkg.tar.zst"):
                    subprocess.run(
                        [str(PACMAN_BIN), "-U", "-dd", "--overwrite", "*", "--noconfirm", str(gp_pkg)],
                        check=False,
                        env=env,
                    )

            all_succeeded.append(pkgname)
            batch_built.append(pkgname)
            print(f"✓ Built, signed & installed {target_pkg.name} ({sz / 1024:.1f} KB)", flush=True)

            if not args.no_push and args.checkpoint_every > 0 and len(batch_built) >= args.checkpoint_every:
                checkpoint_push(batch_built, env)
                batch_built.clear()

        except Exception as exc:
            print(f"✗ FAILED {repo}/{pkgname}: {exc}", flush=True)
            all_failed.append(pkgname)
        finally:
            cleanup_dir(pkg_dir)

    if batch_built and not args.no_push:
        checkpoint_push(batch_built, env)
    elif batch_built and args.no_push:
        reindex_arm64_dbs(env)

    print("\n" + "=" * 80)
    print(f"ARM64 CI SUMMARY | Succeeded: {len(all_succeeded)} | Failed: {len(all_failed)}")
    if all_succeeded:
        print(f"  Succeeded: {', '.join(all_succeeded)}")
    if all_failed:
        print(f"  Failed   : {', '.join(all_failed)}")
    print("=" * 80, flush=True)

    if all_failed and not all_succeeded:
        sys.exit(1)


if __name__ == "__main__":
    main()
