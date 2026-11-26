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

from env_loader import get_packager

MAINTAINER = get_packager()

BUILD_ENV = os.environ.copy()
BUILD_ENV["PATH"] = f"/opt/pacman/bin:/opt/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_ENV["CFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["CXXFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["LDFLAGS"] = "-L/opt/pacman/lib -arch x86_64"
BUILD_ENV["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
BUILD_ENV["PACKAGER"] = MAINTAINER

RECIPES = [
    {
        "name": "gmp",
        "repo": "core",
        "version": "6.3.0",
        "rel": "1",
        "desc": "Free library for arbitrary precision arithmetic",
        "url": "https://gmplib.org/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz",
        "src_dir": "gmp-6.3.0",
        "configure": ["./configure", "--prefix=/opt/pacman", "--enable-cxx"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "mpfr",
        "repo": "core",
        "version": "4.2.1",
        "rel": "1",
        "desc": "Multiple-precision floating-point library",
        "url": "https://www.mpfr.org/",
        "license": "LGPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.1.tar.xz",
        "src_dir": "mpfr-4.2.1",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-gmp=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "pcre2",
        "repo": "core",
        "version": "10.44",
        "rel": "1",
        "desc": "Perl Compatible Regular Expressions - Version 2",
        "url": "https://www.pcre.org/",
        "license": "BSD-3-Clause",
        "src_url": "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.44/pcre2-10.44.tar.bz2",
        "src_dir": "pcre2-10.44",
        "configure": ["./configure", "--prefix=/opt/pacman", "--enable-pcre2-16", "--enable-pcre2-32", "--enable-jit"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "expat",
        "repo": "core",
        "version": "2.6.4",
        "rel": "1",
        "desc": "An XML parser library",
        "url": "https://libexpat.github.io/",
        "license": "MIT",
        "src_url": "https://github.com/libexpat/libexpat/releases/download/R_2_6_4/expat-2.6.4.tar.xz",
        "src_dir": "expat-2.6.4",
        "configure": ["./configure", "--prefix=/opt/pacman", "--without-docbook"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "libffi",
        "repo": "core",
        "version": "3.4.6",
        "rel": "1",
        "desc": "Portable foreign function interface library",
        "url": "https://sourceware.org/libffi/",
        "license": "MIT",
        "src_url": "https://github.com/libffi/libffi/releases/download/v3.4.6/libffi-3.4.6.tar.gz",
        "src_dir": "libffi-3.4.6",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "ncurses",
        "repo": "core",
        "version": "6.5",
        "rel": "1",
        "desc": "System V Release 4.0 curses emulation library",
        "url": "https://invisible-island.net/ncurses/",
        "license": "MIT",
        "src_url": "https://ftp.gnu.org/gnu/ncurses/ncurses-6.5.tar.gz",
        "src_dir": "ncurses-6.5",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-shared", "--without-debug", "--enable-widec", "--enable-pc-files", "--with-pkg-config-libdir=/opt/pacman/lib/pkgconfig"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
        "post_install": "ncurses_links",
    },
    {
        "name": "readline",
        "repo": "core",
        "version": "8.2",
        "rel": "1",
        "desc": "GNU readline library",
        "url": "https://tiswww.case.edu/php/chet/readline/rltop.html",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/readline/readline-8.2.tar.gz",
        "src_dir": "readline-8.2",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-curses"],
        "build": ["make", "SHLIB_LIBS=-lncursesw", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "xz",
        "repo": "core",
        "version": "5.6.3",
        "rel": "1",
        "desc": "Free general-purpose data compression software",
        "url": "https://tukaani.org/xz/",
        "license": "GPL-2.0-or-later AND LGPL-2.1-or-later",
        "src_url": "https://github.com/tukaani-project/xz/releases/download/v5.6.3/xz-5.6.3.tar.gz",
        "src_dir": "xz-5.6.3",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "lzo",
        "repo": "core",
        "version": "2.10",
        "rel": "1",
        "desc": "Extremely fast data compression library",
        "url": "https://www.oberhumer.com/opensource/lzo/",
        "license": "GPL-2.0-or-later",
        "src_url": "https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz",
        "src_dir": "lzo-2.10",
        "configure": ["./configure", "--prefix=/opt/pacman", "--enable-shared"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "xxhash",
        "repo": "core",
        "version": "0.8.2",
        "rel": "1",
        "desc": "Extremely fast non-cryptographic hash algorithm",
        "url": "https://cyan4973.github.io/xxHash/",
        "license": "BSD-2-Clause",
        "src_url": "https://github.com/Cyan4973/xxHash/archive/refs/tags/v0.8.2.tar.gz",
        "src_dir": "xxHash-0.8.2",
        "build": ["make", "PREFIX=/opt/pacman", "-j8"],
        "install": ["make", "PREFIX=/opt/pacman", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "brotli",
        "repo": "core",
        "version": "1.1.0",
        "rel": "1",
        "desc": "Generic-purpose lossless compression algorithm",
        "url": "https://github.com/google/brotli",
        "license": "MIT",
        "src_url": "https://github.com/google/brotli/archive/refs/tags/v1.1.0.tar.gz",
        "src_dir": "brotli-1.1.0",
        "cmake": ["cmake", "-B", "build", "-DCMAKE_INSTALL_PREFIX=/opt/pacman", "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=ON"],
        "build": ["cmake", "--build", "build", "-j8"],
        "install": ["cmake", "--install", "build", "--prefix", "{pkgdir}/opt/pacman"],
    },
    {
        "name": "pkgconf",
        "repo": "core",
        "version": "2.3.0",
        "rel": "1",
        "desc": "Package compiler and linker metadata toolkit",
        "url": "https://gitea.treehouse.systems/ariadne/pkgconf",
        "license": "ISC",
        "src_url": "https://distfiles.dereferenced.org/pkgconf/pkgconf-2.3.0.tar.xz",
        "src_dir": "pkgconf-2.3.0",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
        "post_install": "pkgconf_links",
    },
    {
        "name": "openssl",
        "repo": "core",
        "version": "3.4.0",
        "rel": "1",
        "desc": "The Open Source toolkit for SSL/TLS",
        "url": "https://www.openssl.org/",
        "license": "Apache-2.0",
        "src_url": "https://github.com/openssl/openssl/releases/download/openssl-3.4.0/openssl-3.4.0.tar.gz",
        "src_dir": "openssl-3.4.0",
        "configure": ["./Configure", "darwin64-x86_64-cc", "--prefix=/opt/pacman", "--openssldir=/opt/pacman/etc/ssl", "shared", "no-tests"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install_sw"],
    },
    {
        "name": "sqlite",
        "repo": "core",
        "version": "3.47.0",
        "rel": "1",
        "desc": "C-language library that implements a SQL database engine",
        "url": "https://www.sqlite.org/",
        "license": "blessing",
        "src_url": "https://www.sqlite.org/2024/sqlite-autoconf-3470000.tar.gz",
        "src_dir": "sqlite-autoconf-3470000",
        "configure": ["./configure", "--prefix=/opt/pacman", "--enable-readline"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "gawk",
        "repo": "core",
        "version": "5.3.1",
        "rel": "1",
        "desc": "GNU awk pattern scanning and processing language",
        "url": "https://www.gnu.org/software/gawk/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/gawk/gawk-5.3.1.tar.xz",
        "src_dir": "gawk-5.3.1",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-readline=/opt/pacman", "--with-mpfr=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "coreutils",
        "repo": "core",
        "version": "9.5",
        "rel": "1",
        "desc": "The basic file, shell and text manipulation utilities",
        "url": "https://www.gnu.org/software/coreutils/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/coreutils/coreutils-9.5.tar.xz",
        "src_dir": "coreutils-9.5",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-gmp=/opt/pacman", "--without-selinux", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "findutils",
        "repo": "core",
        "version": "4.10.0",
        "rel": "1",
        "desc": "GNU utilities for finding files",
        "url": "https://www.gnu.org/software/findutils/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/findutils/findutils-4.10.0.tar.xz",
        "src_dir": "findutils-4.10.0",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "bash",
        "repo": "core",
        "version": "5.2.37",
        "rel": "1",
        "desc": "Bourne-Again SHell, a UNIX command interpreter",
        "url": "https://www.gnu.org/software/bash/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/bash/bash-5.2.37.tar.gz",
        "src_dir": "bash-5.2.37",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-installed-readline=/opt/pacman", "--with-curses"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    }
]

def run_post_install(hook, pkgdir):
    libdir = pkgdir / "opt/pacman/lib"
    bindir = pkgdir / "opt/pacman/bin"
    if hook == "ncurses_links":
        # Create non-wide symlinks for compatibility
        for lib in ["ncurses", "form", "panel", "menu"]:
            dylib = libdir / f"lib{lib}.dylib"
            wdylib = f"lib{lib}w.dylib"
            if not dylib.exists() and (libdir / wdylib).exists():
                dylib.symlink_to(wdylib)
    elif hook == "pkgconf_links":
        pkg_config = bindir / "pkg-config"
        if not pkg_config.exists() and (bindir / "pkgconf").exists():
            pkg_config.symlink_to("pkgconf")

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
    
    if "cmake" in recipe:
        print(f"  -> Configuring with CMake...")
        subprocess.run(recipe["cmake"], cwd=src_dir, env=BUILD_ENV, check=True)
    elif "configure" in recipe:
        print(f"  -> Configuring...")
        subprocess.run(recipe["configure"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "build" in recipe:
        print(f"  -> Building...")
        subprocess.run(recipe["build"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "install" in recipe:
        print(f"  -> Installing to staging...")
        inst_cmd = [arg.replace("{pkgdir}", str(pkgdir)) for arg in recipe["install"]]
        subprocess.run(inst_cmd, cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "post_install" in recipe:
        run_post_install(recipe["post_install"], pkgdir)

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
                
        print(f"\nSuccessfully built {len(built)} packages from source in Tier 2!")

if __name__ == "__main__":
    main()

