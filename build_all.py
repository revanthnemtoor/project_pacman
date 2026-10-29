#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import os
from pathlib import Path

EXTRA_PACKAGES = [
    "git",
    "gh",
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
    "tmux",
    "fish",
]

CORE_PACKAGES = [
    "automake",
    "bash",
    "brotli",
    "bzip2",
    "coreutils",
    "diffutils",
    "expat",
    "fastfetch",
    "findutils",
    "gawk",
    "gh",
    "git",
    "gmp",
    "gnupg",
    "grep",
    "gzip",
    "jq",
    "json-c",
    "krb5",
    "less",
    "libffi",
    "libpipeline",
    "libusb",
    "libxcrypt",
    "libxml2",
    "links",
    "lzo",
    "make",
    "ncurses",
    "openssl",
    "p11-kit",
    "pcre2",
    "pkgconf",
    "rsync",
    "sed",
    "sqlite",
    "tar",
    "texinfo",
    "vim",
    "xz",
    "zlib",
    "zstd",
    # Full transitive dependency closure
    "autoconf",
    "ca-certificates",
    "gettext",
    "gnutls",
    "jemalloc",
    "libassuan",
    "libevent",
    "libgcrypt",
    "libgpg-error",
    "libidn2",
    "libksba",
    "libpsl",
    "libsodium",
    "libtasn1",
    "libunistring",
    "lz4",
    "m4",
    "mpfr",
    "nettle",
    "npth",
    "oniguruma",
    "pinentry",
    "popt",
    "readline",
    "utf8proc",
    "xxhash",
    "yyjson",
]

def main():
    parser = argparse.ArgumentParser(description="Build and index key packages for current macOS architecture")
    parser.add_argument("--core", action="store_true", help="Also build all 39 core packages and index into core/")
    parser.add_argument("--skip-deps", action="store_true", help="Build only the top-level packages without recursive dependencies")
    parser.add_argument("packages", nargs="*", help="Optional specific packages to build")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    output_dir = project_dir / "output"
    core_dir = project_dir / "core"
    new_packages_dir = project_dir / "new_packages"

    output_dir.mkdir(exist_ok=True)
    core_dir.mkdir(exist_ok=True)
    new_packages_dir.mkdir(exist_ok=True)

    target_pkgs = args.packages if args.packages else list(dict.fromkeys(EXTRA_PACKAGES + (CORE_PACKAGES if args.core else [])))

    # Build all target packages
    for pkg in target_pkgs:
        print(f"==========================================")
        print(f"Building {pkg}...")
        print(f"==========================================")
        cmd = ["python3", "builder/src/main.py", "build", pkg]
        if args.skip_deps:
            cmd.append("--skip-deps")
        subprocess.run(
            cmd,
            cwd=project_dir,
            env={**os.environ, "PYTHONPATH": "converter/src:."}
        )

    # Update the [pacman] repo in output/
    print(f"==========================================")
    print(f"Updating [pacman] repository in output/...")
    print(f"==========================================")
    subprocess.run(
        ["python3", "builder/src/main.py", "repo", "update"],
        cwd=project_dir,
        env={**os.environ, "PYTHONPATH": "converter/src:."}
    )

    # If --core was passed, also copy all built packages (including dependencies) into core/ and update core.db.tar.gz
    if args.core:
        import platform
        host_arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
        darwin_arch = f"darwin_{host_arch}"
        print(f"==========================================")
        print(f"Updating [core] repository in core/ ({darwin_arch})...")
        print(f"==========================================")
        core_archives = []
        for match in output_dir.glob(f"*-{darwin_arch}.pkg.tar.zst"):
            dest = core_dir / match.name
            shutil.copy2(match, dest)
            core_archives.append(str(dest))
        if core_archives:
            subprocess.run(
                ["/opt/pacman/bin/repo-add", str(core_dir / "core.db.tar.gz"), *core_archives],
                cwd=project_dir,
            )

    # Copy to new_packages
    for file_path in output_dir.glob("*.pkg.tar.zst"):
        shutil.copy2(file_path, new_packages_dir / file_path.name)

    # Sync pacman database
    subprocess.run(["/opt/pacman/bin/pacman", "-Sy"], check=False)
    print("Done!")

if __name__ == "__main__":
    main()
