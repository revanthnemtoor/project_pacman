#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
PACMAN_ROOT = Path("/opt/pacman")

MAINTAINER = "Revanth Reddy Nemtoor <developerrevanth123@gmail.com>"

BUILD_ENV = os.environ.copy()
BUILD_ENV["PATH"] = f"/opt/pacman/bin:/opt/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_ENV["CFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["CXXFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["LDFLAGS"] = "-L/opt/pacman/lib -arch x86_64"
BUILD_ENV["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
BUILD_ENV["PACKAGER"] = MAINTAINER

RECIPES = [
    {
        "name": "libunistring",
        "repo": "core",
        "version": "1.2",
        "rel": "1",
        "desc": "Library for manipulating Unicode strings and C strings",
        "url": "https://www.gnu.org/software/libunistring/",
        "license": "LGPL-3.0-or-later OR GPL-2.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/libunistring/libunistring-1.2.tar.xz",
        "src_dir": "libunistring-1.2",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libidn2",
        "repo": "core",
        "version": "2.3.7",
        "rel": "1",
        "desc": "Free software implementation of IDNA2008 / TR46",
        "url": "https://www.gnu.org/software/libidn/#libidn2",
        "license": "GPL-2.0-or-later OR LGPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/libidn/libidn2-2.3.7.tar.gz",
        "src_dir": "libidn2-2.3.7",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-libunistring-prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libpsl",
        "repo": "core",
        "version": "0.21.5",
        "rel": "1",
        "desc": "Public Suffix List C library & utility",
        "url": "https://rockdaboot.github.io/libpsl/",
        "license": "MIT",
        "src_url": "https://github.com/rockdaboot/libpsl/releases/download/0.21.5/libpsl-0.21.5.tar.gz",
        "src_dir": "libpsl-0.21.5",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libtasn1",
        "repo": "core",
        "version": "4.19.0",
        "rel": "1",
        "desc": "ASN.1 structure parser library",
        "url": "https://www.gnu.org/software/libtasn1/",
        "license": "LGPL-2.1-or-later",
        "src_url": "https://ftp.gnu.org/gnu/libtasn1/libtasn1-4.19.0.tar.gz",
        "src_dir": "libtasn1-4.19.0",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libgpg-error",
        "repo": "core",
        "version": "1.50",
        "rel": "1",
        "desc": "Support library for error values used with GnuPG software",
        "url": "https://gnupg.org/related_software/libgpg-error/",
        "license": "LGPL-2.1-or-later",
        "src_url": "https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.50.tar.bz2",
        "src_dir": "libgpg-error-1.50",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libgcrypt",
        "repo": "core",
        "version": "1.11.0",
        "rel": "1",
        "desc": "General purpose cryptographic library based on the code from GnuPG",
        "url": "https://gnupg.org/related_software/libgcrypt/",
        "license": "LGPL-2.1-or-later",
        "src_url": "https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.11.0.tar.bz2",
        "src_dir": "libgcrypt-1.11.0",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-libgpg-error-prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libassuan",
        "repo": "core",
        "version": "3.0.1",
        "rel": "1",
        "desc": "IPC library used by some of the other GnuPG related packages",
        "url": "https://gnupg.org/related_software/libassuan/",
        "license": "LGPL-2.1-or-later",
        "src_url": "https://gnupg.org/ftp/gcrypt/libassuan/libassuan-3.0.1.tar.bz2",
        "src_dir": "libassuan-3.0.1",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-libgpg-error-prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libksba",
        "repo": "core",
        "version": "1.6.7",
        "rel": "1",
        "desc": "A CMS and X.509 access library",
        "url": "https://gnupg.org/related_software/libksba/",
        "license": "LGPL-3.0-or-later OR GPL-2.0-or-later",
        "src_url": "https://gnupg.org/ftp/gcrypt/libksba/libksba-1.6.7.tar.bz2",
        "src_dir": "libksba-1.6.7",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-libgpg-error-prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "npth",
        "repo": "core",
        "version": "1.7",
        "rel": "1",
        "desc": "The New GNU Portable Threads Library",
        "url": "https://gnupg.org/related_software/npth/",
        "license": "LGPL-2.1-or-later",
        "src_url": "https://gnupg.org/ftp/gcrypt/npth/npth-1.7.tar.bz2",
        "src_dir": "npth-1.7",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "nettle",
        "repo": "core",
        "version": "3.10",
        "rel": "1",
        "desc": "A low-level cryptographic library",
        "url": "https://www.lysator.liu.se/~nisse/nettle/",
        "license": "LGPL-3.0-or-later OR GPL-2.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/nettle/nettle-3.10.tar.gz",
        "src_dir": "nettle-3.10",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-include-path=/opt/pacman/include", "--with-lib-path=/opt/pacman/lib"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libxml2",
        "repo": "core",
        "version": "2.13.4",
        "rel": "1",
        "desc": "XML C parser version 2",
        "url": "https://gitlab.gnome.org/GNOME/libxml2",
        "license": "MIT",
        "src_url": "https://download.gnome.org/sources/libxml2/2.13/libxml2-2.13.4.tar.xz",
        "src_dir": "libxml2-2.13.4",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-zlib=/opt/pacman", "--with-lzma=/opt/pacman", "--without-python"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "gettext",
        "repo": "core",
        "version": "0.22.5",
        "rel": "1",
        "desc": "GNU internationalization library",
        "url": "https://www.gnu.org/software/gettext/",
        "license": "GPL-3.0-or-later AND LGPL-2.1-or-later",
        "src_url": "https://ftp.gnu.org/gnu/gettext/gettext-0.22.5.tar.xz",
        "src_dir": "gettext-0.22.5",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-included-gettext", "--with-libunistring-prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "nano",
        "repo": "extra",
        "version": "8.2",
        "rel": "1",
        "desc": "Pico editor clone with enhancements",
        "url": "https://www.nano-editor.org/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://www.nano-editor.org/dist/v8/nano-8.2.tar.xz",
        "src_dir": "nano-8.2",
        "configure": ["./configure", "--prefix=/opt/pacman", "--enable-utf8"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "wget",
        "repo": "extra",
        "version": "1.25.0",
        "rel": "1",
        "desc": "Network utility to retrieve files from the Web",
        "url": "https://www.gnu.org/software/wget/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/wget/wget-1.25.0.tar.gz",
        "src_dir": "wget-1.25.0",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-ssl=openssl", "--with-libpsl=/opt/pacman", "--with-libidn2=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libevent",
        "repo": "extra",
        "version": "2.1.12",
        "rel": "1",
        "desc": "An event notification library",
        "url": "https://libevent.org/",
        "license": "BSD-3-Clause",
        "src_url": "https://github.com/libevent/libevent/releases/download/release-2.1.12-stable/libevent-2.1.12-stable.tar.gz",
        "src_dir": "libevent-2.1.12-stable",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "tmux",
        "repo": "extra",
        "version": "3.5a",
        "rel": "1",
        "desc": "Terminal multiplexer",
        "url": "https://tmux.github.io/",
        "license": "ISC",
        "src_url": "https://github.com/tmux/tmux/releases/download/3.5a/tmux-3.5a.tar.gz",
        "src_dir": "tmux-3.5a",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libsodium",
        "repo": "extra",
        "version": "1.0.20",
        "rel": "1",
        "desc": "PNaCl usable crypto library",
        "url": "https://libsodium.org/",
        "license": "ISC",
        "src_url": "https://download.libsodium.org/libsodium/releases/libsodium-1.0.20-RELEASE.tar.gz",
        "src_dir": "libsodium-stable",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "utf8proc",
        "repo": "extra",
        "version": "2.9.0",
        "rel": "1",
        "desc": "Clean C library for processing UTF-8 Unicode data",
        "url": "https://juliastrings.github.io/utf8proc/",
        "license": "MIT",
        "src_url": "https://github.com/JuliaStrings/utf8proc/archive/refs/tags/v2.9.0.tar.gz",
        "src_dir": "utf8proc-2.9.0",
        "build": ["make", "prefix=/opt/pacman", "-j8"],
        "install": ["make", "prefix=/opt/pacman", "DESTDIR={pkgdir}", "install"],
    }
]

def build_package(recipe, workdir):
    name = recipe["name"]
    version = recipe["version"]
    rel = recipe["rel"]
    repo = recipe["repo"]
    target_dir = EXTRA_DIR if repo == "extra" else CORE_DIR
    
    print(f"\n{'='*60}")
    print(f"Building {name} {version}-{rel} from source for {repo}...")
    print(f"{'='*60}")
    
    pkg_work = workdir / name
    pkg_work.mkdir(parents=True, exist_ok=True)
    
    # 1. Download
    tar_name = recipe["src_url"].split("/")[-1]
    tar_path = pkg_work / tar_name
    if not tar_path.exists():
        print(f"  -> Downloading {tar_name}...")
        subprocess.run(["curl", "-fsSL", recipe["src_url"], "-o", str(tar_path)], check=True)
        
    # 2. Extract
    print(f"  -> Extracting {tar_name}...")
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(pkg_work)], check=True)
    src_dir = pkg_work / recipe["src_dir"]
    
    # 3. Build & Install into staging pkgdir
    pkgdir = pkg_work / "pkg"
    pkgdir.mkdir(parents=True, exist_ok=True)
    
    if "configure" in recipe:
        print(f"  -> Configuring...")
        subprocess.run(recipe["configure"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "build" in recipe:
        print(f"  -> Building...")
        subprocess.run(recipe["build"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "install" in recipe:
        print(f"  -> Installing to staging...")
        inst_cmd = [arg.replace("{pkgdir}", str(pkgdir)) for arg in recipe["install"]]
        subprocess.run(inst_cmd, cwd=src_dir, env=BUILD_ENV, check=True)

    # 4. Ad-hoc codesign all Mach-O binaries in staging
    print(f"  -> Codesigning Mach-O binaries...")
    for f in pkgdir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    subprocess.run(["codesign", "--sign", "-", "--force", str(f)], check=False, capture_output=True)
            except Exception:
                pass

    # 5. Generate package metadata
    print(f"  -> Packaging native .pkg.tar.zst archive...")
    installed_size = sum(f.stat().st_size for f in pkgdir.rglob("*") if f.is_file() and not f.is_symlink())
    pkginfo = (
        f"pkgname = {name}\n"
        f"pkgver = {version}-{rel}\n"
        f"pkgdesc = {recipe['desc']} (built from source for macOS)\n"
        f"url = {recipe['url']}\n"
        f"builddate = 1730764800\n"
        f"packager = {MAINTAINER}\n"
        f"size = {installed_size}\n"
        f"arch = darwin_x86_64\n"
        f"license = {recipe['license']}\n"
    )
    (pkgdir / ".PKGINFO").write_text(pkginfo)
    (pkgdir / ".BUILDINFO").write_text(f"format = 2\npkgname = {name}\npkgver = {version}-{rel}\n")
    
    subprocess.run(
        "tar -czf .MTREE --format=mtree --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' *",
        cwd=pkgdir,
        shell=True,
        check=False
    )
    
    pkg_filename = f"{name}-{version}-{rel}-darwin_x86_64.pkg.tar.zst"
    dest_pkg = target_dir / pkg_filename
    
    for old_pkg in target_dir.glob(f"{name}-*-darwin_x86_64.pkg.tar.zst"):
        old_pkg.unlink()
        
    filelist = pkg_work / "filelist.txt"
    with open(filelist, "w") as fl:
        for root, dirs, files in os.walk(pkgdir):
            for file in sorted(files):
                full = Path(root) / file
                rel_f = full.relative_to(pkgdir)
                fl.write(f"{rel_f}\n")
                
    tar_cmd = f"cd {pkgdir} && tar -cf - -T {filelist} | zstd -c -T0 -19 -z > {dest_pkg}"
    subprocess.run(tar_cmd, shell=True, check=True)
    print(f"  -> Package built successfully: {dest_pkg.name} ({dest_pkg.stat().st_size:,} bytes)")
    
    print(f"  -> Installing to live /opt/pacman prefix...")
    copy_opt = pkgdir / "opt/pacman"
    if copy_opt.exists():
        subprocess.run(f"cp -Rf {copy_opt}/* /opt/pacman/", shell=True, check=False)
        
    return dest_pkg

def main():
    with tempfile.TemporaryDirectory() as workdir:
        workdir = Path(workdir)
        built = []
        for recipe in RECIPES:
            try:
                pkg = build_package(recipe, workdir)
                built.append(pkg)
            except Exception as e:
                print(f"ERROR building {recipe['name']}: {e}")
                
        print(f"\nSuccessfully built {len(built)} packages from source in Tier 3!")

if __name__ == "__main__":
    main()

